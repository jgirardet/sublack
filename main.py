"""
Sublack

Order of imports should not be changed
"""

import logging
import sublime
import sublime_plugin

from . import sublack
from .sublack import (
    BlackDiffCommand,
    BlackdStartCommand,
    BlackdStopCommand,
    BlackFileCommand,
    BlackFormatAllCommand,
    BlackToggleBlackOnSaveCommand,
)


def plugin_loaded():

    # load config
    current_view = sublime.active_window().active_view()
    settings = sublack.get_settings(current_view)
    if not settings:
        raise IOError("Settings were not loaded!")

    sublack.get_log(settings=settings)
    # check sublack.cache_path
    cp = sublack.cache_path()
    if not cp.exists():
        cp.mkdir()

    # clear cache
    sublack.clear_cache()

    # check blackd autostart
    if settings["black_blackd_autostart"]:

        def _blackd_start():
            sublack.start_blackd_server(current_view)

        sublime.set_timeout_async(_blackd_start, 0)

    # watch for loglevel change
    sublime.load_settings(sublack.SETTINGS_FILE_NAME).add_on_change(
        "black_log", lambda: sublack.Path(__file__).touch()
    )


def plugin_unloaded():

    return sublack.shutdown_blackd()


class BlackEventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        """use blackd at saving time

        Cannot be async since black should be run before save"""
        if sublack.get_on_save_fast(view):
            view.run_command("black_file")

    def on_post_text_command(self, view, command_name, args):
        if command_name == "black_file":
            view.show(view.line(view.sel()[0]))

    def on_exit(self):

        log = sublack.get_log()
        log.debug("on_exit")
        sublack.shutdown_blackd()


# class TestEventListener(sublime_plugin.EventListener):

#     def on_exit(self):

#         log = sublack.get_log()
#         log.debug("on_exit")

#     def on_pre_close_window(self, window):

#         log = sublack.get_log()
#         log.debug("on_pre_close_window")
