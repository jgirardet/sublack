# -*- coding: utf-8 -*-
"""
Sublime Text 3 Plugin to invoke Black on a Python file.
"""
import os.path
import os
import subprocess

import sublime

import requests
import logging

from .consts import (
    HEADERS_TABLE,
    ALREADY_FORMATTED_MESSAGE,
    ALREADY_FORMATTED_MESSAGE_CACHE,
    STATUS_KEY,
    PACKAGE_NAME,
    REFORMATTED_MESSAGE,
)
from .utils import (
    get_settings,
    get_encoding_from_file,
    cache_path,
    find_root_file,
    use_pre_commit,
    Path,
    get_env,
)

from .folding import get_folded_lines, get_ast_index, refold_all


LOG = logging.getLogger(PACKAGE_NAME)


class Blackd:
    """warpper between black command line and blackd."""

    def __init__(self, cmd, content, encoding, config):

        self.headers = self.format_headers(cmd)
        self.content = content
        self.encoding = encoding
        self.config = config

    def format_headers(self, cmd):

        """Get command line args and turn it to properly formatted headers"""
        headers = {}

        # all but line length an dtarget version
        for item in cmd:
            if item in HEADERS_TABLE:
                headers.update(HEADERS_TABLE[item])
        # line length
        if "-l" in cmd:
            headers["X-Line-Length"] = cmd[cmd.index("-l") + 1]

        # target version
        targets = set()
        for index, item in enumerate(cmd):
            if item == "--target-version":
                version = cmd[index + 1]
                variant = version[:-1] + "." + version[-1]
                targets.add(variant)

        if "--py36" in cmd:
            targets.add("py3.6")

        if targets:
            headers["X-Python-Variant"] = ",".join(targets)

        LOG.debug("headers : %s", headers)
        return headers

    def process_response(self, response):
        """Format to the Popen format.

        returncode(int), out(byte), err(byte)
        """
        LOG.debug("Response status code : %s", response.status_code)
        if response.status_code == 200:
            return 0, response.content, b"1 file reformatted"

        elif response.status_code == 204:
            return 0, response.content, b"1 file left unchanged"

        elif response.status_code in [400, 500]:
            return -1, b"", response.content

    def process_errros(self, msg):
        response = requests.Response()
        response.status_code = 500
        LOG.error(msg)
        response._content = msg.encode()
        return response

    def __call__(self):

        self.headers.update(
            {"Content-Type": "application/octet-stream; charset=" + self.encoding}
        )
        url = (
            "http://"
            + self.config["black_blackd_host"]
            + ":"
            + self.config["black_blackd_port"]
            + "/"
        )
        try:
            response = requests.post(url, data=self.content, headers=self.headers)
        except requests.ConnectionError as err:

            msg = "blackd not running on port {}".format(
                self.config["black_blackd_port"]
            )
            response = self.process_errros(msg)
            sublime.message_dialog(msg + ", you can start it with blackd_start command")
        except Exception as err:
            response = self.process_errros(str(err))
            LOG.error("Request to  Blackd failed")

        return self.process_response(response)


class Black:
    """
    This class wraps Back invocation
    """

    def __init__(self, view):
        self.view = view
        self.config = get_settings(view)
        self.all = sublime.Region(0, self.view.size())
        self.variables = view.window().extract_variables()
        self.formatted_cache = cache_path() / "formatted"

        LOG.debug("config: %s", self.config)
        if self.config["black_use_precommit"]:
            self.pre_commit_config = use_pre_commit(
                find_root_file(self.view, ".pre-commit-config.yaml")
            )
        else:
            self.pre_commit_config = False

    def get_command_line(self, edit, extra=[]):
        # prepare popen arguments
        cmd = self.config["black_command"]
        if not cmd:
            # always show error in popup
            msg = "Black command not configured. Problem with settings ?"
            sublime.error_message(msg)
            raise Exception(msg)

        cmd = os.path.expanduser(cmd)

        cmd = sublime.expand_variables(cmd, self.variables)

        # set  black in input/ouput mode with -
        cmd = [cmd, "-"]

        # extra args
        if extra:
            cmd.extend(extra)

        # add black specific config to cmmandline

        # Line length option
        if self.config.get("black_line_length"):
            cmd.extend(["-l", str(self.config["black_line_length"])])

        # fast
        if self.config.get("black_fast", None):
            cmd.append("--fast")

        # black_skip_string_normalization
        if self.config.get("black_skip_string_normalization"):
            cmd.append("--skip-string-normalization")

        # handle pyi
        filename = self.view.file_name()
        if filename and filename.endswith(".pyi"):
            cmd.append("--pyi")

        # black_py36
        if self.config.get("black_py36"):
            cmd.append("--py36")

        # black target-vversion
        if self.config.get("black_target_version"):
            versions = []
            for v in self.config["black_target_version"]:
                cmd.extend(["--target-version", v])

        LOG.debug("command line: %s", cmd)
        return cmd

    def windows_popen_prepare(self):
        # win32: hide console window
        if sublime.platform() == "windows":
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags = (
                subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            )
            startup_info.wShowWindow = subprocess.SW_HIDE
        else:
            startup_info = None
        return startup_info

    def get_content(self):
        # get encoding of current file
        encoding = self.view.encoding()
        if encoding == "Undefined":
            encoding = get_encoding_from_file(self.view)
        if not encoding:
            encoding = self.config["black_default_encoding"]

        # select the whole file en encode it
        # encoding in popen starts with python 3.6
        content = self.view.substr(self.all)
        content = content.encode(encoding)

        LOG.debug("encoding: %s", encoding)
        return content, encoding

    def run_black(self, cmd, env, cwd, content):
        try:
            p = subprocess.Popen(
                cmd,
                env=env,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=self.windows_popen_prepare(),
            )
            out, err = p.communicate(input=content)

        except UnboundLocalError as err:  # unboud pour p si popen echoue
            msg = "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            sublime.error_message("OSError: %s\n\n%s" % (err, msg))
            raise OSError(
                "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            )

        except OSError as err:  # unboud pour p si popen echoue
            msg = "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            sublime.error_message("OSError: %s\n\n%s" % (err, msg))
            raise OSError(
                "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            )

        LOG.debug("run_black: returncode %s, err: %s", p.returncode, err)
        return p.returncode, out, err

    def do_diff(self, edit, out, encoding):
        window = self.view.window()
        f = window.new_file()
        f.set_scratch(True)
        f.set_name("sublack diff %s" % self.view.name())
        f.set_syntax_file("Packages/Diff/Diff.sublime-syntax")
        f.insert(edit, 0, out.decode(encoding))

    def get_good_working_dir(self):
        filename = self.view.file_name()
        if filename:
            return os.path.dirname(filename)

        window = self.view.window()
        if not window:
            return None

        folders = window.folders()
        if not folders:
            return None

        return folders[0]

    def is_cached(self, content, cmd):
        h_content = hash(content)
        cache = self.formatted_cache.open().read().splitlines()
        for line in cache:
            content_f, cmd_f = line.split("|||")
            if int(content_f) == h_content:
                if cmd_f == str(cmd):
                    return True
        return False

    def add_to_cache(self, content, cmd):
        if self.is_cached(content, cmd):
            return
        with self.formatted_cache.open("r+") as cache:
            old = cache.read().splitlines()
            if len(old) > 250:
                old.pop()

            cache.seek(0)
            new = [str(hash(content)) + "|||" + str(cmd)]
            LOG.debug("write to cache %s", str(new))

            new_file = "\n".join((new + old))
            cache.write(new_file)
            return True

    def finalize(self, edit, extra, returncode, out, err, content, cmd, encoding):
        error_message = err.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")

        LOG.debug("black says : %s" % error_message)
        # failure
        if returncode != 0:
            self.view.set_status(STATUS_KEY, error_message)
            return returncode

        # already formated, nothing changes
        elif "unchanged" in error_message:
            self.view.set_status(STATUS_KEY, ALREADY_FORMATTED_MESSAGE)
            self.add_to_cache(content, cmd)

        # diff mode
        elif "--diff" in extra:
            self.do_diff(edit, out, encoding)

        # standard mode
        else:
            # setup folding
            old_sel = self.view.sel()[0]
            folded_lines = get_folded_lines(self.view)

            # result of formatting
            new_content = out.decode(encoding)
            self.view.replace(edit, self.all, new_content)

            # reapply folding
            old = get_ast_index(self.view, content, encoding)
            new = get_ast_index(self.view, out, encoding)
            if old and new:
                refold_all(old, new, self.view, folded_lines)
            self.view.sel().clear()
            self.view.sel().add(old_sel)

            # status and caching
            self.view.set_status(STATUS_KEY, REFORMATTED_MESSAGE)
            sublime.set_timeout_async(lambda: self.add_to_cache(new_content, cmd))

    def format_via_precommit(self, edit, content, cwd, env):
        cmd = ["pre-commit", "run", "black", "--files"]

        import tempfile

        tmp_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)

        tmp = Path(tmp_file.name)
        tmp_file.close()
        tmp.write_text(content)

        cmd.extend([str(tmp.resolve()), "--config", str(self.pre_commit_config)])
        LOG.debug("cwd : %s", cwd)
        LOG.debug(self.view.window().folders())
        LOG.debug(cmd)
        try:
            a = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                startupinfo=self.windows_popen_prepare(),
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            )
            print(a.stdout.read())
        except subprocess.CalledProcessError as err:
            LOG.error(err)
            return err
        except Exception as err:
            tmp.unlink()
            raise err

        self.view.replace(edit, self.all, tmp.read_text())
        sublime.set_timeout_async(lambda: tmp.unlink())

    def __call__(self, edit, extra=[]):

        # get command_line  + args
        content, encoding = self.get_content()
        cwd = self.get_good_working_dir()
        LOG.debug("working dir: %s", cwd)
        env = get_env()

        if self.pre_commit_config:
            LOG.debug("Using pre-commit with %s", self.pre_commit_config)
            self.format_via_precommit(edit, content.decode(encoding), cwd, env)
            return
        else:
            cmd = self.get_command_line(edit, extra)

        # check the cache
        # cache may not be used with pre-commit
        if self.is_cached(content, cmd):
            self.view.set_status(STATUS_KEY, ALREADY_FORMATTED_MESSAGE_CACHE)
            return

        # call black or balckd

        if (
            self.config["black_use_blackd"] and "--diff" not in extra
        ):  # no diff with server
            LOG.debug("using blackd")
            returncode, out, err = Blackd(cmd, content, encoding, self.config)()
        else:
            LOG.debug("using black")
            returncode, out, err = self.run_black(cmd, env, cwd, content)

        # format/diff in editor
        self.finalize(edit, extra, returncode, out, err, content, cmd, encoding)
