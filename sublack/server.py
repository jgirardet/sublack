from __future__ import annotations

import contextlib
import functools
import sublime
import time

from . import utils

_typing = False
if _typing:
    import pathlib
    import subprocess
del _typing


_blackd_process = None
_blackd_starting = False


def set_blackd_process(process: subprocess.Popen[str]):
    global _blackd_process
    _blackd_process = process


def get_blackd_process() -> subprocess.Popen[str] | None:
    global _blackd_process
    return _blackd_process


@functools.lru_cache()
def get_pid_cache_path() -> pathlib.Path:
    return utils.cache_path() / "pid"


def set_cache_pid(process: subprocess.Popen[str]):
    log = utils.get_log()
    get_pid_cache_path().write_text(str(process.pid))
    log.debug(f"pid cache updated to: {process.pid}")


def get_cached_pid():
    log = utils.get_log()
    try:
        return int(get_pid_cache_path().read_text())
    except ValueError:
        log.debug("No pid in cache")
        return
    except FileNotFoundError:
        log.debug("Cache file not found")
        return


def is_blackd_starting() -> bool:
    global _blackd_starting
    return _blackd_starting


@contextlib.contextmanager
def blackd_starting_true():
    global _blackd_starting
    _blackd_starting = True
    print(f"pre _blackd_starting: {_blackd_starting}")
    try:
        yield
    finally:
        _blackd_starting = False
        print(f"post _blackd_starting: {_blackd_starting}")


def _start_blackd_server(port: str):
    with blackd_starting_true():
        log = utils.get_log()
        if not port:
            log.info("No valid port given, defaulting to 45484")
            port = "45484"

        python_exe_path = utils.get_vendor_python_exe_path()
        blackd_path = utils.get_vendor_blackd_path()
        blackd_command = [python_exe_path, blackd_path, "--bind-port", str(port)]
        log.debug(f"blackd_command: {blackd_command}")
        process = utils.popen(blackd_command)
        time.sleep(1)
        if process.stderr:
            raise Exception(process.stderr.read())

        set_cache_pid(process)
        set_blackd_process(process)
        if utils.is_blackd_running_on_port(port):
            utils.set_has_blackd_started(True)
            return process.pid


def start_blackd_server(view: sublime.View, port: str | None = None):
    print(f"START_BLACKD_SERVER: {port}")
    with blackd_starting_true():
        port = port or utils.get_settings(view)["black_blackd_port"]
        if port is None:
            raise AttributeError("No port number has been defined!")

        return _start_blackd_server(port)


def stop_blackd_server():
    log = utils.get_log()
    log.debug("Stopping blackd server")
    pid = get_cached_pid()
    if pid is None:
        log.critical("No pid cached - cannot stop server")
        return

    if utils.is_windows():
        utils.kill_with_pid(pid)

    else:
        process = get_blackd_process()
        assert process
        process.terminate()
        process.wait(timeout=10)

    log.info("blackd stopped")
