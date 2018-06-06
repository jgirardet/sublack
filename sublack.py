# -*- coding: utf-8 -*-
"""
Sublime Text 3 Plugin to invoke Black on a Python file.
"""

import locale
import os
import subprocess
import re

import sublime
import sublime_plugin


PLUGIN_SETTINGS_FILE = "sublack.sublime-settings"
SUBLIME_SETTINGS_KEY = "sublack"

ENCODING_PATTERN = r"^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)"

ALREADY_FORMATED_MESSAGE = "Sublack: already well formated !"

CONFIG_OPTIONS = [
    "black_command",
    "black_on_save",
    "black_line_length",
    "black_fast",
    "black_debug_on",
    "black_default_encoding",
    "black_skip_string_normalization",
]


def get_setting(view, key, default_value=None):
    # 1. check sublime settings (this includes project settings)
    settings = view.settings()
    config = settings.get(SUBLIME_SETTINGS_KEY)
    if config is not None and key in config:
        return config[key]

    # 2. check plugin settings
    settings = sublime.load_settings(PLUGIN_SETTINGS_FILE)
    return settings.get(key, default_value)


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

        cmd = sublime.expand_variables(cmd, self.view.window().extract_variables())

        # set  black in input/ouput mode with -
        cmd = [cmd, "-"]

        # Line length option
        if self.config.get("black_line_length"):
            cmd.extend(["-l", str(self.config["black_line_length"])])

        # fast
        if self.config.get("black_fast", None):
            cmd.append("--fast")

        # black_skip_string_normalization
        if self.config.get("black_skip_string_normalization"):
            cmd.append("--skip-string-normalization")

        # extra args
        if extra:
            cmd.extend(extra)

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
        f.insert(edit, 0, out.decode(encoding))

    def __call__(self, edit, extra=[]):

        cmd = self.get_command_line(edit, extra)
        env = self.get_env()
        content, encoding = self.get_content()
        returncode, out, err = self.run_black(cmd, env, content)

        error_message = err.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")

        # logging
        if self.config["black_debug_on"]:
            print("[SUBLACK] : %s" % error_message)

        # failure
        if returncode != 0:
            sublime.status_message(error_message)
            return returncode

        # already formated, nothing changes
        elif "unchanged" in error_message:
            sublime.status_message(ALREADY_FORMATED_MESSAGE)

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
        if get_setting(self.view, "black_debug_on"):
            print("[SUBLACK] : run black_file")
        Black(self.view)(edit)


class BlackDiffCommand(sublime_plugin.TextCommand):
    """
    The "black_diff" command show a diff of the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    def run(self, edit):
        if get_setting(self.view, "black_debug_on"):
            print("[SUBLACK] : run black_diff")
        Black(self.view)(edit, extra=["--diff"])


class EventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if get_setting(view, "black_on_save"):
            view.run_command("black_file")
