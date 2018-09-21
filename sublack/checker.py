import time
import subprocess
import platform
import os
import signal
import re
import argparse
import logging


DEFAULT_INTERVAL = 5


LOG = logging.getLogger("blackdserver_checker")
formatter = logging.Formatter(
    "[blackdserver_checker:%(funcName)s:%(lineno)d](%(levelname)s) %(message)s"
)
dh = logging.StreamHandler()
dh.setFormatter(formatter)
LOG.addHandler(dh)


class Checker:
    def __init__(self, watched: str, target: str, interval: int = DEFAULT_INTERVAL):

        self.watched = watched.encode()
        self.target = int(target)
        self.interval = interval

        self.is_running = self._set_platform()

        LOG.debug("platform %s", self.is_running.__name__)

    def windows_prepare(self):
        st = subprocess.STARTUPINFO()
        st.dwFlags = (
            subprocess.STARTF_USESHOWWINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        st.wShowWindow = subprocess.SW_HIDE
        return st

    def is_running_windows(self):
        # tasklist = subprocess.check_output(["tasklist", "/FO", "CSV"]).splitlines()

        tasklist = (
            subprocess.Popen(
                ["tasklist", "/FO", "CSV"],
                stdout=subprocess.PIPE,
                startupinfo=self.windows_prepare(),
            )
            .stdout.read()
            .splitlines()
        )

        # r_watched = re.compile(rb'"%b\.exe"' % self.watched)
        r_watched = re.compile(rb'"' + self.watched + rb'\.exe"')
        # r_target = re.compile(rb'".+","%b"' % str(self.target).encode())
        r_target = re.compile(rb'".+","' + str(self.target).encode() + rb'"')

        watched_found = False
        target_found = False

        for task in tasklist:

            if r_watched.match(task):
                watched_found = True
                LOG.debug("watched found at line %s", task)

            if r_target.match(task):
                target_found = True
                LOG.debug("target found at line %s", task)

            if watched_found and target_found:
                LOG.info(
                    'watched "%s" and target "%d" found', self.watched, self.target
                )
                return True

        LOG.info("target or watched not running anymore")

        return False

    def is_running_unix(self):

        tasklist = subprocess.check_output(["ps", "x"]).splitlines()

        watched_found = False
        target_found = False

        for task in tasklist:

            splitted = task.split(maxsplit=4)

            if (
                self.watched in splitted[4]
                and b"checker.py" not in splitted[4]
                and splitted[2] != b"Z"
            ):
                watched_found = True
                LOG.debug("watched found at line %s", task)

            if str(self.target).encode() == splitted[0] and splitted[2] != b"Z":
                target_found = True
                LOG.debug("target found at line %s", task)

            if watched_found and target_found:
                LOG.info(
                    'watched "%s" and target "%d" found',
                    self.watched.decode(),
                    self.target,
                )
                return True

        LOG.info("target or watched not running anymore")
        return False

    def _set_platform(self):
        plat = platform.system()

        if plat in ["Linux", "Darwin"]:
            return self.is_running_unix

        elif plat in ["Windows"]:
            return self.is_running_windows
        else:
            raise EnvironmentError("environnement {} is not supported", plat)

    def watch(self):

        while True:
            time.sleep(self.interval)
            if not self.is_running():
                return

    def terminate_target(self):
        try:
            LOG.info("killing target %d", self.target)
            os.kill(self.target, signal.SIGTERM)
        except ProcessLookupError:
            LOG.info("Process %d already terminated", self.target)

    def run(self):
        self.watch()
        self.terminate_target()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="checker")
    parser.add_argument("watched", type=str, help="Watched program's name")
    parser.add_argument("target", type=int, help="target's pid")
    parser.add_argument(
        "interval",
        nargs="?",
        type=int,
        default=DEFAULT_INTERVAL,
        help="interval between each check, default is 5",
    )
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="count", default=0
    )

    args = parser.parse_args()

    if args.verbose == 1:
        LOG.setLevel(logging.INFO)
    elif args.verbose > 1:
        LOG.setLevel(logging.DEBUG)
    else:
        LOG.setLevel(logging.WARNING)

    LOG.info("Running checker with args %s", vars(args))
    params = vars(args)
    params.pop("verbose")
    Checker(**vars(args)).run()
    LOG.info("stopping checker")
