from __future__ import annotations

import sublime
import sublime_plugin

from . import blacker
from . import consts
from . import server
from . import utils

_typing = False
if _typing:
    from typing import Any
del _typing


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

        blacker.Black(self.view)(edit)

        # re apply view position
        # fix : https://github.com/jgirardet/sublack/issues/52
        # not tested : view.run_command doesn't reproduce bug in tests...
        sublime.set_timeout_async(lambda: self.view.set_viewport_position(old_view_port), delay=25)


class BlackDiffCommand(sublime_plugin.TextCommand):
    """
    The "black_diff" command show a diff of the current document.
    """

    def is_enabled(self):
        return utils.is_python(self.view)

    is_visible = is_enabled

    def run(self, edit):
        utils.get_log().debug("running black_file")
        blacker.Black(self.view)(edit, extra=["--diff"])


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

    def run(self, _):
        view: sublime.View = self.view

        settings = utils.get_settings(view)
        current_state: bool = settings["black_on_save"]
        next_state = not current_state

        # A setting set on a particular view overules all other places where
        # the same setting could have been set as well. E.g. project settings.
        # Now, we first `erase` such a view setting which is luckily an
        # operation that never throws, and immediately check again if the
        # wanted next state is fulfilled by that side effect.
        # If yes, we're almost done and just clean up the status area.
        view.settings().erase(consts.BLACK_ON_SAVE_VIEW_SETTING)
        if utils.get_settings(view)["black_on_save"] == next_state:
            view.erase_status(consts.STATUS_KEY)
            return

        # Otherwise, we set the next state, and indicate in the status bar
        # that this view now deviates from the other views.
        view.settings().set(consts.BLACK_ON_SAVE_VIEW_SETTING, next_state)
        view.set_status(consts.STATUS_KEY, "black: {}".format("ON" if next_state else "OFF"))


class BlackdStartCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return True

    is_visible = is_enabled

    def run(self, _, **kwargs: Any):
        port = kwargs["port"] if kwargs and "port" in kwargs else None

        def _blackd_start():
            server.start_blackd_server(self.view, port=port)

        sublime.set_timeout_async(_blackd_start, 0)


class BlackdStopCommand(sublime_plugin.ApplicationCommand):
    def is_enabled(self):
        return True

    is_visible = is_enabled

    def run(self):
        utils.get_log().debug("blackd_stop command running")
        view = sublime.active_window().active_view()
        assert view, "No view found!"
        if server.stop_blackd_server():
            view.set_status(consts.STATUS_KEY, consts.BLACKD_STOPPED)
        else:
            view.set_status(consts.STATUS_KEY, consts.BLACKD_STOP_FAILED)


class BlackFormatAllCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return True

    is_visible = is_enabled

    def run(self):
        black_all = blacker.BlackAll(self.window)
        black_all.run()
