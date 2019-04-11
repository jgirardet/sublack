import sublime_plugin
import sublime
from .consts import (
    BLACK_ON_SAVE_VIEW_SETTING,
    STATUS_KEY,
    BLACKD_STARTED,
    BLACKD_STOPPED,
    BLACKD_START_FAILED,
    BLACKD_STOP_FAILED,
    PACKAGE_NAME,
    BLACKD_ALREADY_RUNNING,
    REFORMATTED_MESSAGE,
    REFORMAT_ERRORS,
)
from .utils import get_settings, check_blackd_on_http, get_on_save_fast, timed, popen
from .blacker import Black
import logging
from .server import BlackdServer
import subprocess

LOG = logging.getLogger(PACKAGE_NAME)


def is_python(view):
    return view.match_selector(0, "source.python")


class BlackFileCommand(sublime_plugin.TextCommand):
    """
    The "black_file" command formats the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    is_visible = is_enabled

    @timed
    def run(self, edit):
        LOG.debug("running black_file")
        Black(self.view)(edit)


class BlackDiffCommand(sublime_plugin.TextCommand):
    """
    The "black_diff" command show a diff of the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    is_visible = is_enabled

    def run(self, edit):
        LOG.debug("running black_file")
        Black(self.view)(edit, extra=["--diff"])


class BlackToggleBlackOnSaveCommand(sublime_plugin.TextCommand):
    """
    The "black_toggle_black_on_save" switches the setting with the same
    name temporarily per view.
    """

    def is_enabled(self):
        return is_python(self.view)

    is_visible = is_enabled

    def description(self):
        settings = get_settings(self.view)
        if settings["black_on_save"]:
            return "Sublack: Disable black on save"
        else:
            return "Sublack: Enable black on save"

    def run(self, edit):
        view = self.view

        settings = get_settings(view)
        current_state = settings["black_on_save"]
        next_state = not current_state

        # A setting set on a particular view overules all other places where
        # the same setting could have been set as well. E.g. project settings.
        # Now, we first `erase` such a view setting which is luckily an
        # operation that never throws, and immediately check again if the
        # wanted next state is fulfilled by that side effect.
        # If yes, we're almost done and just clean up the status area.
        view.settings().erase(BLACK_ON_SAVE_VIEW_SETTING)
        if get_settings(view)["black_on_save"] == next_state:
            view.erase_status(STATUS_KEY)
            return

        # Otherwise, we set the next state, and indicate in the status bar
        # that this view now deviates from the other views.
        view.settings().set(BLACK_ON_SAVE_VIEW_SETTING, next_state)
        view.set_status(STATUS_KEY, "black: {}".format("ON" if next_state else "OFF"))


class BlackdStartCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return True

    is_visible = is_enabled

    def run(self, edit):
        started = None
        LOG.debug("blackd_start command running")
        settings = get_settings(self.view)
        port = settings["black_blackd_port"]
        running, port_free = check_blackd_on_http(port)
        if running:
            LOG.info(BLACKD_ALREADY_RUNNING.format(port))
            self.view.set_status(STATUS_KEY, BLACKD_ALREADY_RUNNING.format(port))
            return
        elif port_free:
            sv = BlackdServer(
                deamon=True, host="localhost", port=port, settings=settings
            )
            started = sv.run()

        if started:
            self.view.set_status(STATUS_KEY, BLACKD_STARTED.format(port))
        else:
            self.view.set_status(STATUS_KEY, BLACKD_START_FAILED.format(port))


class BlackdStopCommand(sublime_plugin.ApplicationCommand):
    def is_enabled(self):
        return True

    is_visible = is_enabled

    def run(self):
        LOG.debug("blackd_stop command running")
        if BlackdServer().stop_deamon():
            sublime.active_window().active_view().set_status(STATUS_KEY, BLACKD_STOPPED)
        else:
            sublime.active_window().active_view().set_status(
                STATUS_KEY, BLACKD_STOP_FAILED
            )


class BlackEventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        """use blackd at saving time

        Cannot be async since black should be run before save"""
        if get_on_save_fast(view):
            view.run_command("black_file")

    def on_post_text_command(self, view, command_name, args):
        if command_name == "black_file":
            view.show(view.line(view.sel()[0]))


class BlackFormatAllCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return True

    is_visible = is_enabled

    def run(self):
        if get_settings(self.window.active_view())["black_confirm_formatall"]:
            if not sublime.ok_cancel_dialog("Sublack : Format all ?"):
                return

        folders = self.window.folders()

        success = []
        errors = []
        dispatcher = None
        for folder in folders:
            p = popen(
                ["black", "."],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=folder,
            )
            p.wait(timeout=10)
            dispatcher = success if p.returncode == 0 else errors
            dispatcher.append((folder, p.returncode, p.stderr.read()))

        if not errors:  # all 0 return_code
            self.window.active_view().set_status(STATUS_KEY, REFORMATTED_MESSAGE)
        else:
            self.window.active_view().set_status(STATUS_KEY, REFORMAT_ERRORS)

        for out in success:
            LOG.debug(
                "black formatted folder %s with returncode %s and following en stderr :%s",
                *out
            )

        for out in errors:
            LOG.error(
                "black formatted folder %s with returncode %s and following en stderr :%s",
                *out
            )
