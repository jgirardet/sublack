""" sublack
    

   isort:skip_file
"""

import sys

import logging
import sublime
import sys, os

sys.path.append(os.path.dirname(__file__))


LOG = logging.getLogger("sublack")
handler = logging.StreamHandler()
LOG.addHandler(handler)
LOG.setLevel(logging.INFO)


from .sublack import *  # noqa
import sublack

# from . import sublack


sys.modules["sublack"] = sublack


def plugin_loaded():

    # set logLevel
    current_view = sublime.active_window().active_view()
    config = sublack.utils.get_settings(current_view)
    if config["black_debug_on"]:
        LOG.setLevel(logging.DEBUG)
