from __future__ import annotations


def _setup_vendor_packages():
    import pathlib as pathlib
    import site

    current_directory = pathlib.Path(__file__).parent
    vendor_packages_path = current_directory / "vendor/packages"
    site.addsitedir(str(vendor_packages_path))
    print(f"Added packages site path: {vendor_packages_path}")


_setup_vendor_packages()

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
# from .server import BlackdServer
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
    # "BlackdServer",
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

