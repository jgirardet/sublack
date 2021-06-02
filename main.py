"""
Sublack

Order of imports should not be changed
"""

import logging
import sublime
import os
from .sublack import (
    PACKAGE_NAME,
    SETTINGS_FILE_NAME,
    get_settings,
    cache_path,
    clear_cache,
    Path,
    BlackFileCommand,
    BlackDiffCommand,
    BlackToggleBlackOnSaveCommand,
    BlackEventListener,
    BlackdStartCommand,
    BlackdStopCommand,
    BlackFormatAllCommand,
    utils
)  # flake8: noqa

LOG = logging.getLogger(PACKAGE_NAME)

if not os.environ.get("CI", None):
    LOG.propagate = False


def plugin_loaded():
    # load config
    current_view = sublime.active_window().active_view()
    config = get_settings(current_view)
    if not config:
        LOG.error("Settings were not loaded")
        return
    if config["black_log"] == None:
        config["black_log"] = "info"
    # Setup  logging
    if not LOG.handlers:
        debug_formatter = logging.Formatter(
            "[{}:%(filename)s](%(levelname)s) %(message)s".format(PACKAGE_NAME)
        )
        dh = logging.StreamHandler()
        dh.setLevel(logging.DEBUG)
        dh.setFormatter(debug_formatter)
        LOG.addHandler(dh)

    try:
        LOG.setLevel(config.get("black_log").upper())
    except ValueError as err:  # https://forum.sublimetext.com/t/an-odd-problem-about-sublime-load-settings/30335/6
        LOG.error(err)
        LOG.setLevel("ERROR")
        LOG.error("fallback to loglevel ERROR")

    LOG.info("Loglevel set to %s", config["black_log"].upper())

    # check cache_path
    cp = cache_path()
    if not cp.exists():
        cp.mkdir()

    # clear cache
    clear_cache()

    # check blackd autostart
    if config["black_blackd_autostart"]:

        def _blackd_start():
            from .sublack import utils
            utils.start_blackd_server(current_view)

        sublime.set_timeout_async(_blackd_start, 0)

    # watch for loglevel change
    sublime.load_settings(SETTINGS_FILE_NAME).add_on_change(
        "black_log", lambda: Path(__file__).touch()
    )
