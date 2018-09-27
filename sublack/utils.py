import re
import sublime
from .consts import (
    CONFIG_OPTIONS,
    ENCODING_PATTERN,
    KEY_ERROR_MARKER,
    PACKAGE_NAME,
    SETTINGS_FILE_NAME,
    SETTINGS_NS_PREFIX,
)

from pathlib import Path
import subprocess
import signal
import os
from functools import partial
import socket
import requests
import logging

LOG = logging.getLogger("sublack")


def timed(fn):
    def to_time(*args, **kwargs):
        import time

        st = time.time()
        rev = fn(*args, **kwargs)
        end = time.time()
        print("durée {} {:.2f} ms".format(fn.__name__, (end - st) * 1000))
        return rev

    return to_time


def get_on_save_fast(view):
    """Fast checker for black_on_save setting"""
    flat_settings = view.settings()
    if flat_settings.get("sublack.black_on_save"):
        return True

    if flat_settings.get(PACKAGE_NAME, {}).get("black_on_save", False):
        return True

    if sublime.load_settings(SETTINGS_FILE_NAME).get("black_on_save"):
        return True

    return False


def get_settings(view):
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


def get_encoding_from_region(region, view):
    """
    ENCODING_PATTERN is given by PEP 263
    """

    ligne = view.substr(region)
    encoding = re.findall(ENCODING_PATTERN, ligne)

    return encoding[0] if encoding else None


def get_encoding_from_file(view):
    """
    get from 2nd line only If failed from 1st line.
    """
    region = view.line(sublime.Region(0))
    encoding = get_encoding_from_region(region, view)
    if encoding:
        return encoding
    else:
        encoding = get_encoding_from_region(view.line(region.end() + 1), view)
        return encoding
    return None


def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def cache_path():
    return Path(sublime.cache_path(), PACKAGE_NAME)


def startup_info():
    "running windows process in background"
    if sublime.platform() == "windows":
        st = subprocess.STARTUPINFO()
        st.dwFlags = (
            subprocess.STARTF_USESHOWWINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        st.wShowWindow = subprocess.SW_HIDE
        return st
    else:
        return None


def kill_with_pid(pid: int):
    if sublime.platform() == "windows":
        # need to properly kill precess traa
        subprocess.call(
            ["taskkill", "/F", "/T", "/PID", str(pid)], startupinfo=startup_info()
        )
    else:
        os.kill(pid, signal.SIGTERM)


popen = partial(subprocess.Popen, startupinfo=startup_info())


def check_blackd_on_http(port, host="localhost"):
    """Check if blackd is running and if tested port is free

    Returns: is_Running, is_Port_is_Free"""
    try:
        resp = requests.post("http://" + host + ":" + port, data="a=1")
    except requests.ConnectionError:
        return False, True
    else:

        if resp.content == b"a = 1\n":
            return True, False
        else:
            return False, False


def find_pyproject(view):
    """Only search in projects and folders since pyproject.toml should be nowhere else"""
    window = view.window()
    variables = window.extract_variables()
    # project path
    path = Path(variables.get("project_path", "")) / "pyproject.toml"
    LOG.debug("pyproject path %s", path)
    if path.exists():
        return path

    # folders
    folders = window.folders()

    for path in folders:
        LOG.debug("Folders : %s", path)
        path = Path(path) / "pyproject.toml"
        if path.exists():

            return path

    # nothing found
    return None


############################
# Let it like this wainting for toml depedency in package contrl
# https://github.com/wbond/package_control_channel/pull/7298
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import toml

###################""


def read_pyproject_toml(pyproject: Path) -> dict:
    """Return config options foud in pyproject
    """
    config = {}
    if not pyproject:
        LOG.debug("No pyproject.toml file found")
        return {}

    try:
        pyproject_toml = toml.load(str(pyproject))
        config = pyproject_toml.get("tool", {}).get("black", {})
    except (toml.TomlDecodeError, OSError) as e:
        LOG.error("Error reading configuration file: %s", pyproject)
        # pass

    LOG.debug("config values extracted from %s : %r", pyproject, config)
    return config
