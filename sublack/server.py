import sublime
import requests
import time

from .utils import (
    cache_path,
    format_log_data,
    get_log,
    get_open_port,
    get_python3_executable,
    is_blackd_running_on_port,
    is_port_free,
    is_windows,
    kill_with_pid,
    popen,
)


class BlackdServer:
    def __init__(self, host="localhost", port=None, deamon=False, **kwargs):
        if not port:
            self.port = str(get_open_port())
        else:
            self.port = port

        self._blackd_cmd = None
        self.host = host
        self.proc = None
        self.deamon = deamon
        self.pid_path = cache_path() / "pid"
        self.timeout = kwargs.get("timeout", 5)
        self.sleep_time = kwargs.get("sleep_time", 0.1)
        default_watched = "plugin_host-3.3.exe" if is_windows() else "plugin_host-3.3"
        self.log.debug("default_watched: {dw}".format(dw=default_watched))
        self.watched = kwargs.get("watched", default_watched)
        self.checker_interval = kwargs.get("checker_interval", None)
        self.settings = kwargs.get("settings", None)

        self.platform = sublime.platform()
        self._depth_count = 0

        log_message = "New blackdServer instance with params: {data}".format(
            data=format_log_data(vars(self))
        )
        self.log.debug(log_message)

    @property
    def log(self):

        return get_log()

    @property
    def blackd_cmd(self):

        if self._blackd_cmd is None:

            self._blackd_cmd = (
                "{cmd}d".format(cmd=self.settings["black_command"]) if self.settings else "blackd"
            )
            self.log.debug("Setting {cmd} as blackd command".format(cmd=self._blackd_cmd))

        return self._blackd_cmd

    def is_running(self, timeout=None, sleep_time=None):
        # check server running
        timeout = timeout if timeout else self.timeout
        sleep_time = sleep_time if sleep_time else self.sleep_time
        started = time.time()
        while time.time() - started < timeout:  # timeout 5 s

            try:
                requests.post("http://{h}:{p}/".format(h=self.host, p=self.port))
            except requests.ConnectionError:
                time.sleep(sleep_time)
            else:
                self.log.info(
                    "blackd running at {h} on port {p} with pid {pid}".format(
                        h=self.host, p=self.port, pid=getattr(self.proc, "pid", None)
                    )
                )

                return True
        self.log.error(
            "blackd not running at {h} on port {p} with pid {pid}".format(h=self.host, p=self.port)
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

    def blackd_is_runnable(self):

        if is_port_free(self.port):
            self.log.debug("Port: {} checked, is free".format(self.port))
            return True

        if is_blackd_running_on_port(self.port):
            self.log.warning(
                "{} - aborting!".format("Blackd already running on port {}".format(self.port))
            )

        else:
            self.log.debug("Failed to start blackd - port: {} is busy".format(self.port))

        return False

    def _run_blackd(self, cmd):
        running = None
        log_message = "Starting blackd with args:"
        for value in cmd:
            log_message = "{lm}\n - {v}".format(lm=log_message, v=value)

        self.log.debug(log_message)

        if not self.blackd_is_runnable():
            return self.proc, False

        try:
            self.proc = popen(cmd)

        except FileNotFoundError as err:
            self.log.critical(
                "The given blackd command or path could not run: {}".format(self.blackd_cmd)
            )
            return None, False

        if self.is_running(timeout=5):
            running = True

        else:
            _, err = self.proc.communicate(timeout=1)
            self.log.error("blackd start error {err}".format(err))  # show stderr

        return self.proc, running

    def run(self):

        cmd = [self.blackd_cmd, "--bind-port", self.port]
        self.proc, running = self._run_blackd(cmd)

        if not running:
            self.log.error("Server not running!")
            return False

        if self.deamon:

            self.write_cache(self.proc.pid)
            python_executable = get_python3_executable(self.settings)
            self.log.debug("Python executable found : {pyex}".format(pyex=python_executable))

        return True

    def stop(self, pid=None):
        if self.proc:
            if is_windows():
                kill_with_pid(self.proc.pid)
            else:
                self.proc.terminate()
                self.proc.wait(timeout=10)
        else:
            kill_with_pid(pid)

        self.log.info("blackd stopped")

    def stop_deamon(self):
        self.log.debug("blackdServer stopping deamon")
        pid = self.get_cached_pid()
        if pid:
            self.stop(pid)
            self.write_cache("")
            return pid
        else:
            self.log.error("No blackd deamon could be stop since no pid cached")
