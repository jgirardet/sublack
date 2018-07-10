# -*- coding: utf-8 -*-
"""
Sublime Text 3 Plugin to invoke Black on a Python file.
"""
import os.path
import locale
import os
import subprocess
import re

import sublime
import sublime_plugin

PACKAGE_NAME = "sublack"
SETTINGS_FILE_NAME = "{}.sublime-settings".format(PACKAGE_NAME)
SETTINGS_NS_PREFIX = "{}.".format(PACKAGE_NAME)
KEY_ERROR_MARKER = "__KEY_NOT_PRESENT_MARKER__"

ENCODING_PATTERN = r"^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)"

ALREADY_FORMATED_MESSAGE = "Sublack: already well formated !"

CONFIG_OPTIONS = [
    "black_line_length",
    "black_fast",
    "black_skip_string_normalization",
    "black_command",
    "black_on_save",
    "black_debug_on",
    "black_default_encoding",
    "black_autouse_pyproject",
]


def get_settings(view):
    flat_settings = view.settings()
    nested_settings = flat_settings.get(PACKAGE_NAME, {})
    global_settings = sublime.load_settings(SETTINGS_FILE_NAME)
    settings = {}

    for k in CONFIG_OPTIONS:
        # 1. check sublime "flat settings"
        value = flat_settings.get(SETTINGS_NS_PREFIX + k, KEY_ERROR_MARKER)
        if value != KEY_ERROR_MARKER:
            settings[k] = value
            continue

        # 2. check sublieme "nested settings" for compatibility reason
        value = nested_settings.get(k, KEY_ERROR_MARKER)
        if value != KEY_ERROR_MARKER:
            settings[k] = value
            continue

        # 3. check plugin/user settings
        settings[k] = global_settings.get(k)

    return settings


def get_encoding_from_region(region, view):
    """
    ENCODING_PATTERN is given by PEP 263
    """

    ligne = view.substr(region)
    encoding = re.findall(ENCODING_PATTERN, ligne)

    return encoding[0] if encoding else None


def get_encoding_from_file(view):
    """
    get from 2nd line only If failed from 1st line.
    """
    region = view.line(sublime.Region(0))
    encoding = get_encoding_from_region(region, view)
    if encoding:
        return encoding
    else:
        encoding = get_encoding_from_region(view.line(region.end() + 1), view)
        return encoding
    return None


class Black:
    """
    This class wraps Back invocation
    """

    def __init__(self, view):
        self.view = view
        self.config = get_settings(view)
        self.all = sublime.Region(0, self.view.size())
        self.variables = view.window().extract_variables()

    def get_command_line(self, edit, extra=[]):
        # prepare popen arguments
        cmd = self.config["black_command"]
        if not cmd:
            # always show error in popup
            msg = "Black command not configured. Problem with settings?"
            sublime.error_message(msg)
            raise Exception(msg)

        cmd = os.path.expanduser(cmd)

        cmd = sublime.expand_variables(cmd, self.variables)

        # set  black in input/ouput mode with -
        cmd = [cmd, "-"]

        # extra args
        if extra:
            cmd.extend(extra)

        # skip other config if pyproject with black config in
        if self.config["black_autouse_pyproject"] and self.use_pyproject():
            return cmd

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

    def __call__(self, edit, extra=[]):

        cmd = self.get_command_line(edit, extra)
        env = self.get_env()
        cwd = self.get_good_working_dir()
        content, encoding = self.get_content()
        returncode, out, err = self.run_black(cmd, env, cwd, content)

        error_message = err.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")

        # logging
        if self.config["black_debug_on"]:
            print("[SUBLACK] : %s" % error_message)

        # failure
        if returncode != 0:
            self.view.window().status_message(error_message)
            return returncode

        # already formated, nothing changes
        elif "unchanged" in error_message:
            self.view.window().status_message(ALREADY_FORMATED_MESSAGE)

        # diff mode
        elif "--diff" in extra:
            self.do_diff(edit, out, encoding)

        # standard mode
        else:
            self.view.replace(edit, self.all, out.decode(encoding))


def is_python(view):
    return view.match_selector(0, "source.python")


class BlackFileCommand(sublime_plugin.TextCommand):
    """
    The "black_file" command formats the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        if get_settings(self.view)["black_debug_on"]:
            print("[SUBLACK] : run black_file")
        Black(self.view)(edit)


class BlackDiffCommand(sublime_plugin.TextCommand):
    """
    The "black_diff" command show a diff of the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        if get_settings(self.view)["black_debug_on"]:
            print("[SUBLACK] : run black_diff")
        Black(self.view)(edit, extra=["--diff"])


class EventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if get_settings(view)["black_on_save"]:
            view.run_command("black_file")
