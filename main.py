"""
Sublack

Order of imports should not be changed
"""
import logging
import sys

import sublime

from .sublack import *  # noqa
from . import sublack

sys.modules["sublack"] = sublack

from sublack.utils import cache_path
from sublack.consts import PACKAGE_NAME


LOG = logging.getLogger(PACKAGE_NAME)
LOG.propagate = False


def plugin_loaded():
    # load config
    current_view = sublime.active_window().active_view()
    config = sublack.utils.get_settings(current_view)

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
        LOG.setLevel(config.get("black_log", "").upper())
    except ValueError as err:
        LOG.error(err)
        LOG.setLevel("ERROR")
        LOG.error("fallback to loglevel ERROR")

    LOG.info("Loglevel set to %s", config["black_log"].upper())

    # check cache_path
    cp = cache_path()
    if not cp.exists():
        cp.mkdir()

    # check blackd autostart
    # if config["black_blackd_autostart"]:
    #     current_view.run_command("blackd_start")
