import subprocess
import sublime
import socket
import requests
import time


import logging
LOG = logging.getLogger("sublack")


class BlackdServer:
    def __init__(self, host="localhost", port=None):
        if not port:
            self.port = str(self.get_open_port())
        self.host = host
        self.proc = None
        self.platform = sublime.platform()

    def is_running(self):
        # check server running
        started = time.time()
        while time.time() - started < 5:  # timeout 5 s
            try:
                requests.post("http://" + self.host + ":" + self.port)
            except requests.ConnectionError:
                time.sleep(0.2)
            else:
                LOG.info(
                    "blackd running at {} on port {} with pid {}".format(
                        self.host, self.port, self.proc.pid
                    )
                )

                return True
        LOG.info(
            "failed to start blackd at {} on port {}}".format(self.host, self.port)
        )
        return False

    def run(self):
        # use this complexity to properly terminate blackd

        cmd = ["blackd", "--bind-port", self.port]

        self.proc = subprocess.Popen(cmd)

        return self.is_running()

    def stop(self):
        self.proc.terminate()
        LOG.info('blackd shutdown')

    def get_open_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()
        return port
