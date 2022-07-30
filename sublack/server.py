from __future__ import annotations

import sublime

import subprocess
import time

from . import utils
from .consts import BLACKD_ALREADY_RUNNING
from .consts import BLACKD_START_FAILED
from .consts import BLACKD_STARTED
from .consts import STATUS_KEY
from .vendor.packages import requests

_typing = False
if _typing:
    from typing import Optional
del _typing


class BlackdServer:
    def __init__(
        self,
        host="localhost",
        port: str | None = None,
        deamon: bool = False,
        timeout: int = 5,
        sleep_time: float = 0.1,
        checker_interval: int | None = None,
        settings: dict[str, list[str]] | None = None
    ):
        self.port = port or str(utils.get_open_port())
        self._blackd_cmd = None
        self._process: subprocess.Popen[str] | None = None
        self.host = host
        self.deamon = deamon
        self.pid_path = utils.cache_path() / "pid"
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.checker_interval = checker_interval
        self.settings = settings

        self.platform = sublime.platform()
        self._depth_count = 0

        log_message = "New blackdServer instance with params: {data}".format(
            data=utils.format_log_data(vars(self))
        )
        self.log.debug(log_message)

    # Properties:
    @property
    def process(self) -> subprocess.Popen[str]:
        if self._process is None:
            self.log.error("Blackd process is undefined")
            raise RuntimeError("Blackd process is undefined")
        return self._process

    @process.setter
    def process(self, value: subprocess.Popen[str]):
        assert isinstance(value, subprocess.Popen), (
            f"process must be an instance of {subprocess.Popen}. Got: {value} of type: {type(value)}"
        )
        self._process = value

    @property
    def log(self):
        return utils.get_log()

    @property
    def blackd_command(self) -> str:
        if self._blackd_cmd is None:
            self._blackd_cmd = f"{utils.get_black_executable_command()}d"
            self.log.debug("Setting {command} as blackd command".format(command=self._blackd_cmd))

        return self._blackd_cmd

    # Private Methods:
    def _run_vendor_blackd(self, current_blackd_command: tuple[str, str, str]):
        """The given black command has failed, attempt to fallback onto vendored black"""

        vendor_blackd_exe_path = f"{utils.get_vendor_black_exe_path()}d"
        # If vendored black path matches the path in current_blackd_command, then
        # safe to assume we have already attempted to call and thus it will not work for
        # some bonkers reason:
        if vendor_blackd_exe_path == current_blackd_command[0]:
            self.log.critical(
                "The given blackd command or path could not run: {}".format(self.blackd_command)
            )
            return None, False

        self.log.info(f"Attempting to run blackd with vendored command:\n - {vendor_blackd_exe_path}")
        return self._run_blackd(blackd_command=vendor_blackd_exe_path)

    def _run_blackd(self, blackd_command: None | str = None) -> tuple[Optional[subprocess.Popen[str]], bool]:
        _blackd_command = (blackd_command or self.blackd_command, "--bind-port", self.port)
        running = False
        log_message = "Starting blackd with args:"
        for value in _blackd_command:
            log_message = "{lm}\n - {v}".format(lm=log_message, v=value)

        self.log.debug(log_message)
        if not self.blackd_is_runnable():
            return None, False

        try:
            self.process = utils.popen(_blackd_command)
            if self.is_running(timeout=5):
                return self.process, running

            _, err = self.process.communicate(timeout=2)
            self.log.error("blackd start error: {err}".format(err=err))  # show stderr

        except FileNotFoundError as err:
            return self._run_vendor_blackd(_blackd_command)

        return self.process, running

    # Public Methods:
    def is_running(self, timeout: int | None = None, sleep_time: float | None = None):
        # check server running
        timeout = timeout or self.timeout
        sleep_time = sleep_time or self.sleep_time
        started = time.time()
        while time.time() - started < timeout:  # timeout 5 s
            try:
                requests.post("http://{h}:{p}/".format(h=self.host, p=self.port))
            except requests.ConnectionError:
                time.sleep(sleep_time)
            else:
                self.log.info(
                    "blackd running at {h} on port {p} with pid {pid}".format(
                        h=self.host, p=self.port, pid=getattr(self.process, "pid", None)
                    )
                )

                return True

        self.log.error(
            "blackd not running at {h} on port {p} with pid {pid}".format(h=self.host, p=self.port, pid=self.process.pid)
        )
        return False

    def write_cache(self, pid):
        with self.pid_path.open("w") as f:
            f.write(str(pid))
        self.log.debug('pid cache updated to "%s"', pid)

    def get_cached_pid(self):
        try:
            pid = int(self.pid_path.open().read())
        except ValueError:
            self.log.debug("get_cached_pid: No pid in cache")
            return
        except FileNotFoundError:
            self.log.debug("get_cached_pid: Cache file not found")
            return
        else:
            self.log.debug("get_cached_pid: %s", pid)
            return pid

    def blackd_is_runnable(self) -> bool:
        if utils.is_port_free(self.port):
            self.log.debug("Port: {} checked, is free".format(self.port))
            return True

        if utils.is_blackd_running_on_port(self.port):
            self.log.warning(
                "{} - aborting!".format("Blackd already running on port {}".format(self.port))
            )

        else:
            self.log.debug("Failed to start blackd - port: {} is busy".format(self.port))

        return False

    def run(self):
        _process, running = self._run_blackd()
        if not (_process or running):
            self.log.error("Server not running!")
            return False

        if self.deamon:
            self.write_cache(self.process.pid)
            # python_executable = get_python3_executable(self.settings)
            # self.log.debug("Python executable found : {pyex}".format(pyex=python_executable))

        return True

    def stop(self, pid=None):
        if self.process:
            if utils.is_windows():
                utils.kill_with_pid(self.process.pid)
            else:
                self.process.terminate()
                self.process.wait(timeout=10)
        else:
            utils.kill_with_pid(pid)

        self.log.info("blackd stopped")

    def stop_deamon(self):
        self.log.debug("blackdServer stopping deamon")
        pid = self.get_cached_pid()
        if pid:
            self.stop(pid)
            self.write_cache("")
            return pid

        self.log.error("No blackd deamon could be stop since no pid cached")

    @staticmethod
    def start_blackd_server(view: sublime.View) -> None:
        log = utils.get_log()
        if utils.has_blackd_started():
            log.debug("Blackd server already started!")
            return

        utils.set_has_blackd_started(False)
        log.debug("start_blackd_server executed")
        if view is None:
            log.debug("No valid view found!")
            return

        started = None
        settings = utils.get_settings(view)
        port = settings["black_blackd_port"]
        if not port:
            log.info("No valid port given, defaulting to 45484")
            port = "45484"

        port_free = utils.is_port_free(port)
        log.debug("port_free: {}".format(port_free))
        if port_free:
            log.info("Creating new BlackdServer")
            blackd_server = BlackdServer(
                deamon=True, host="localhost", port=port, settings=settings
            )
            started = blackd_server.run()

        else:
            running = utils.is_blackd_running_on_port(port)
            log.debug("running: {}".format(running))
            if running:
                log.info(BLACKD_ALREADY_RUNNING.format(port))
                view.set_status(STATUS_KEY, BLACKD_ALREADY_RUNNING.format(port))
                utils.set_has_blackd_started(True)
                return

            log.info("Creating new BlackdServer")
            blackd_server = BlackdServer(
                deamon=True, host="localhost", port=port, settings=settings
            )
            started = blackd_server.run()

        if started:
            log.info(BLACKD_STARTED.format(port))
            view.set_status(STATUS_KEY, BLACKD_STARTED.format(port))
            sublime.set_timeout_async(lambda: view.set_status(STATUS_KEY, ""), 2000)
            utils.set_has_blackd_started(True)

        else:
            log.info(BLACKD_START_FAILED.format(port))
            view.set_status(STATUS_KEY, BLACKD_START_FAILED.format(port))
            utils.set_has_blackd_started(False)

    @staticmethod
    def shutdown_blackd() -> None:
        log = utils.get_log()
        if not utils.has_blackd_started():
            log.info("Blackd not started, nothing to shutdown")
            return

        black_server = BlackdServer()
        black_server.stop_deamon()