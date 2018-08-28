import sublime_plugin
from .consts import BLACK_ON_SAVE_VIEW_SETTING, STATUS_KEY
from .utils import get_settings
from .blacker import Black
import logging


LOG = logging.getLogger("sublack")


def is_python(view):
    return view.match_selector(0, "source.python")


class BlackFileCommand(sublime_plugin.TextCommand):
    """
    The "black_file" command formats the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    is_visible = is_enabled

    def run(self, edit):
        LOG.debug("[SUBLACK] : run black_file")
        Black(self.view)(edit)


class BlackDiffCommand(sublime_plugin.TextCommand):
    """
    The "black_diff" command show a diff of the current document.
    """

    def is_enabled(self):
        return is_python(self.view)

    is_visible = is_enabled

    def run(self, edit):
        LOG.debug("[SUBLACK] : run black_diff")
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


class EventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if get_settings(view)["black_on_save"]:
            view.run_command("black_file")

    def on_post_text_command(self, view, command_name, args):
        if command_name == "black_file":
            view.show(view.line(view.sel()[0]))
