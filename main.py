"""
Sublack
"""

import pathlib
import sublime
import sublime_plugin

from . import sublack
from .sublack import server
from .sublack import utils
from .sublack.commands import *


def plugin_loaded():
    current_view = sublime.active_window().active_view()
    if current_view is None:
        utils.get_log().error("No active view found!")
        return

    settings = sublack.get_settings(current_view)
    if not settings:
        raise IOError("Settings were not loaded!")

    # check sublack.cache_path
    cp = sublack.cache_path()
    if not cp.exists():
        cp.mkdir()

    # clear cache
    sublack.clear_cache()

    # check blackd autostart
    if settings["black_blackd_autostart"]:

        def _blackd_start():
            server.start_blackd_server(current_view)

        sublime.set_timeout_async(_blackd_start, 0)

    # watch for loglevel change
    sublime.load_settings(sublack.SETTINGS_FILE_NAME).add_on_change(
        "black_log", lambda: pathlib.Path(__file__).touch()
    )


def plugin_unloaded():
    return server.stop_blackd_server()


class BlackEventListener(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        """use blackd at saving time

        Cannot be async since black should be run before save"""
        if sublack.get_on_save_fast(view):
            view.run_command("black_file")

    def on_post_text_command(self, view: sublime.View, command_name: str, _):
        if command_name == "black_file":
            view.show(view.line(view.sel()[0]))

    def on_exit(self):
        """
        Shutdown blackd when sublime shuts down
        """

        log = sublack.get_log()
        log.debug("on_exit")
        plugin_unloaded()
