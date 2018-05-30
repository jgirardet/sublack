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

    def __call__(self, edit):

        # prepare popen arguments
        cmd = get_setting(self.view, "black_command")
        if not cmd:
            # always show error in popup
            msg = "Black command not configured. Problem with settings?"
            sublime.error_message(msg)
            raise Exception(msg)

        cmd = os.path.expanduser(cmd)

        cmd = sublime.expand_variables(cmd, sublime.active_window().extract_variables())

        # set  black in input/ouput mode with -
        self.cmd = [cmd, "-"]

        # Line length option
        line_length = get_setting(self.view, "line_length")
        if line_length is not None:
            self.cmd += ["-l", str(line_length)]

        # win32: hide console window
        if sys.platform in ("win32", "cygwin"):
            self.popen_startupinfo = subprocess.STARTUPINFO()
            self.popen_startupinfo.dwFlags = (
                subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            )
            self.popen_startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            self.popen_startupinfo = None

        # get encoding of current file
        encoding = self.view.encoding()
        if encoding == "Undefined":
            encoding = get_encoding_from_file(self.view)
        if not encoding:
            encoding = get_setting(self.view, "default_encoding", "utf-8")

        # select the whole file en encode it
        # encoding in popen starts with python 3.6
        all_file = sublime.Region(0, self.view.size())
        content = self.view.substr(all_file)
        content = content.encode(encoding)

        # modifying the locale is necessary to keep the click library happy on OSX
        env = os.environ.copy()
        if locale.getdefaultlocale() == (None, None):
            if platform.system() == "Darwin":
                env["LC_CTYPE"] = "UTF-8"

        try:
            p = subprocess.Popen(
                self.cmd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=self.popen_startupinfo,
            )
            out, err = p.communicate(input=content)

        except OSError as err:
            msg = (
                "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            )
            sublime.error_message("OSError: %s\n\n%s" % (err, msg))
            return

        if p.returncode == 0:
            self.view.replace(edit, all_file, out.decode(encoding))
            if get_setting(self.view, "debug"):
                print("[SUBLACK] : %s" % err.decode(encoding))

        else:
            print("[SUBLACK] Black did not run succesfully: %s" % err.decode(encoding))
            return


def is_python(view):
    return view.score_selector(0, "source.python") > 0


class BlackFileCommand(sublime_plugin.TextCommand):
    """
    The "yapf_document" command formats the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        Black(self.view)(edit)


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
