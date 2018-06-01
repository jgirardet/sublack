# -*- coding: utf-8 -*-
"""
Sublime Text 3 Plugin to invoke Black on a Python file.
"""

import locale
import os
import subprocess
import sys
import platform
import re

import sublime
import sublime_plugin


SUBLIME_3 = sys.version_info >= (3, 0)
KEY = "sublack"

PLUGIN_SETTINGS_FILE = "sublack.sublime-settings"
SUBLIME_SETTINGS_KEY = "sublack"

ENCODING_PATTERN = r"^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)"

CONFIG_OPTIONS = [
    "black_command",
    "on_save",
    "line_length",
    "fast",
    "debug_on",
    "default_encoding",
]


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
        self.config = {i: get_setting(view, i) for i in CONFIG_OPTIONS}
        self.all = sublime.Region(0, self.view.size())

    def get_command_line(self, edit, extra=[]):
        # prepare popen arguments
        cmd = self.config["black_command"]
        if not cmd:
            # always show error in popup
            msg = "Black command not configured. Problem with settings?"
            sublime.error_message(msg)
            raise Exception(msg)

        cmd = os.path.expanduser(cmd)

        cmd = sublime.expand_variables(cmd, sublime.active_window().extract_variables())

        # set  black in input/ouput mode with -
        cmd = [cmd, "-"]

        # Line length option
        if self.config["line_length"] is not None:
            cmd.extend(["-l", str(self.config["line_length"])])

        # fast
        if self.config["fast"]:
            cmd.append("--fast")

        # extra args
        if extra:
            cmd.extend(extra)

        return cmd

    def windows_popen_prepare(self):
        # win32: hide console window
        if sys.platform in ("win32", "cygwin"):
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
            if platform.system() == "Darwin":
                env["LC_CTYPE"] = "UTF-8"
        return env

    def get_content(self):
        # get encoding of current file
        encoding = self.view.encoding()
        if encoding == "Undefined":
            encoding = get_encoding_from_file(self.view)
        if not encoding:
            encoding = self.config["default_encoding"]

        # select the whole file en encode it
        # encoding in popen starts with python 3.6
        content = self.view.substr(self.all)
        content = content.encode(encoding)

        return content, encoding

    def run_black(self, cmd, env, content):

        try:
            p = subprocess.Popen(
                cmd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=self.windows_popen_prepare(),
            )
            out, err = p.communicate(input=content)

        except OSError as err:
            msg = (
                "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            )
            sublime.error_message("OSError: %s\n\n%s" % (err, msg))

        return p.returncode, out, err

    def do_diff(self, edit, out, encoding):
        window = sublime.active_window()
        f = window.new_file()
        f.set_scratch(True)
        f.set_name("sublack diff %s" % self.view.file_name().split("/")[-1])
        f.insert(edit, 0, out.decode(encoding))

    def __call__(self, edit, extra=[]):

        cmd = self.get_command_line(edit, extra)
        env = self.get_env()
        content, encoding = self.get_content()
        returncode, out, err = self.run_black(cmd, env, content)

        error_message = err.decode(encoding)

        # logging
        if get_setting(self.view, "debug_on"):
            print("[SUBLACK] : %s" % error_message)

        # failure
        if returncode != 0:
            return returncode

        # already formated, nothing changes
        elif "already well formatted, good job" in error_message:
            sublime.status_message("Sublack: %s" % error_message)

        # diff mode
        elif "--diff" in extra:
            self.do_diff(edit, out, encoding)

        # standard mode
        else:
            self.view.replace(edit, self.all, out.decode(encoding))


def is_python(view):
    return view.score_selector(0, "source.python") > 0


class BlackFileCommand(sublime_plugin.TextCommand):
    """
    The "black_file" command formats the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        if get_setting(self.view, "debug_on"):
            print("[SUBLACK] : run black_file")
        Black(self.view)(edit)


class BlackDiffCommand(sublime_plugin.TextCommand):
    """
    The "black_diff" command show a diff of the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        if get_setting(self.view, "debug_on"):
            print("[SUBLACK] : run black_diff")
        Black(self.view)(edit, extra=["--diff"])


class EventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if get_setting(view, "on_save"):
            view.run_command("black_file")


def get_setting(view, key, default_value=None):
    # 1. check sublime settings (this includes project settings)
    settings = sublime.active_window().active_view().settings()
    config = settings.get(SUBLIME_SETTINGS_KEY)
    if config is not None and key in config:
        return config[key]

    # 2. check plugin settings
    settings = sublime.load_settings(PLUGIN_SETTINGS_FILE)
    return settings.get(key, default_value)
