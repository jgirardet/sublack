# -*- coding: utf-8 -*-
"""
Sublime Text 3 Plugin to invoke Black on a Python file.
"""


import os
import subprocess
import sys
import textwrap

import sublime
import sublime_plugin


SUBLIME_3 = sys.version_info >= (3, 0)
KEY = "sublack"

PLUGIN_SETTINGS_FILE = "Sublack.sublime-settings"
SUBLIME_SETTINGS_KEY = "Sublack"



def indent_text(text, indent, trailing_nl):
    # reindent
    text = textwrap.indent(text, indent)

    # remove trailing newline if so desired
    if not trailing_nl and text.endswith('\n'):
        text = text[:-1]

    return text



class Black:
    """
    This class wraps Back invocation
    """

    def __init__(self, view):
        self.view = view

    def __call__(self, edit):

        # prepare popen arguments
        cmd = self.get_setting("black_command")
        if not cmd:
            # always show error in popup
            msg = 'Black command not configured. Problem with settings?'
            sublime.error_message(msg)
            raise Exception(msg)
        cmd = os.path.expanduser(cmd)
        cmd = sublime.expand_variables(
            cmd, sublime.active_window().extract_variables())

        self.popen_args = [cmd]

        # use directory of current file
        self.fname = self.view.file_name()
        self.popen_cwd = os.path.dirname(self.fname) if self.fname else None


        # win32: hide console window
        if sys.platform in ('win32', 'cygwin'):
            self.popen_startupinfo = subprocess.STARTUPINFO()
            self.popen_startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
            self.popen_startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            self.popen_startupinfo = None

        self.errors = []

    
        self.popen_args += [self.fname]

        try:
            subprocess.Popen(
                self.popen_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.popen_cwd,
                # env=self.popen_env,
                startupinfo=self.popen_startupinfo)
        except OSError as err:
            # always show error in popup
            msg = "You may need to install Black and/or configure 'black_command' in Sublack's Settings."
            sublime.error_message("OSError: %s\n\n%s" % (err, msg))
            return

        # encoded_stdout, encoded_stderr = popen.communicate()


    def get_setting(self, key, default_value=None):
        return get_setting(self.view, key, default_value)


def is_python(view):
    return view.score_selector(0, 'source.python') > 0


class PreserveSelectionAndView:
    """
    This context manager assists in preserving the selection when text is replaced.
    (Sublime Text 3 already does a good job preserving the view.)
    """

    def __init__(self, view):
        self.view = view

    def __enter__(self):
        # save selection
        self.sel = list(self.view.sel())
        return self

    def __exit__(self, type, value, traceback):
        # restore selection
        self.view.sel().clear()
        for s in self.sel:
            self.view.sel().add(s)



class BlackDocumentCommand(sublime_plugin.TextCommand):
    """
    The "yapf_document" command formats the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        with PreserveSelectionAndView(self.view):
            Black(self.view)(edit)


class EventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):  # pylint: disable=no-self-use
        if get_setting(view, 'on_save'):
            view.run_command('black_document')


def get_setting(view, key, default_value=None):
    # 1. check sublime settings (this includes project settings)
    settings = sublime.active_window().active_view().settings()
    config = settings.get(SUBLIME_SETTINGS_KEY)
    if config is not None and key in config:
        return config[key]

    # 2. check plugin settings
    settings = sublime.load_settings(PLUGIN_SETTINGS_FILE)
    return settings.get(key, default_value)
