import logging
import sublime

from ._sublack.commands import *  # noqa
from ._sublack.utils import get_settings

LOG = logging.getLogger("sublack")
# handler = logging.StreamHandler()
# LOG.addHandler(handler)
LOG.setLevel(logging.INFO)


def plugin_loaded():

    # set logLevel
    current_view = sublime.active_window().active_view()
    config = get_settings(current_view)
    if config["black_debug_on"]:
        LOG.setLevel(logging.DEBUG)
