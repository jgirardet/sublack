import subprocess
import sublime
import requests
import time
import os
import sys
import tempfile
import logging
from .utils import (
    cache_path,
    kill_with_pid,
    popen,
    get_open_port,
    check_blackd_on_http,
    get_python3_executable,
)
from .consts import PACKAGE_NAME

LOG = logging.getLogger(PACKAGE_NAME)


class BlackdServer:
    def __init__(self, host="localhost", port=None, deamon=False, **kwargs):
        if not port:
            self.port = str(get_open_port())
        else:
            self.port = port
        self.host = host
        self.proc = None
        self.deamon = deamon
        self.pid_path = cache_path() / "pid"
        self.timeout = kwargs.get("timeout", 5)
        self.sleep_time = kwargs.get("sleep_time", 0.1)
        default_watched = (
            "plugin_host.exe" if sublime.platform() == "windows" else "plugin_host"
        )
        self.watched = kwargs.get("watched", default_watched)
        self.checker_interval = kwargs.get("checker_interval", None)
        self.settings = kwargs.get("settings", None)

        self.platform = sublime.platform()
        LOG.debug("New blackdServer instance with params : %s", vars(self))

    def is_running(self, timeout=None, sleep_time=None):
        # check server running
        timeout = timeout if timeout else self.timeout
        sleep_time = sleep_time if sleep_time else self.sleep_time
        started = time.time()
        while time.time() - started < timeout:  # timeout 5 s

            try:
                requests.post("http://" + self.host + ":" + self.port)
            except requests.ConnectionError:
                time.sleep(sleep_time)
            else:
                LOG.info(
                    "blackd running at %s on port %s with pid %s",
                    self.host,
                    self.port,
                    getattr(self.proc, "pid", None),
                )

                return True
        LOG.error("blackd not running at %s on port %s", self.host, self.port)
        return False

    def write_cache(self, pid):
        with self.pid_path.open("w") as f:
            f.write(str(pid))
        LOG.debug('pid cache updated to "%s"', pid)

    def get_cached_pid(self):
        try:
            pid = int(self.pid_path.open().read())
        except ValueError:
            LOG.debug("get_cached_pid: No pid in cache")
            return
        except FileNotFoundError:
            LOG.debug("get_cached_pid: Cache file not found")
            return
        else:
            LOG.debug("get_cached_pid: %s", pid)
            return pid

    def blackd_is_runnable(self):

        http_state = check_blackd_on_http(self.port)
        if http_state[0]:
            msg = "Blackd already running en port {}".format(self.port)
            LOG.warning(msg + " aborting..")
        else:
            if http_state[1]:
                LOG.debug("port checked, seems free")
                return True  #  server not running, port free
            else:
                msg("Fail to start blackd port %s seems busy", self.port)
                LOG.debug(msg)
        return False

    def _run_blackd(self, cmd):
        running = None

        LOG.debug("Starting blackd with args %s", cmd)

        if not self.blackd_is_runnable():
            return self.proc, False

        self.proc = popen(cmd)

        if self.is_running(timeout=5):
            running = True
        else:
            out, err = self.proc.communicate(timeout=1)

            LOG.error(b"blackd start error %s", err)  # show stderr

        return self.proc, running

    @property
    def blackd_cmd(self):
        blackd = self.settings["black_command"] + "d" if self.settings else "blackd"
        LOG.debug("using %s as blackd command", blackd)
        return blackd

    def run(self):

        cmd = [self.blackd_cmd, "--bind-port", self.port]

        self.proc, running = self._run_blackd(cmd)

        if not running:
            return False

        if self.deamon:

            self.write_cache(self.proc.pid)

            python_executable = get_python3_executable(self.settings)
            LOG.debug("python_executable found : %s", python_executable)

            checker = tempfile.NamedTemporaryFile(suffix="checker.py", delete=False)
            with checker:
                checker.write(
                    sublime.load_resource("Packages/sublack/sublack/checker.py").encode(
                        "utf8"
                    )
                )
            LOG.debug("checker tempfile: %s", checker.name)
            checker_cmd = [
                python_executable,
                checker.name,
                self.watched,
                str(self.proc.pid),
            ]

            # set timeout of interval
            checker_cmd = (
                checker_cmd
                if not self.checker_interval
                else checker_cmd + [str(self.checker_interval)]
            )

            if python_executable:
                LOG.debug("Running checker with args %s", checker_cmd)
                self.checker = popen(checker_cmd)
                LOG.info("Blackd Checker running with pid %s", self.checker.pid)
            else:
                sublime.error_message(
                    "Sublack: Checker didn't start successfull."
                    "You will have to run manually Stop Blackd before leaving sublime_text to stop blackd. "
                    "you can set 'black_log' to 'debug', and add an issue to sublack to help fix it"
                    "This maybe related to https://github.com/jgirardet/sublack/issues/35"
                )

        return True

    def stop(self, pid=None):
        if self.proc:
            if sublime.platform() == "windows":
                kill_with_pid(self.proc.pid)
            else:
                self.proc.terminate()
                self.proc.wait(timeout=10)
        else:
            kill_with_pid(pid)

        LOG.info("blackd stopped")

    def stop_deamon(self):
        LOG.debug("blackdServer stopping deamon")
        pid = self.get_cached_pid()
        if pid:
            self.stop(pid)
            self.write_cache("")
            return pid
        else:
            LOG.error("No blackd deamon could be stop since no pid cached")
