import sublime_plugin
import sublime
import subprocess

from .consts import (
    BLACK_ON_SAVE_VIEW_SETTING,
    STATUS_KEY,
    BLACKD_STOPPED,
    BLACKD_STOP_FAILED,
    REFORMATTED_MESSAGE,
    REFORMAT_ERRORS,
)
from . import utils
from .blacker import Black
from .server import BlackdServer


class BlackFileCommand(sublime_plugin.TextCommand):
    """
    The "black_file" command formats the current document.
    """

    def is_enabled(self):
        return utils.is_python(self.view)

    is_visible = is_enabled

    # @timed
    def run(self, edit):
        utils.get_log().debug("Formatting current file")
        # backup view position:
        old_view_port = self.view.viewport_position()

        Black(self.view)(edit)

        # re apply view position
        # fix : https://github.com/jgirardet/sublack/issues/52
        # not tested : view.run_command doesn't reproduce bug in tests...
        sublime.set_timeout_async(lambda: self.view.set_viewport_position(old_view_port))


class BlackDiffCommand(sublime_plugin.TextCommand):
    """
    The "black_diff" command show a diff of the current document.
    """

    def is_enabled(self):
        return utils.is_python(self.view)

    is_visible = is_enabled

    def run(self, edit):
        utils.get_log().debug("running black_file")
        Black(self.view)(edit, extra=["--diff"])


class BlackToggleBlackOnSaveCommand(sublime_plugin.TextCommand):
    """
    The "black_toggle_black_on_save" switches the setting with the same
    name temporarily per view.
    """

    def is_enabled(self):
        return utils.is_python(self.view)

    is_visible = is_enabled

    def description(self):
        settings = utils.get_settings(self.view)
        if settings["black_on_save"]:
            return "Sublack: Disable black on save"
        else:
            return "Sublack: Enable black on save"

    def run(self, edit):
        view = self.view

        settings = utils.get_settings(view)
        current_state = settings["black_on_save"]
        next_state = not current_state

        # A setting set on a particular view overules all other places where
        # the same setting could have been set as well. E.g. project settings.
        # Now, we first `erase` such a view setting which is luckily an
        # operation that never throws, and immediately check again if the
        # wanted next state is fulfilled by that side effect.
        # If yes, we're almost done and just clean up the status area.
        view.settings().erase(BLACK_ON_SAVE_VIEW_SETTING)
        if utils.get_settings(view)["black_on_save"] == next_state:
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
        def _blackd_start():
            utils.start_blackd_server(self.view)

        sublime.set_timeout_async(_blackd_start, 0)


class BlackdStopCommand(sublime_plugin.ApplicationCommand):
    def is_enabled(self):
        return True

    is_visible = is_enabled

    def run(self):
        utils.get_log().debug("blackd_stop command running")
        if BlackdServer().stop_deamon():
            sublime.active_window().active_view().set_status(STATUS_KEY, BLACKD_STOPPED)
        else:
            sublime.active_window().active_view().set_status(STATUS_KEY, BLACKD_STOP_FAILED)


class BlackFormatAllCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return True

    is_visible = is_enabled

    def run(self):
        LOG = utils.get_log()
        if utils.get_settings(self.window.active_view())["black_confirm_formatall"]:
            if not sublime.ok_cancel_dialog(
                "Sublack: Format all?\nInfo: It runs black without sublack "
                "(ignoring sublack Options and Configuration)."
            ):
                return

        folders = self.window.folders()

        success = []
        errors = []
        dispatcher = None
        for folder in folders:
            p = utils.popen(
                ["black", "."], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=folder
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
                "black formatted folder %s with returncode %s and following en stderr :%s", *out
            )

        for out in errors:
            LOG.error(
                "black formatted folder %s with returncode %s and following en stderr :%s", *out
            )
