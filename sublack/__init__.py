from __future__ import annotations

import site

site.addsitedir(r"D:\Code\Git\_venvs\debugpy\Lib\site-packages")

import debugpy

debugpy.configure(python="C:/Program Files/Python38/python.exe")
debugpy.listen(("localhost", 5678))
debugpy.wait_for_client()


from .consts import *
from .utils import (
    cache_path,
    clear_cache,
    get_log,
    get_on_save_fast,
    get_open_port,
    get_settings,
    is_python,
    kill_with_pid,
    popen,
    get_startup_info,
)
from .server import BlackdServer
from .blacker import Black
from .blacker import Blackd
from .commands import (
    BlackDiffCommand,
    BlackdStartCommand,
    BlackdStopCommand,
    BlackFileCommand,
    BlackFormatAllCommand,
    BlackToggleBlackOnSaveCommand,
)

__all__ = (
    "Black",
    "Blackd",
    "BlackDiffCommand",
    "BlackdServer",
    "BlackdStartCommand",
    "BlackdStopCommand",
    "BlackFileCommand",
    "BlackFormatAllCommand",
    "BlackToggleBlackOnSaveCommand",
    "cache_path",
    "clear_cache",
    "get_log",
    "get_on_save_fast",
    "get_open_port",
    "get_settings",
    "is_python",
    "kill_with_pid",
    "PACKAGE_NAME",
    "popen",
    "get_startup_info",
)
