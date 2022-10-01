from __future__ import annotations

import functools
import sublime
import subprocess
# import time

from . import utils
# from .consts import BLACKD_ALREADY_RUNNING
# from .consts import BLACKD_START_FAILED
# from .consts import BLACKD_STARTED
# from .consts import STATUS_KEY

_blackd_process = None


def set_blackd_process(process: subprocess.Popen[str]):
    global _blackd_process
    _blackd_process = process


def get_blackd_process() -> subprocess.Popen[str] | None:
    global _blackd_process
    return _blackd_process


@functools.lru_cache()
def get_pid_cache_path():
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


def start_blackd_server(view: sublime.View):
    log = utils.get_log()
    settings = utils.get_settings(view)
    port = settings["black_blackd_port"]
    if not port:
        log.info("No valid port given, defaulting to 45484")
        port = "45484"

    python_exe_path = utils.get_vendor_python_exe_path()
    blackd_path = utils.get_vendor_blackd_path()
    blackd_command = [python_exe_path, blackd_path, "--bind-port", str(port)]
    log.debug(f"blackd_command: {blackd_command}")
    process = utils.popen(blackd_command)
    set_cache_pid(process)
    set_blackd_process(process)
    if utils.is_blackd_running_on_port(port):
        utils.set_has_blackd_started(True)
        return process.pid


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
