# -*- coding: utf-8 -*-
"""
Sublime Text 4 Plugin to invoke Black on a Python file.
"""

from __future__ import annotations

import os
import pathlib
import sublime
import subprocess

from .vendor.packages import requests
from . import consts
from . import folding
from . import utils


_typing = False
if _typing:
    from typing import Any
del _typing


# self.log = logging.getLogger(PACKAGE_NAME)


class Blackd:
    """
    Wrapper between black command line and blackd
    """

    def __init__(
        self,
        command: list[str],
        content: bytes,
        encoding: str,
        config: dict[str, Any],
        view: sublime.View | None = None,
    ):
        super().__init__()
        self._view = view

        self.headers = self.format_headers(command)
        self.content = content
        self.encoding = encoding
        self.config = config

    @property
    def log(self):
        return utils.get_log()

    @property
    def view(self):
        view = self._view or sublime.active_window().active_view()
        assert view, "view not defined!"
        return view

    def format_headers(self, command: list[str]) -> dict[str, Any]:
        """Get command line args and turn it to properly formatted headers"""
        headers: dict[str, Any] = {}
        command_set = set(command)
        self.log.debug(f"command_set: {command_set}")
        # all but line length an dtarget version
        for item in command:
            if item not in consts.HEADERS_TABLE:
                continue

            headers.update(consts.HEADERS_TABLE[item])

        if "-l" in command_set:
            headers["X-Line-Length"] = command[command.index("-l") + 1]

        filename = self.view.file_name()
        if filename and filename.endswith(".pyi"):
            headers["X-Python-Variant"] = "pyi"

        else:
            targets = set()
            for index, item in enumerate(command):
                if item != "--target-version":
                    continue

                version = command[index + 1]
                variant = f"{version[:-1]}.{version[-1]}"
                targets.add(variant)

            if targets:
                headers["X-Python-Variant"] = ",".join(targets)

        use_dif = "--diff" in command_set
        if use_dif:
            headers["X-Diff"] = "true"

        self.log.debug(f"headers: {headers}")
        return headers

    def process_response(self, response):
        """Format to the Popen format.

        returncode(int), out(byte), err(byte)
        """
        self.log.debug("Response status code : %s", response.status_code)
        if response.status_code == 200:
            return 0, response.content, b"1 file reformatted"

        elif response.status_code == 204:
            return 0, response.content, b"1 file left unchanged"

        elif response.status_code in [400, 500]:
            return -1, response.content, b"unknown error"

        return -1, response.content, b"no valid response"

    def process_errors(self, msg):
        response = requests.Response()
        response.status_code = 500
        self.log.error(msg)
        response._content = msg.encode()
        return response

    def __call__(self):
        if not utils.has_blackd_started():
            self.log.debug("Black server has not finished initializing!")
            return None, None, None

        self.headers.update({"Content-Type": f"application/octet-stream; charset={self.encoding}"})
        url = "http://{h}:{p}/".format(
            h=self.config["black_blackd_host"], p=self.config["black_blackd_port"]
        )
        try:
            self.log.info("Requesting url: {url}".format(url=url))
            response = requests.post(url, data=self.content, headers=self.headers)

        except requests.ConnectionError as err:
            self.log.critical("Connection error:\n {err}".format(err=err))
            msg = "blackd not running on port {p}".format(p=self.config["black_blackd_port"])
            response = self.process_errors(msg)
            sublime.message_dialog("{}, you can start it with blackd_start command".format(msg))

        except Exception as err:
            response = self.process_errors(str(err))
            self.log.error("Request to Blackd failed")

        return self.process_response(response)


class Black:
    """
    This class wraps Black invocation
    """

    def __init__(self, view: sublime.View | None = None):
        super().__init__()

        active_window = sublime.active_window()
        view = view or active_window.active_view()
        assert view, "view not defined, cannot init Black!"
        window = view.window() or active_window

        self.view = view
        self.settings = utils.get_settings(view=view)
        self.all = sublime.Region(0, self.view.size())
        self.variables = window.extract_variables()
        self.formatted_cache = utils.cache_path() / "formatted"
        self.pre_commit_config = False

        self.log.debug("Config:\n{}".format(utils.format_log_data(self.settings)))
        if not self.settings.get("black_use_precommit"):
            return

        root_file = utils.find_root_file(self.view, ".pre-commit-config.yaml")
        if root_file is None:
            return

        self.pre_commit_config = utils.use_pre_commit(root_file)

    @property
    def log(self):
        return utils.get_log()

    def get_content(self):
        encoding = utils.get_encoding(settings=self.settings)

        # select the whole file en encode it
        # encoding in popen starts with python 3.6
        content = self.view.substr(self.all)
        content = content.encode(encoding)

        self.log.debug("encoding: %s", encoding)
        return content, encoding

    def run_black(self, command: list[str], env: dict[str, Any], cwd: str | None, content: bytes):
        try:
            process = subprocess.run(
                command,
                env=env,
                cwd=cwd,
                input=content,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=utils.get_startup_info(),
            )
            out, err = process.stdout, process.stderr

        except UnboundLocalError as err:
            msg = "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            sublime.error_message("OSError: %s\n\n%s" % (err, msg))
            raise OSError(
                "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            )

        except OSError as err:
            import traceback

            exception = traceback.format_exc()
            msg = "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            sublime.error_message("OSError: %s\n\n%s" % (exception, msg))
            raise OSError(
                "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            )

        self.log.debug("run_black: returncode %s, err: %s", process.returncode, err)
        return process.returncode, out, err

    def create_diff_view(self, edit: sublime.Edit, content: bytes, encoding: str):
        window = sublime.active_window()
        view = window.new_file()
        window.focus_view(view)
        view.set_scratch(True)
        view.set_name(f"sublack diff {self.view.name()}")
        view.set_syntax_file("Packages/Diff/Diff.sublime-syntax")
        view.insert(edit, 0, content.decode(encoding))

    def get_working_directory(self):
        filename = self.view.file_name()
        if filename:
            return os.path.dirname(filename)

        window = self.view.window()
        if not window:
            return

        folders = window.folders()
        if not folders:
            return

        return folders[0]

    def is_cached(self, content, command):
        h_content = hash(content)
        cache = self.formatted_cache.open().read().splitlines()
        self.log.debug(f"cache: {cache}")
        for line in cache:
            content_f, cmd_f = line.split("|||")
            if int(content_f) == h_content:
                if cmd_f == str(command):
                    return True
        return False

    def add_to_cache(self, content, command):
        if self.is_cached(content, command):
            return
        with self.formatted_cache.open("r+") as cache:
            old = cache.read().splitlines()
            if len(old) > 250:
                old.pop()

            cache.seek(0)
            new = [str(hash(content)) + "|||" + str(command)]
            self.log.debug("write to cache %s", str(new))

            new_file = "\n".join((new + old))
            cache.write(new_file)
            return True

    def finalize(self, edit: sublime.Edit, extra, returncode, out, err, content, command, encoding):
        error_message = err.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")

        self.log.debug(f"Black returned: {error_message}")
        # failure
        if returncode != 0:
            self.view.set_status(consts.STATUS_KEY, error_message)
            return returncode

        # already formated, nothing changes
        elif "unchanged" in error_message:
            self.view.set_status(consts.STATUS_KEY, consts.ALREADY_FORMATTED_MESSAGE)
            self.add_to_cache(content, command)

        # diff mode
        elif "--diff" in extra:
            self.create_diff_view(edit, out, encoding)

        # standard mode
        else:
            # setup folding
            old_sel = self.view.sel()[0]
            folded_lines = folding.get_folded_lines(self.view)

            # result of formatting
            new_content = out.decode(encoding)
            self.view.replace(edit, self.all, new_content)

            # reapply folding
            old = folding.get_ast_index(content)
            new = folding.get_ast_index(out)
            if old and new:
                folding.refold_all(old, new, self.view, folded_lines)
            self.view.sel().clear()
            self.view.sel().add(old_sel)

            # status and caching
            self.view.set_status(consts.STATUS_KEY, consts.REFORMATTED_MESSAGE)
            sublime.set_timeout_async(lambda: self.add_to_cache(new_content, command))

    def format_via_precommit(self, edit: sublime.Edit, content, cwd, env):
        command = ["pre-commit", "run", "black", "--files"]

        import tempfile

        tmp_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)

        tmp = pathlib.Path(tmp_file.name)
        tmp_file.close()
        tmp.write_text(content)

        command.extend([str(tmp.resolve()), "--config", str(self.pre_commit_config)])
        window = self.view.window()
        assert window, "No window found!"
        self.log.debug("cwd : %s", cwd)
        self.log.debug(window.folders())
        self.log.debug(command)
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                startupinfo=utils.get_startup_info(),
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            )
            if process.stdout:
                print(process.stdout.read())
        except subprocess.CalledProcessError as err:
            self.log.error(err)
            return err
        except Exception as err:
            tmp.unlink()
            raise err

        self.view.replace(edit, self.all, tmp.read_text())
        sublime.set_timeout_async(lambda: tmp.unlink())

    def __call__(
        self, edit: sublime.Edit, file_path: pathlib.Path | None = None, extra: list[str] = []
    ):

        # get command_line  + args
        content, encoding = self.get_content()
        cwd = self.get_working_directory()
        self.log.debug(f"Working dir: {cwd}")
        env = utils.get_env()

        if self.pre_commit_config:
            self.log.debug("Using pre-commit with {}".format(self.pre_commit_config))
            self.format_via_precommit(edit, content.decode(encoding), cwd, env)
            return

        use_blackd = self.settings.get("black_use_blackd", True) and "--diff" not in extra
        command = utils.get_full_black_command(
            view=self.view,
            file_path=file_path,
            use_blackd=use_blackd,
            extra=extra,
        )

        # check the cache
        # cache may not be used with pre-commit
        if self.is_cached(content, command):
            self.view.set_status(consts.STATUS_KEY, consts.ALREADY_FORMATTED_MESSAGE_CACHE)
            return

        if use_blackd:
            if not utils.has_blackd_started():
                self.log.debug("Black server has not finished initializing!")
                sublime.error_message("Black server has not finished initializing!")
                return

            self.log.debug("using blackd")
            returncode, out, err = Blackd(command, content, encoding, self.settings)()

        else:
            self.log.debug("using black")
            returncode, out, err = self.run_black(command, env, cwd, content)

        # format/diff in editor
        self.finalize(edit, extra, returncode, out, err, content, command, encoding)


class BlackAll:
    def __init__(self, window: sublime.Window):
        super().__init__()

        view = window.active_view()
        assert view, "view not defined, cannot init BlackAll!"

        view = window.active_view()
        assert view, "view not defined, cannot init BlackAll!"

        self.view = view
        self.settings = utils.get_settings(view=view)
        self.variables = window.extract_variables()
        self.folders = window.folders()
        # self.folders = ["D:\\Code\\Git\\sublack\\tests\\format_all"]

    @property
    def log(self):
        return utils.get_log()

    def get_working_directory(self):
        filename = self.view.file_name()
        if filename:
            return os.path.dirname(filename)

        window = self.view.window()
        if not window:
            return

        folders = window.folders()
        if not folders:
            return

        return folders[0]

    def run_black_command(self, command: list[str]):
        try:
            process = subprocess.run(
                command,
                env=utils.get_env(),
                cwd=self.get_working_directory(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=utils.get_startup_info(),
                timeout=10,
            )
            stdout, stderr = process.stdout, process.stderr

        except UnboundLocalError as error:
            msg = "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            sublime.error_message("OSError: %s\n\n%s" % (error, msg))
            raise OSError(
                "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            )

        except OSError as error:
            import traceback

            exception = traceback.format_exc()
            msg = "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            sublime.error_message("OSError: %s\n\n%s" % (exception, msg))
            raise OSError(
                "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            )

        self.log.debug(f"run_black_command: return code: {process.returncode}, message: {stderr}")
        return process.returncode, stdout, stderr

    def run_black_on_folder(self, folder, extra: list[str] = []):
        command = utils.get_full_black_command(
            view=self.view,
            file_path=folder,
            use_blackd=False,
            extra=extra,
        )
        return self.run_black_command(command)

    def run(self, extra: list[str] = []):
        folders = self.folders
        if self.settings["black_confirm_formatall"]:
            folders_str = "\n- ".join(folders)
            message = (
                f"Sublack: Format all files in the following folders:\n\n- {folders_str}"
                "\n\nWarning: This cannot be undone!"
            )
            if not sublime.ok_cancel_dialog(message):
                return

        error_list: list[tuple[str, int, str]] = []
        success_list: list[tuple[str, int, str]] = []
        for folder in folders:
            return_code, _, error = self.run_black_on_folder(folder, extra=extra)
            result_list = success_list if return_code == 0 else error_list
            result_list.append((folder, return_code, error.decode()))

        error_message = (
            consts.REFORMATTED_ALL_PARTIAL_MESSAGE
            if success_list and error_list
            else consts.REFORMATTED_ALL_MESSAGE
            if success_list
            else consts.REFORMAT_ERRORS
        )
        # if success_list and error_list:
        #     error_message = consts.REFORMATTED_ALL_PARTIAL_MESSAGE

        # elif success_list:
        #     error_message = consts.REFORMATTED_ALL_MESSAGE

        # else:
        #     error_message = consts.REFORMAT_ERRORS

        self.view.set_status(consts.STATUS_KEY, error_message)
        for result in success_list:
            folder, code, output = result
            self.log.debug(
                f"Black successfully formatted folder: {folder} - return code: {code} output: {output}"
            )

        for result in error_list:
            folder, code, output = result
            self.log.error(
                f"Black failed to format folder: {folder} - return code: {code} output: {output}"
            )
