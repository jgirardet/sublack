from __future__ import annotations

import inspect
import pathlib
import site


_vendor_package_path: pathlib.Path | None = None

def get_vendor_package_path() -> pathlib.Path:
	global _vendor_package_path
	if _vendor_package_path is None:
		_current_directory = pathlib.Path(inspect.getfile(lambda: None))
		_vendor_package_path = _current_directory.parent

	return _vendor_package_path

site.addsitedir(str(get_vendor_package_path()))

