# -*- coding: utf-8 -*-
"""
Sublime Text 3 Plugin to invoke Black on a Python file.
"""


import os
import subprocess
import sys


import sublime
import sublime_plugin


SUBLIME_3 = sys.version_info >= (3, 0)
KEY = "sublack"

PLUGIN_SETTINGS_FILE = "sublack.sublime-settings"
SUBLIME_SETTINGS_KEY = "sublack"


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

        self.popen_args = [cmd]

        # get filename and use directory of current file
        fname = self.view.file_name()
        self.popen_cwd = os.path.dirname(fname) if fname else None

        # win32: hide console window
        if sys.platform in ("win32", "cygwin"):
            self.popen_startupinfo = subprocess.STARTUPINFO()
            self.popen_startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            self.popen_startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            self.popen_startupinfo = None

        self.popen_args += [fname]

        # Line length option

        line_length = get_setting(self.view, "line_length")
        if line_length is not None:
            self.popen_args += ["-l {0}".format(line_length)]
            print("line : ", self.popen_args)

        try:
            p = subprocess.Popen(
                self.popen_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.popen_cwd,
                startupinfo=self.popen_startupinfo,
            )
            p.wait()
            if p.returncode != 0:
                msg = "Black did not run succesfully: please check the console for details."
                sublime.error_message(msg)
                print(p.stdout.readlines(), p.stderr.readlines())

        except OSError as err:
            # always show error in popup
            msg = "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            sublime.error_message("OSError: %s\n\n%s" % (err, msg))
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
        if not get_setting(self.view, "on_save"):
            self.view.run_command("save")
        Black(self.view)(edit)


class EventListener(sublime_plugin.EventListener):

    def on_post_save(self, view):
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
