from __future__ import annotations

_typing = False
if _typing:
    from . import lib

    from typing import Any
del _typing

import importlib
import inspect
import pathlib


_vendor_local_path: pathlib.Path | None = None


def get_vendor_local_path() -> pathlib.Path:
    """
    Get the local path to the vendor sub-package
    """

    global _vendor_local_path
    if _vendor_local_path is None:
        _current_directory = pathlib.Path(inspect.getfile(lambda: None))
        _vendor_local_path = _current_directory.parent

    return _vendor_local_path


def __getattr__(name: str) -> Any:
    vendor_local_path = get_vendor_local_path()
    for sub_path in vendor_local_path.iterdir():
        if sub_path.name != name:
            continue

        return importlib.import_module(f"{__name__}.{name}")

    raise AttributeError(f"{__name__} has no attribute: {name}")


__all__ = (
    "lib",
)