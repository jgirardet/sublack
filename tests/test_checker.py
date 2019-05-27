from fixtures import sublack as s

from unittest.mock import patch
from unittest import TestCase, skipIf

import subprocess
import os
import platform
import pathlib

Checker = s.Checker
popen = s.popen
kill_with_pid = s.kill_with_pid


root_dir = pathlib.Path(__file__).parents[1]
sublack_dir = root_dir / "sublack"


class TestSetPlatform(TestCase):
    @patch.object(s.checker.platform, "system", return_value="Linux")
    def test_setplatform_linux(self, plat):
        a = Checker("bla", 13246789)
        self.assertEqual(a.is_running_unix, a.is_running)

    @patch.object(s.checker.platform, "system", return_value="Darwin")
    def test_setplatform_osx(self, plat):
        a = Checker("bla", 13246789)
        self.assertEqual(a.is_running_unix, a.is_running)

    @patch.object(s.checker.platform, "system", return_value="Windows")
    def test_setplatform_windows(self, plat):
        a = Checker("bla", 13246789)
        self.assertEqual(a.is_running_windows, a.is_running)


@skipIf(platform.system() == "Windows", "unix tests")
class TestIsRunningUnix(TestCase):
    def test_target_alredy_terminated_return_talse(self):
        p = subprocess.Popen(["ls"])
        p.wait(timeout=2)
        c = Checker("a", p.pid)
        self.assertFalse(c.is_running())

    def test_watched_still_running_return_true(self):
        p = subprocess.Popen(["tail", "-f"])
        c = Checker("tail", os.getpid())
        try:
            self.assertTrue(c.is_running())
        except AssertionError as err:
            raise err
        finally:
            p.terminate()
            p.wait(timeout=2)

    def test_watched_not_running_return_false(self):
        p = subprocess.Popen(["tail", "-f"])
        c = Checker("tail", os.getpid())
        p.terminate()
        p.wait(timeout=2)
        self.assertFalse(c.is_running())

    def test_do_not_take_checker_args_in_account_return_false(self):
        p = subprocess.Popen(
            ["python3", "checker.py", "head", "987654"], cwd=str(sublack_dir)
        )
        c = Checker("head", os.getpid())
        try:
            self.assertFalse(c.is_running())
        except AssertionError as err:
            raise err
        finally:
            p.terminate()
            p.wait(timeout=2)


@skipIf(platform.system() != "Windows", "windows tests")
class TestIsRunningWindows(TestCase):
    def test_target_alredy_terminated_return_talse(self):
        p = popen(["timeout"])
        p.wait(timeout=2)
        c = Checker("a", p.pid)
        self.assertFalse(c.is_running())

    def test_watched_still_running_return_true(self):
        p = popen(["timeout", "/t", "3"])
        c = Checker("timeout", os.getpid())
        try:
            self.assertFalse(c.is_running())
        except AssertionError as err:
            raise err
        finally:
            p.terminate()
            p.wait(timeout=2)

    def test_watched_not_running_return_false(self):
        p = popen(["timeout", "/t", "3"])
        c = Checker("timeout", os.getpid())
        p.terminate()
        p.wait(timeout=2)
        self.assertFalse(c.is_running())


@skipIf(platform.system() == "Windows", "unix tests")
class TestRunUnix(TestCase):

    maxDiff = None

    def setUp(self):
        self.w = subprocess.Popen(["sleep", "3"])
        self.t = subprocess.Popen(["man", "vi"])

        self.p = subprocess.Popen(
            ["python3", "checker.py", "sleep", str(self.t.pid), "0"],
            cwd=str(sublack_dir),
        )

    def tearDown(self):
        for x in (self.w, self.t, self.p):
            try:
                x.terminate()
                # x.wait()
            except ProcessLookupError:
                pass

    def test_good_run(self):
        """test setup is ok"""
        self.assertIsNone(self.w.poll())  # is_running
        self.assertIsNone(self.t.poll())  # is_running
        self.assertIsNone(self.p.poll())  # is_running

    def test_target_stops_if_watched_stops(self):
        """watched stop -> target stops -> checker stops"""
        self.w.terminate()
        self.w.wait(timeout=2)
        self.assertIsNotNone(self.w.poll())
        self.assertIsNotNone(self.t.wait(timeout=10))
        self.assertIsNotNone(self.p.wait(timeout=2))

    def test_checker_stops_if_target_stops(self):
        """target stops  -> checker stops -> watched running"""
        self.t.terminate()
        self.t.wait(timeout=2)
        self.assertIsNotNone(self.t.wait(timeout=2))
        self.assertIsNotNone(self.p.wait(timeout=2))
        self.assertIsNone(self.w.poll())


@skipIf(platform.system() != "Windows", "windows tests")
class TestRunWindows(TestCase):
    def setUp(self):
        self.w = popen(["timeout", "/t", "3"])
        self.t = popen(["CHOICE", "/C:AB", "/T:10", "/D:A"])

        self.p = popen(
            [
                s.utils.get_python3_executable(),
                "checker.py",
                "timeout",
                str(self.t.pid),
                "0",
            ],
            cwd=str(sublack_dir),
        )

    def tearDown(self):
        for x in (self.w, self.t, self.p):
            try:
                kill_with_pid(x.pid)
            except ProcessLookupError:
                pass

    def test_good_run(self):
        """test setup is ok"""
        self.assertIsNone(self.w.poll())  # is_running
        self.assertIsNone(self.t.poll())  # is_running
        self.assertIsNone(self.p.poll())  # is_running

    def test_target_stops_if_watched_stops(self):
        """watched stop -> target stops -> checker stops"""
        self.w.terminate()
        self.w.wait(timeout=2)
        self.assertIsNotNone(self.w.poll())
        self.assertIsNotNone(self.t.wait(timeout=2))
        self.assertIsNotNone(self.p.wait(timeout=2))

    def test_checker_stops_if_target_stops(self):
        """target stops  -> checker stops -> watched running"""
        self.t.terminate()
        self.t.wait(timeout=2)
        self.assertIsNotNone(self.t.wait(timeout=2))
        self.assertIsNotNone(self.p.wait(timeout=2))
        self.assertIsNone(self.w.poll())
