from __future__ import annotations
import multiprocessing

import sublime

import functools
import locale
import logging
import os
import pathlib
import re
import signal
import socket
import subprocess
import time

from . import vendor
from .consts import CONFIG_OPTIONS
from .consts import ENCODING_PATTERN
from .consts import KEY_ERROR_MARKER
from .consts import PACKAGE_NAME
from .consts import SETTINGS_FILE_NAME
from .consts import SETTINGS_NS_PREFIX

_typing = False
if _typing:
    from typing import Any
del _typing

_has_blackd_started = False
_depth_count = 0
_log = None


def get_log(settings: dict[str, Any] | None = None) -> logging.Logger:
    """
    Generate a logger for sublack.
    """

    global _log
    if _log is None:
        _log = logging.getLogger(PACKAGE_NAME)
        # Prevent duplicate log items from being created if the module is reloaded:
        if _log.handlers:
            return _log

        settings = (
            get_settings(sublime.active_window().active_view()) if settings is None else settings
        )
        debug_formatter = logging.Formatter(
            "[{pn}:%(filename)s.%(funcName)s-%(lineno)d](%(levelname)s) %(message)s".format(
                pn=PACKAGE_NAME
            )
        )
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(debug_formatter)
        stream_handler.setLevel(logging.DEBUG)
        _log.addHandler(stream_handler)
        if settings["black_log_to_file"]:
            try:
                fh = logging.FileHandler("sublack.log")
                fh.setFormatter(debug_formatter)
                fh.setLevel(level=logging.DEBUG)
                _log.addHandler(fh)
            except PermissionError as err:
                _log.debug("Unable to create sublack file log:\n - {}".format(err))

        if settings["black_log"] is None:
            settings["black_log"] = "info"

        try:
            _log.setLevel(settings.get("black_log").upper())
        except ValueError as err:  # https://forum.sublimetext.com/t/an-odd-problem-about-sublime-load-settings/30335/6
            _log.error(err)
            _log.setLevel("ERROR")
            _log.error("fallback to loglevel ERROR")

        _log.info("Loglevel set to {l}".format(l=settings["black_log"].upper()))

        if not os.environ.get("CI", None):
            _log.propagate = False

    return _log


@functools.lru_cache()
def get_platform() -> str:
    return sublime.platform().lower()


@functools.lru_cache()
def is_windows() -> bool:
    return get_platform() == "windows"


def timed(fn):
    @functools.wraps(fn)
    def to_time(*args, **kwargs):

        st = time.time()
        rev = fn(*args, **kwargs)
        end = time.time()
        get_log().debug("Time: {} {:.2f} ms".format(fn.__name__, (end - st) * 1000))
        return rev

    return to_time


def has_blackd_started() -> bool:
    global _has_blackd_started
    return _has_blackd_started


def set_has_blackd_started(value : bool) -> None:
    global _has_blackd_started
    _has_blackd_started = value


def match_exclude(view: sublime.View) -> bool:
    log = get_log()
    pyproject = find_pyproject(view)
    if not pyproject:
        return False

    excluded = read_pyproject_toml(pyproject).get("exclude", None)
    if not excluded:
        return False

    file_name = view.file_name()
    if not file_name:
        log.debug("File is not saved!")
        return False

    current_file = pathlib.Path(file_name)
    try:
        rel_path = current_file.relative_to(pyproject.parent)
    except ValueError:
        log.debug("%s not in %s", current_file, pyproject.parent)
        return False

    else:
        if re.match(excluded, "/" + str(rel_path), re.VERBOSE):
            log.info("%s excluded from pyproject, aborting", rel_path)
            return True

    return False


def get_on_save_fast(view: sublime.View):
    """Fast checker for black_on_save setting"""

    if match_exclude(view):
        return False

    flat_settings = view.settings()
    if flat_settings.has("sublack.black_on_save"):
        return flat_settings.get("sublack.black_on_save")

    if "black_on_save" in flat_settings.get(PACKAGE_NAME, {}):
        return flat_settings.has("sublack.black_on_save")

    return sublime.load_settings(SETTINGS_FILE_NAME).get("black_on_save")


def get_settings(view: sublime.View) -> dict[str, Any]:
    flat_settings = view.settings()
    nested_settings = flat_settings.get(PACKAGE_NAME, {})
    global_settings = sublime.load_settings(SETTINGS_FILE_NAME)
    pyproject_settings = read_pyproject_toml(find_pyproject(view))
    settings = {}

    for k in CONFIG_OPTIONS:
        # 1. pyproject
        value = pyproject_settings.get(k[6:].replace("_", "-"), None)
        if value:
            settings[k] = value
            continue

        # 2. check sublime "flat settings"
        value = flat_settings.get(SETTINGS_NS_PREFIX + k, KEY_ERROR_MARKER)
        if value != KEY_ERROR_MARKER:
            settings[k] = value
            continue

        # 3. check sublieme "nested settings" for compatibility reason
        value = nested_settings.get(k, KEY_ERROR_MARKER)
        if value != KEY_ERROR_MARKER:
            settings[k] = value
            continue

        # 4. check plugin/user settings
        settings[k] = global_settings.get(k)

    return settings


def is_python(view: sublime.View) -> bool:

    return view.match_selector(0, "source.python")


def get_encoding_from_region(region: sublime.Region, view: sublime.View) -> str:
    """
    ENCODING_PATTERN is given by PEP 263
    """

    ligne = view.substr(region)
    encoding = re.findall(ENCODING_PATTERN, ligne)

    return encoding[0] if encoding else ""


def get_encoding_from_file(view: sublime.View) -> str:
    """
    Get from 2nd line only If failed from 1st line.
    """

    region = view.line(sublime.Region(0))
    encoding = get_encoding_from_region(region, view)
    if encoding:
        return encoding
    else:
        encoding = get_encoding_from_region(view.line(region.end() + 1), view)
        return encoding


def get_encoding(settings=None) -> str:
    view = sublime.active_window().active_view()
    assert view
    encoding = view.encoding()
    if encoding == "Undefined":
        encoding = get_encoding_from_file(view)

    if not encoding:
        settings = settings or get_settings(view)
        encoding = settings["black_default_encoding"]

    return encoding


def get_open_port() -> str:
    _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _socket.bind(("", 0))
    port = _socket.getsockname()[1]
    _socket.close()
    return port


@functools.lru_cache()
def get_startup_info() -> subprocess.STARTUPINFO | None:
    if not is_windows():
        return

    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE
    return startup_info


@functools.lru_cache()
def get_black_executable_command(vendor: bool = False) -> str:
    log = get_log()
    view = sublime.active_window().active_view()
    settings = get_settings(view)
    # use_blackd: bool = settings["black_use_blackd"]
    # if use_blackd:
    #     blackd_path = get_vendor_blackd_path()
    #     blackd_command = f"{blackd_path} --bind-host {} --bind-port {}"
    #     multiprocessing
    #     return
    user_black_command: str = settings["black_command"]
    black_command = get_vendor_black_exe_path() if vendor else user_black_command
    black_command = black_command or get_vendor_black_exe_path()
    # default_shell = os.environ.get("SHELL", "/bin/bash") if get_platform() != "windows" else None
    # print(f"black_command: {black_command}")
    try:
        subprocess.run(
            black_command,
            capture_output=True,
            universal_newlines=True,
            input="def test(): return",
            startupinfo=get_startup_info(),
        )
        return black_command

    except FileNotFoundError:
        log.debug(f"Black command could not be found: {black_command}. Using vendored path.")
        if black_command == get_vendor_black_exe_path():
            message_text = f"Vendored black path was not found: {black_command}!"
            log.critical(message_text)
            sublime.error_message(message_text)
            raise

        return get_black_executable_command(vendor=True)

    except subprocess.CalledProcessError as error:
        log.debug(f"Black command failed to run:\n {error}.\nUsing vendored path.")
        if black_command == get_vendor_black_exe_path():
            message_text = "Vendored black path failed to run!"
            log.critical(f"{message_text}:\n - {black_command}!")
            sublime.error_message(message_text)
            raise

        return get_black_executable_command(vendor=True)


@functools.lru_cache()
def get_vendor_black_exe_path() -> str:
    vendor_local_path = vendor.get_vendor_local_path()
    return str(vendor_local_path / ".venv/Scripts/black")


@functools.lru_cache()
def get_vendor_blackd_path() -> str:
    vendor_local_path = vendor.get_vendor_local_path()
    return str(vendor_local_path / "python/windows/Lib/blackd")


@functools.lru_cache()
def get_vendor_python_exe_path() -> pathlib.Path:
    vendor_local_path = vendor.get_vendor_local_path()
    return vendor_local_path / "python/windows/python.exe"


@functools.lru_cache()
def cache_path() -> pathlib.Path:
    return pathlib.Path(sublime.cache_path(), PACKAGE_NAME)


def shell() -> bool:
    """set shell to True on windows"""
    if is_windows():
        return True
    return False


def kill_with_pid(pid: int) -> None:
    get_log().debug("kill_with_pid")
    # return os.kill(pid, signal.SIGTERM)
    if is_windows():
        # need to properly kill precess traa
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], startupinfo=get_startup_info())
        get_log().debug(f"blackd server with pid: {pid} destroyed!")
        return

    os.kill(pid, signal.SIGTERM)


def get_env() -> dict:
    # modifying the locale is necessary to keep the click library happy on OSX
    env = os.environ.copy()
    if locale.getdefaultlocale() == (None, None):
        if get_platform() == "osx":
            env["LC_CTYPE"] = "UTF-8"
    return env


def popen(*args, **kwargs) -> subprocess.Popen[str]:
    _startup_info = get_startup_info()
    _env = get_env()
    return subprocess.Popen(
        *args,
        startupinfo=_startup_info,
        env=_env,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        **kwargs
    )


# @timed
def is_port_free(port: str, host: str = "localhost") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _socket:
        response = _socket.connect_ex((host, int(port)))
        get_log().debug("response: {}".format(response))
        return response == 10061


# @timed
def is_blackd_running_on_port(port: str, host: str = "localhost") -> bool:
    """
    Check if blackd is running and if tested port is free

    Returns: is_Running, is_Port_is_Free
    """
    from .vendor.packages import requests

    log = get_log()
    try:
        response = requests.post("http://{h}:{p}/".format(h=host, p=port), data="a=1")

    except requests.ConnectionError as err:
        log.error("Connection Error:\n - {}".format(err))
        return False

    else:
        log.debug("response.content: {}".format(response.content))
        if response.content == b"a = 1\n":
            return True

        return False


def find_root_file(view: sublime.View, filename:str) -> pathlib.Path | None:
    """Only search in projects and folders since pyproject.toml/precommit, ... should be nowhere else"""
    log = get_log()
    window = view.window()

    filepath = window.extract_variables().get("file_path", None)
    if not filepath:
        return
    filepath = pathlib.Path(filepath)

    folders = []
    for folder in window.folders():
        path = pathlib.Path(folder)
        if path in filepath.parents:
            folders.append(path)

    if not folders:
        return

    root = min(folders)
    for parent in filepath.parents:
        if parent < root:
            break

        path = pathlib.Path(parent) / filename
        if path.exists():
            log.debug("filename:{f} path:{p}".format(f=filename, p=path))
            return path

    return


def find_pyproject(view: sublime.View) -> pathlib.Path | None:
    pyproject = find_root_file(view, "pyproject.toml")
    if pyproject:
        return pyproject

    folders = [pathlib.Path(f).resolve() for f in view.window().folders()]

    try:
        fname = view.file_name()
        if not fname:
            return
        cur_fil = pathlib.Path(fname)
    except AttributeError:
        return

    # La suite fait probablement doublon avec find_root_file
    for folder in cur_fil.parents:
        if (folder / "pyproject.toml").is_file():
            return folder / "pyproject.toml"

        if (folder / ".git").is_dir():
            return

        if (folder / ".hg").is_dir():
            return

        if folder.resolve() in folders:
            return


def read_pyproject_toml(pyproject: pathlib.Path | None) -> dict:
    """Return config options foud in pyproject"""

    from .vendor.packages import toml

    log = get_log()
    config = {}
    if pyproject is None:
        log.debug("No pyproject.toml file found")
        return {}

    try:
        pyproject_toml = toml.load(str(pyproject))
        config = pyproject_toml.get("tool", {}).get("black", {})
    except (toml.TomlDecodeError, OSError) as err:
        log.error("Error reading configuration file: {pr}, {err}".format(pr=pyproject, err=err))

    # log.debug("config values extracted from %s : %r", pyproject, config)
    return config


def use_pre_commit(precommit: pathlib.Path) -> bool:
    """Returns True if black in .pre-commit-config.yaml"""

    from .vendor.packages import yaml

    log = get_log()
    if not precommit:
        log.debug("No .pre-commit-config.yaml file found")
        return False

    config = yaml.load(precommit.read_text(), Loader=yaml.FullLoader)
    if not config:
        return False

    if "repos" not in config:
        log.debug('.pre-commit-config.yaml has no "repos"')
        return False

    for repo in config["repos"]:
        if "https://github.com/ambv/black" == repo["repo"]:
            return precommit
        for hooks in repo["hooks"]:
            if hooks["id"] == "black":
                return precommit

    return False


def clear_cache() -> None:
    with (cache_path() / "formatted").open("wt") as file:
        file.write("")


def format_log_data(data: dict[str, Any] | list[Any] | Any, key: str | None = None) -> str:
    global _depth_count
    message = ""
    dash_string = "-" * _depth_count
    if isinstance(data, dict):
        if key:
            message = "{msg}{ds} {k}:".format(msg=message, ds=dash_string, k=key)

        _depth_count += 1
        for key, value in data.items():
            message = "{msg}\n{v}".format(msg=message, v=format_log_data(value, key=key))

        _depth_count -= 1

    elif isinstance(data, list):
        if key:
            message = "{msg}{ds} {k}:".format(msg=message, ds=dash_string, k=key)

        _depth_count += 1
        for value in data:
            message = "{msg}\n{v}".format(msg=message, v=format_log_data(value))

        _depth_count -= 1

    else:
        if key:
            message = "{msg}{ds} {k}: {v}".format(msg=message, ds=dash_string, k=key, v=data)

        else:
            message = "{msg}{ds} {v}".format(msg=message, ds=dash_string, v=data)

    return message
