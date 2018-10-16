from fixtures import sublack as s
import time

from unittest import TestCase
from unittest.mock import patch
import requests

BlackdServer = s.BlackdServer


test_proc = None
test_port = str(s.get_open_port())


def setUpModule():
    global test_proc
    global test_port

    test_proc = s.popen(["blackd", "--bind-port", test_port])
    time.sleep(0.5)  # wait balckd on


def tearDownModule():
    global test_proc
    s.kill_with_pid(test_proc.pid)


class TestBlackdServer(TestCase):
    """
    Use self.serv as temp server in tests. automtically closed
    at tearDown
    """

    def setUp(self):
        import platform

        self.return_code = 1 if platform.system() == "Windows" else 0

    def tearDown(self):
        if hasattr(self, "serv") and self.serv.proc:  # a blackdserver
            try:
                self.serv.stop()
            except AttributeError:
                pass
            except ProcessLookupError:
                pass

    def test_no_port_give_random_port(self):
        b = BlackdServer()
        c = BlackdServer()
        self.assertNotEqual(c.port, b.port)

    def test_is_running_blackd_not_running_return_False(self):
        b = BlackdServer(timeout=0.001)
        with patch.object(
            s.server.requests, "post", side_effect=requests.ConnectionError
        ) as m:
            # b = sublack.server.BlackdServer(timeout=0)
            self.assertFalse(b.is_running())
            m.assert_called_with(
                "http://localhost:{}".format(b.port)
            )  # ensure requests is called once

    def test_is_running_blackd_running_return_True(self):
        global test_port
        b = BlackdServer(port=test_port, sleep_time=0.1)
        self.assertTrue(b.is_running())

    def test_stop(self):
        self.serv = BlackdServer(checker_interval=0, sleep_time=0.001)
        self.serv.run()
        self.assertTrue(self.serv.is_running())
        self.serv.stop()
        self.assertEqual(self.serv.proc.wait(timeout=2), self.return_code)

    def test_daemon(self):
        self.serv = BlackdServer(sleep_time=0, checker_interval=0, deamon=True)
        self.assertTrue(self.serv.run())
        self.assertTrue(self.serv.is_running(), msg="should wait blackd is running")
        self.assertEqual(
            self.serv.get_cached_pid(),
            self.serv.proc.pid,
            "cache should be written with pid",
        )

        BlackdServer().stop_deamon()
        self.assertEqual(
            self.serv.proc.wait(timeout=2),
            self.return_code,
            "blackd should be stopped with return code 0",
        )
        self.assertFalse(
            BlackdServer().get_cached_pid(), "should get a blank cached pid"
        )

    def test_run_start_fail(self):
        global test_port
        self.serv = BlackdServer(sleep_time=0, checker_interval=0, port=test_port)
        with patch("sublime.message_dialog"):
            running = self.serv.run()
        self.assertFalse(running)

    def test_run_blackd_start_ok(self):
        self.serv = BlackdServer(sleep_time=0, checker_interval=0)
        running = self.serv.run()
        self.assertTrue(running)

    def test_blackd_path(self):
        self.serv = BlackdServer(
            sleep_time=0,
            checker_interval=0,
            settings=({"black_command": "/bla/ble/black"}),
        )
        self.assertEqual(self.serv.blackd_cmd, "/bla/ble/blackd")
