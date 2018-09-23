import subprocess
import sublime
import requests
import time
import os
import sys
import logging
from .utils import cache_path, kill_with_pid, popen, get_open_port, check_blackd_on_http
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
        self.watched = kwargs.get("watched", "plugin_host")
        self.checker_interval = kwargs.get("checker_interval", None)

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
        proc = None
        running = None

        LOG.debug("Starting blackd with args %s", cmd)

        if not self.blackd_is_runnable():
            return proc, False

        proc = popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if self.is_running(timeout=5):
            running = True
            LOG.debug(
                "BlackdServer started on port %s with pid %s", self.port, proc.pid
            )
        else:
            proc.communicate(timeout=1)
            error = proc.stderr.read()

            # LOG.error(b"blackd start error %s", error)  # show stderr
            LOG.error(b"blackd start error %s", error)  # show stderr

        return proc, running

    def run(self):

        cmd = ["blackd", "--bind-port", self.port]

        self.proc, running = self._run_blackd(cmd)

        if not running:
            return False

        if self.deamon:
            cwd = os.path.dirname(os.path.abspath(__file__))
            checker_cmd = [
                sys.executable,
                "checker.py",
                self.watched,
                str(self.proc.pid),
            ]
            checker_cmd = (
                checker_cmd
                if not self.checker_interval
                else checker_cmd + [str(self.checker_interval)]
            )
            LOG.debug("Running checker with args %s", checker_cmd)
            self.checker = popen(checker_cmd, cwd=cwd)
            LOG.info("Blackd Checker running with pid %s", self.checker.pid)

            self.write_cache(self.proc.pid)

        return True

    def stop(self, pid=None):
        if self.proc:
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
