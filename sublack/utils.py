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

import pathlib
import subprocess
import signal
import os
import locale
import socket
import requests
import logging
import yaml
import toml

LOG = logging.getLogger("sublack")


class Path(type(pathlib.Path())):
    def write_text(
        self, content, mode="w", buffering=-1, encoding=None, errors=None, newline=None
    ):

        with self.open(
            mode="w", buffering=-1, encoding=None, errors=None, newline=None
        ) as file:

            return file.write(content)

    def read_text(
        self, mode="w", buffering=-1, encoding=None, errors=None, newline=None
    ):

        with self.open(
            mode="r", buffering=-1, encoding=None, errors=None, newline=None
        ) as file:

            return file.read()


def timed(fn):
    def to_time(*args, **kwargs):
        import time

        st = time.time()
        rev = fn(*args, **kwargs)
        end = time.time()
        LOG.debug("durée {} {:.2f} ms".format(fn.__name__, (end - st) * 1000))
        return rev

    return to_time


def match_exclude(view):
    pyproject = find_pyproject(view)
    if pyproject:
        excluded = read_pyproject_toml(pyproject).get("exclude", None)
        if excluded:
            cur_fil = Path(view.file_name())
            try:
                rel_path = cur_fil.relative_to(pyproject.parent)
            except ValueError:
                LOG.debug("%s not in %s", cur_fil, pyproject.parent)
                return

            else:
                if re.match(excluded, "/" + str(rel_path), re.VERBOSE):
                    LOG.info("%s excluded from pyproject, aborting", rel_path)
                    return True


def get_on_save_fast(view):
    """Fast checker for black_on_save setting"""

    if match_exclude(view):
        return False

    flat_settings = view.settings()
    if flat_settings.has("sublack.black_on_save"):
        return flat_settings.get("sublack.black_on_save")

    if "black_on_save" in flat_settings.get(PACKAGE_NAME, {}):
        return flat_settings.has("sublack.black_on_save")

    return sublime.load_settings(SETTINGS_FILE_NAME).get("black_on_save")


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
        # st.dwFlags = (
        #     subprocess.STARTF_USESHOWWINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        # )
        st.dwFlags = subprocess.STARTF_USESHOWWINDOW
        st.wShowWindow = subprocess.SW_HIDE
        return st
    else:
        return None


def shell():
    """set shell to True on windows"""
    if sublime.platform() == "windows":
        return True
    else:
        False


def kill_with_pid(pid: int):
    if sublime.platform() == "windows":
        # need to properly kill precess traa
        subprocess.call(
            ["taskkill", "/F", "/T", "/PID", str(pid)], startupinfo=startup_info()
        )
    else:
        os.kill(pid, signal.SIGTERM)


def get_env():
    # modifying the locale is necessary to keep the click library happy on OSX
    env = os.environ.copy()
    if locale.getdefaultlocale() == (None, None):
        if sublime.platform() == "osx":
            env["LC_CTYPE"] = "UTF-8"
    return env


def popen(*args, **kwargs):
    return subprocess.Popen(*args, startupinfo=startup_info(), env=get_env(), **kwargs)
    # return subprocess.Popen(*args,shell=shell(), env=get_env(), **kwargs)


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


def find_root_file(view, filename):
    """Only search in projects and folders since pyproject.toml/precommit, ... should be nowhere else"""
    window = view.window()
    variables = window.extract_variables()
    # project path
    path = Path(variables.get("project_path", "")) / filename
    if path.exists():
        # LOG.debug("%s path %s", filename, path)
        return path

    # folders
    folders = window.folders()
    for path in folders:
        # LOG.debug("Folders : %s", path)
        path = Path(path) / filename
        if path.exists():

            LOG.debug("%s path %s", filename, path)
            return path

    # nothing found
    return None


def find_pyproject(view):
    pyproject = find_root_file(view, "pyproject.toml")
    if pyproject:
        return pyproject

    folders = [Path(f).resolve() for f in view.window().folders()]

    try:
        fname = view.file_name()
        if not fname:
            return
        cur_fil = Path(fname)
    except AttributeError:
        return

    for folder in cur_fil.parents:
        if (folder / "pyproject.toml").is_file():
            return folder / "pyproject.toml"

        if (folder / ".git").is_dir():
            return None

        if (folder / ".hg").is_dir():
            return None

        if folder.resolve() in folders:
            return None


def read_pyproject_toml(pyproject: Path) -> dict:
    """Return config options foud in pyproject"""
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

    # LOG.debug("config values extracted from %s : %r", pyproject, config)
    return config


def use_pre_commit(precommit: Path) -> bool:
    """Returns True if black in .pre-commit-config.yaml"""

    if not precommit:
        LOG.debug("No .pre-commit-config.yaml file found")
        return False

    config = yaml.load(precommit.read_text())
    if not config:
        return False

    if "repos" not in config:
        LOG.debug('.pre-commit-config.yaml has no "repos"')
        return False

    for repo in config["repos"]:
        if "https://github.com/ambv/black" == repo["repo"]:
            return precommit
        for hooks in repo["hooks"]:
            if hooks["id"] == "black":
                return precommit

    return False


def clear_cache():
    with (cache_path() / "formatted").open("wt") as file:
        file.write("")


def is_python3_executable(python_executable, default_shell=None):
    find_version = '{} -c "import sys;print(sys.version_info.major)"'.format(
        python_executable
    )
    default_shell = None

    if sublime.platform() != "windows":
        default_shell = os.environ.get("SHELL", "/bin/bash")

    try:
        version_out = subprocess.check_output(
            find_version, shell=True, executable=default_shell
        ).decode()

    except FileNotFoundError:
        LOG.debug("is_python3_executable : FileNotFoundError")
        return False

    except subprocess.CalledProcessError as err:
        LOG.debug("is_python3_executable : CalledProcessError %s", err)
        return False

    LOG.debug("version returned %s", version_out)
    if not version_out or version_out.strip() != "3":
        LOG.debug("%s is not a python3 executable", python_executable)
        return False

    else:
        return True


def find_python3_executable():
    if sublime.platform() == "windows":
        pythons = []
        # where could return many lines
        try:
            pythons = subprocess.check_output("where python", shell=True).decode()
        except subprocess.CalledProcessError:
            return False

        for python_executable in pythons.splitlines():
            if is_python3_executable(python_executable):
                return python_executable.strip()

    else:
        default_shell = os.environ.get("SHELL", None)
        paths = (
            re.search(
                r"(?m)^PATH=(.*)",
                subprocess.check_output("env", shell=True).decode(),
                # subprocess.check_output("bash -ilc env", shell=True).decode(),
            )
            .group(1)
            .split(":")
        )
        LOG.debug("paths found: %r", paths)

        # first look at python 3
        for path in paths:
            to_check = Path(path, "python3")
            if to_check.exists():
                return str(to_check)

        for path in paths:
            to_check = Path(path, "python")
            if to_check.exists() and is_python3_executable(to_check, default_shell):
                return str(to_check)

    LOG.debug("no valid interpreter found via find_python3_executable")
    return False


def get_python3_executable(config=None):

    # First check for python3/python in path
    for version in ["python3", "python"]:
        if is_python3_executable(version):
            LOG.debug("using %s as python interpreter", version)
            return version
        LOG.debug("No valid python found using only python3/python")

    # then find  one via shell
    python_exec = find_python3_executable()
    if python_exec:
        LOG.debug("using %s as python3 interpreter found", python_exec)
        return python_exec

    # third: guess from black_command
    if config:
        if config["black_command"] != "black":
            python_exec = str(Path(config["black_command"]).parent / "python")
            LOG.debug("guessing from black_command")
            if is_python3_executable(python_exec):
                LOG.debug(
                    "using %s as python3 interpreter guess from black_command",
                    python_exec,
                )

                return python_exec

    LOG.debug("no valid python3 interpreter was found")

    return False  # nothing found
