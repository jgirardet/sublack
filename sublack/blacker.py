# -*- coding: utf-8 -*-
"""
Sublime Text 3 Plugin to invoke Black on a Python file.
"""
import os.path
import locale
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
    timed,
    cache_path,
    find_root_file,
    use_pre_commit,
    popen,
)

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

        # all but line length
        for item in cmd:
            if item in HEADERS_TABLE:
                headers.update(HEADERS_TABLE[item])
        # line length
        if "-l" in cmd:
            headers["X-Line-Length"] = cmd[cmd.index("-l") + 1]

        LOG.debug("headers : %s", headers)
        return headers

    def process_response(self, response):
        """Format to the Popen format.

        returncode(int), out(byte), err(byte)
        """
        LOG.debug("Respone status code : %s", response.status_code)
        if response.status_code == 200:
            return 0, response.content, b"1 file reformated"

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
        self.use_pre_commit = self.config["black_use_precommit"] and use_pre_commit(
            find_root_file(view, ".pre-commit-config.yaml")
        )

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

        # black_skip_string_normalization
        if self.config.get("black_skip_numeric_underscore_normalization"):
            cmd.append("--skip-numeric-underscore-normalization")

        # handle pyi
        filename = self.view.file_name()
        if filename and filename.endswith(".pyi"):
            cmd.append("--pyi")

        # include /exclude
        if self.config.get("black_include"):
            cmd.extend(["--include", str(self.config["black_include"])])

        if self.config.get("black_exclude"):
            cmd.extend(["--exclude", str(self.config["black_exclude"])])

        # black_py36
        if self.config.get("black_py36"):
            cmd.append("--py36")

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

    def get_env(self):
        # modifying the locale is necessary to keep the click library happy on OSX
        env = os.environ.copy()
        if locale.getdefaultlocale() == (None, None):
            if sublime.platform() == "osx":
                env["LC_CTYPE"] = "UTF-8"
        return env

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

        prog = self.variables.get("project_path", "")
        if prog:
            return prog

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
            content_f, cmd_f = line.split("|")
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
            new = [str(hash(content)) + "|" + str(cmd)]
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
            new_content = out.decode(encoding)
            self.view.replace(edit, self.all, new_content)
            self.view.set_status(STATUS_KEY, REFORMATTED_MESSAGE)
            sublime.set_timeout_async(lambda: self.add_to_cache(new_content, cmd))

    def format_via_precommit(self, cmd, edit, content):
        import tempfile

        with tempfile.NamedTemporaryFile(
            prefix=".sublack", suffix=".py", dir=self.get_good_working_dir()
        ) as tmp:

            with open(tmp.name, "w") as f:
                f.write(content)

            cmd.append(tmp.name)
            p = popen(cmd, stdout=subprocess.PIPE, cwd=self.get_good_working_dir())
            p.wait(timeout=5)
            new_content = open(tmp.name).read()
            self.view.replace(edit, self.all, new_content)

    def __call__(self, edit, extra=[]):

        # get command_line  + args
        content, encoding = self.get_content()

        print("use precommit : ", self.use_pre_commit)

        if self.use_pre_commit:
            cmd = ["pre-commit", "run", "black", "--files"]
            self.format_via_precommit(cmd, edit, content.decode(encoding))
            return
        else:
            cmd = self.get_command_line(edit, extra)
        env = self.get_env()

        cwd = self.get_good_working_dir()
        LOG.debug("working dir: %s", cwd)

        # check the cache
        if self.is_cached(content, cmd):
            self.view.set_status(STATUS_KEY, ALREADY_FORMATTED_MESSAGE_CACHE)
            return

        # call black or balckd
        if self.use_pre_commit:
            self.run_standalone("")
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
