import functools
import locale
import logging
import os
import pathlib
import re
import requests
import signal
import socket
import sublime
import subprocess
import time
import toml
import yaml

from .consts import (
    BLACKD_ALREADY_RUNNING,
    BLACKD_START_FAILED,
    BLACKD_STARTED,
    CONFIG_OPTIONS,
    ENCODING_PATTERN,
    KEY_ERROR_MARKER,
    PACKAGE_NAME,
    SETTINGS_FILE_NAME,
    SETTINGS_NS_PREFIX,
    STATUS_KEY,
)


_has_blackd_started = False
_depth_count = 0
_LOG_ = None


def get_log(settings=None) -> logging.Logger:

    global _LOG_
    if _LOG_ is None:
        _LOG_ = logging.getLogger(PACKAGE_NAME)
        # Prevent duplicate log items from being created if the module is reloaded:
        if _LOG_.handlers:
            return _LOG_

        settings = (
            get_settings(sublime.active_window().active_view()) if settings is None else settings
        )
        debug_formatter = logging.Formatter(
            "[{pn}:%(filename)s.%(funcName)s-%(lineno)d](%(levelname)s) %(message)s".format(
                pn=PACKAGE_NAME
            )
        )
        sh = logging.StreamHandler()
        sh.setFormatter(debug_formatter)
        sh.setLevel(logging.DEBUG)
        _LOG_.addHandler(sh)
        if settings["black_log_to_file"]:

            try:
                fh = logging.FileHandler("sublack.log")
                fh.setFormatter(debug_formatter)
                fh.setLevel(level=logging.DEBUG)
                _LOG_.addHandler(fh)

            except PermissionError as err:
                _LOG_.debug("Unable to create sublack file log:\n - {}".format(err))

        if settings["black_log"] is None:
            settings["black_log"] = "info"

        try:
            _LOG_.setLevel(settings.get("black_log").upper())
        except ValueError as err:  # https://forum.sublimetext.com/t/an-odd-problem-about-sublime-load-settings/30335/6
            _LOG_.error(err)
            _LOG_.setLevel("ERROR")
            _LOG_.error("fallback to loglevel ERROR")

        _LOG_.info("Loglevel set to {l}".format(l=settings["black_log"].upper()))

        if not os.environ.get("CI", None):
            _LOG_.propagate = False

    return _LOG_


class Path(type(pathlib.Path())):
    def write_text(self, content, mode="w", buffering=-1, encoding=None, errors=None, newline=None):

        with self.open(mode="w", buffering=-1, encoding=None, errors=None, newline=None) as file:

            return file.write(content)

    def read_text(self, mode="w", buffering=-1, encoding=None, errors=None, newline=None):

        with self.open(mode="r", buffering=-1, encoding=None, errors=None, newline=None) as file:

            return file.read()


@functools.lru_cache()
def get_platform():

    return sublime.platform().lower()


@functools.lru_cache()
def is_windows():

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


def has_blackd_started():
    global _has_blackd_started
    return _has_blackd_started


def set_has_blackd_started(value):
    global _has_blackd_started
    _has_blackd_started = value
    return value


def start_blackd_server(view):
    from . import server

    if has_blackd_started():
        return

    LOG = get_log()
    set_has_blackd_started(False)
    LOG.debug("start_blackd_server executed")
    if view is None:
        LOG.debug("No valid view found!")
        set_has_blackd_started(False)
        return

    started = None
    settings = get_settings(view)
    port = settings["black_blackd_port"]
    if not port:
        LOG.info("No valid port given, defaulting to 45484")
        port = "45484"

    port_free = is_port_free(port)
    LOG.debug("port_free: {}".format(port_free))
    if port_free:
        LOG.info("Creating new BlackdServer")
        blackd_server = server.BlackdServer(
            deamon=True, host="localhost", port=port, settings=settings
        )
        started = blackd_server.run()

    else:
        running = is_blackd_running_on_port(port)
        LOG.debug("running: {}".format(running))
        if running:
            LOG.info(BLACKD_ALREADY_RUNNING.format(port))
            view.set_status(STATUS_KEY, BLACKD_ALREADY_RUNNING.format(port))
            set_has_blackd_started(True)
            return

        LOG.info("Creating new BlackdServer")
        blackd_server = server.BlackdServer(
            deamon=True, host="localhost", port=port, settings=settings
        )
        started = blackd_server.run()

    if started:
        LOG.info(BLACKD_STARTED.format(port))
        view.set_status(STATUS_KEY, BLACKD_STARTED.format(port))
        sublime.set_timeout_async(lambda: view.set_status(STATUS_KEY, ""), 2000)
        set_has_blackd_started(True)

    else:
        LOG.info(BLACKD_START_FAILED.format(port))
        view.set_status(STATUS_KEY, BLACKD_START_FAILED.format(port))
        set_has_blackd_started(False)


def match_exclude(view):
    LOG = get_log()
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


def get_settings(view) -> dict:
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


def is_python(view) -> bool:

    return view.match_selector(0, "source.python")


def get_encoding_from_region(region, view) -> str:
    """
    ENCODING_PATTERN is given by PEP 263
    """

    ligne = view.substr(region)
    encoding = re.findall(ENCODING_PATTERN, ligne)

    return encoding[0] if encoding else ""


def get_encoding_from_file(view) -> str:
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


def get_open_port() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@functools.lru_cache()
def cache_path() -> Path:

    return Path(sublime.cache_path(), PACKAGE_NAME)


@functools.lru_cache()
def startup_info():
    get_log().debug("Running windows process in background")
    if is_windows():
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = subprocess.SW_HIDE
        return startup_info
    else:
        return None


def shell() -> bool:
    """set shell to True on windows"""
    if is_windows():
        return True
    return False


def kill_with_pid(pid: int) -> None:
    if is_windows():
        # need to properly kill precess traa
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(pid)], startupinfo=startup_info())
    else:
        os.kill(pid, signal.SIGTERM)


def get_env() -> dict:
    # modifying the locale is necessary to keep the click library happy on OSX
    env = os.environ.copy()
    if locale.getdefaultlocale() == (None, None):
        if get_platform() == "osx":
            env["LC_CTYPE"] = "UTF-8"
    return env


def popen(*args, **kwargs):
    _startup_info = startup_info()
    _get_env = get_env()
    return subprocess.Popen(*args, startupinfo=_startup_info, env=_get_env, **kwargs)
    # return subprocess.Popen(*args,shell=shell(), env=get_env(), **kwargs)


@timed
def is_port_free(port: str, host: str = "localhost") -> bool:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        response = s.connect_ex((host, int(port)))
        get_log().debug("response: {}".format(response))
        return response == 10061


@timed
def is_blackd_running_on_port(port: str, host: str = "localhost") -> bool:
    """Check if blackd is running and if tested port is free

    Returns: is_Running, is_Port_is_Free"""

    LOG = get_log()
    try:
        resp = requests.post("http://{h}:{p}/".format(h=host, p=port), data="a=1")

    except requests.ConnectionError as err:
        LOG.error("Connection Error:\n - {}".format(err))
        return False

    else:

        LOG.debug("resp.content: {}".format(resp.content))
        if resp.content == b"a = 1\n":
            return True

        return False


def find_root_file(view, filename):
    """Only search in projects and folders since pyproject.toml/precommit, ... should be nowhere else"""
    LOG = get_log()
    window = view.window()

    filepath = window.extract_variables().get("file_path", None)
    if not filepath:
        return
    filepath = Path(filepath)

    # folders
    folders = []
    for f in window.folders():
        p = Path(f)
        if p in filepath.parents:
            folders.append(p)

    if folders:
        root = min(folders)
    else:
        return

    for parent in filepath.parents:
        # LOG.debug("Folders : %s", path)
        if parent < root:
            break
        path = Path(parent) / filename
        if path.exists():

            LOG.debug("filename:{f} path:{p}".format(f=filename, p=path))
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


def read_pyproject_toml(pyproject: Path) -> dict:
    """Return config options foud in pyproject"""
    LOG = get_log()
    config = {}
    if not pyproject:
        LOG.debug("No pyproject.toml file found")
        return {}

    try:
        pyproject_toml = toml.load(str(pyproject))
        config = pyproject_toml.get("tool", {}).get("black", {})
    except (toml.TomlDecodeError, OSError) as err:
        LOG.error("Error reading configuration file: {pr}, {err}".format(pr=pyproject, err=err))
        # pass

    # LOG.debug("config values extracted from %s : %r", pyproject, config)
    return config


def use_pre_commit(precommit: Path) -> bool:
    """Returns True if black in .pre-commit-config.yaml"""

    LOG = get_log()
    if not precommit:
        LOG.debug("No .pre-commit-config.yaml file found")
        return False

    config = yaml.load(precommit.read_text(), Loader=yaml.FullLoader)
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


def clear_cache() -> None:
    with (cache_path() / "formatted").open("wt") as file:
        file.write("")


@functools.lru_cache()
def is_python3_executable(python_executable: str, default_shell=None) -> bool:
    LOG = get_log()
    find_version = '{} -c "import sys;print(sys.version_info.major)"'.format(python_executable)
    default_shell = None

    if get_platform() != "windows":
        default_shell = os.environ.get("SHELL", "/bin/bash")

    try:
        version_out = subprocess.check_output(
            find_version, shell=True, executable=default_shell
        ).decode()

    except FileNotFoundError as err:
        LOG.debug("is_python3_executable - FileNotFoundError:\n - {e}".format(e=err))
        return False

    except subprocess.CalledProcessError as err:
        LOG.debug("is_python3_executable - CalledProcessError:\n - {e}".format(e=err))
        return False

    LOG.debug("Version returned {v}".format(v=version_out).strip())
    if not version_out or version_out.strip() != "3":
        LOG.debug("{pe} is not a python3 executable!".format(pe=python_executable))
        return False

    return True


@functools.lru_cache()
def find_python3_executable() -> str:
    LOG = get_log()
    LOG.debug("Platform: {p}".format(p=get_platform()))
    if is_windows():
        # where could return many lines
        try:
            pythons = subprocess.check_output("where python", shell=True).decode()
        except subprocess.CalledProcessError as err:
            LOG.debug("find_python3_executable - CalledProcessError:\n - {e}".format(e=err))
            return ""

        for python_executable in pythons.splitlines():
            LOG.debug("python_executable: {pe}".format(pe=python_executable))
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
        LOG.debug("paths found: {p}".format(p=paths))

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
    return ""


def get_python3_executable(config: dict = None) -> str:

    LOG = get_log()
    # First check for python3/python in path
    for version in ["python3", "python", "py"]:
        if is_python3_executable(version):
            LOG.debug("using %s as python interpreter", version)
            return version
        LOG.debug("No valid python found using only python3/python")

    # then find  one via shell
    python_exec = find_python3_executable()
    if python_exec:
        LOG.debug("Using {pex} as python3 interpreter".format(pex=python_exec))
        return python_exec

    # third: guess from black_command
    if config:
        if config["black_command"] != "black":
            python_exec = str(Path(config["black_command"]).parent / "python")
            LOG.debug("guessing from black_command")
            if is_python3_executable(python_exec):
                LOG.debug("using %s as python3 interpreter guess from black_command", python_exec)

                return python_exec

    LOG.debug("no valid python3 interpreter was found")

    return ""  # nothing found


def format_log_data(in_data, in_key: str = None) -> str:
    global _depth_count
    message = ""
    dash_string = "-" * _depth_count
    if isinstance(in_data, dict):
        if in_key:
            message = "{msg}{ds} {k}:".format(msg=message, ds=dash_string, k=in_key)

        _depth_count += 1
        for key, value in in_data.items():
            message = "{msg}\n{v}".format(msg=message, v=format_log_data(value, in_key=key))

        _depth_count -= 1

    elif isinstance(in_data, list):
        if in_key:
            message = "{msg}{ds} {k}:".format(msg=message, ds=dash_string, k=in_key)

        _depth_count += 1
        for value in in_data:
            message = "{msg}\n{v}".format(msg=message, v=format_log_data(value))

        _depth_count -= 1

    else:
        if in_key:
            message = "{msg}{ds} {k}: {v}".format(msg=message, ds=dash_string, k=in_key, v=in_data)

        else:
            message = "{msg}{ds} {v}".format(msg=message, ds=dash_string, v=in_data)

    return message


def shutdown_blackd() -> None:
    LOG = get_log()
    from . import server

    if not has_blackd_started():
        LOG.debug("Blackd not started, nothing to shutdown")
        return

    black_server = server.BlackdServer()
    black_server.stop_deamon()
