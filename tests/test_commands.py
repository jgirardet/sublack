from unittest import TestCase
from unittest.mock import patch

import sublime
from fixtures import sublack, blacked, unblacked, diff, TestCaseBlack

import requests

Path = sublack.utils.Path

TEST_BLACK_SETTINGS = {
    "black_command": "black",
    "black_on_save": True,
    "black_line_length": None,
    "black_fast": False,
    "black_debug_on": True,
    "black_default_encoding": "utf-8",
    "black_skip_string_normalization": False,
    "black_include": None,
    "black_py36": None,
    "black_exclude": None,
    "black_use_blackd": False,
    "black_blackd_host": "localhost",
    "black_blackd_port": "",
    "black_use_precommit": False,
}


@patch.object(sublack.commands, "is_python", return_value=True)
@patch.object(sublack.blacker, "get_settings", return_value=TEST_BLACK_SETTINGS)
class TestBlack(TestCaseBlack):
    def test_black_file(self, s, c):
        self.setText(unblacked)
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())

    def test_black_file_nothing_todo(self, s, c):
        # clear cache
        sublack.utils.clear_cache()

        self.setText(blacked)
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())
        self.assertEqual(
            self.view.get_status(sublack.consts.STATUS_KEY),
            sublack.consts.ALREADY_FORMATTED_MESSAGE,
        )

    def test_black_file_nothing_todo_cached(self, s, c):
        # clear cache
        sublack.utils.clear_cache()

        self.setText(blacked)
        self.view.run_command("black_file")

        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())
        self.assertEqual(
            self.view.get_status(sublack.consts.STATUS_KEY),
            sublack.consts.ALREADY_FORMATTED_MESSAGE_CACHE,
        )

    def test_black_file_dirty_stay_dirty(self, s, c):
        self.setText(blacked)
        self.assertTrue(self.view.is_dirty())
        self.view.run_command("black_file")
        self.assertTrue(self.view.is_dirty())
        self.assertEqual(blacked, self.all())

    def test_black_diff(self, s, c):

        self.setText(unblacked)
        self.view.set_name("base")
        backup = self.view
        self.view.run_command("black_diff")

        w = sublime.active_window()
        v = w.active_view()
        res = sublime.Region(0, v.size())
        res = sublime.Region(v.lines(res)[2].begin(), v.size())
        res = v.substr(res).strip()
        self.assertEqual(res, diff)
        self.assertEqual(
            v.settings().get("syntax"), "Packages/Diff/Diff.sublime-syntax"
        )
        self.view = backup
        v.set_scratch(True)
        v.close()

    def test_folding1(self, s, c):
        self.setText(
            """class A:
    def a():


        def b():
            pass
"""
        )
        self.view.fold(sublime.Region(21, 65))
        self.view.run_command("black_file")
        self.assertEqual(
            """class A:
    def a():
        def b():
            pass
""",
            self.all(),
        )
        self.assertEquals(
            self.view.unfold(sublime.Region(0, self.view.size())),
            [sublime.Region(21, 55)],
        )

    def test_folding2(self, s, c):
        self.setText(
            """

class A:
    def a():
        def b():
            pass
"""
        )
        self.view.fold(sublime.Region(10, 57))
        self.view.run_command("black_file")
        self.assertEqual(
            """class A:
    def a():
        def b():
            pass
""",
            self.all(),
        )
        self.assertEquals(
            self.view.unfold(sublime.Region(0, self.view.size())),
            [sublime.Region(8, 55)],
        )


class TestBlackdServer(TestCase):
    def setUp(self):
        self.port = str(sublack.get_open_port())
        SETTINGS = {"sublack.black_blackd_port": self.port}

        self.view = sublime.active_window().new_file()
        self.settings = self.view.settings()
        # make sure we have a window to work with
        [self.settings.set(k, v) for k, v in SETTINGS.items()]
        self.settings.set("close_windows_when_empty", False)

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")
        sublime.run_command("blackd_stop")

    def test_startblackd(self):
        # First normal Run
        self.view.run_command("blackd_start")
        self.assertTrue(
            sublack.check_blackd_on_http(self.port), "should have been formatted"
        )
        self.assertEqual(
            self.view.get_status(sublack.STATUS_KEY),
            sublack.BLACKD_STARTED.format(self.port),
            "sould tell it starts",
        )

        # already running aka port in use
        with patch("sublime.message_dialog"):
            self.view.run_command("blackd_start")
        self.assertEqual(
            self.view.get_status(sublack.STATUS_KEY),
            sublack.BLACKD_ALREADY_RUNNING.format(self.port),
            "sould tell it fails",
        )

    def test_stoplackd(self):
        # set up
        self.view.run_command("blackd_start")
        self.assertTrue(
            sublack.check_blackd_on_http(self.port),
            "ensure blackd is running for the test",
        )

        # already running, normal way
        sublime.run_command("blackd_stop")
        self.assertRaises(
            requests.ConnectionError,
            lambda: requests.post(
                "http://localhost:" + self.port, "server should be down"
            ),
        )
        self.assertEqual(
            self.view.get_status(sublack.STATUS_KEY),
            sublack.BLACKD_STOPPED,
            "should tell it stops",
        )

        # already stopped
        sublime.run_command("blackd_stop")
        self.assertEqual(
            self.view.get_status(sublack.STATUS_KEY),
            sublack.BLACKD_STOP_FAILED,
            "status tell stop failed",
        )

    # @patch.object(sublack.utils, "find_python3_executable", return_value=False)
    # @patch.object(
    #     sublack.utils, "is_python3_executable", side_effect=[False, False]
    # )
    # def test_osx_bug(self, a):
    #     """sublackissu #35"""

    #     self.view.run_command("blackd_start")
    # self.assertTrue(
    #     sublack.check_blackd_on_http(self.port), "should have been formatted"
    # )
    # self.assertEqual(
    #     self.view.get_status(sublack.STATUS_KEY),
    #     sublack.BLACKD_STARTED.format(self.port),
    #     "sould tell it starts",
    # )
    # import subprocess
    # import os

    # print(os.environ["PATH"])
    # self.assertEqual(
    #     subprocess.check_output(
    #         "env python3 -V", shell=True, executable="/bin/bash"
    #     ),
    #     subprocess.check_output("bash -ilc env", shell=True, executable="/bin/bash"),
    # )


class TestFormatAll(TestCaseBlack):
    def setUp(self):
        super().setUp()
        self.window.set_project_data({"folders": [{"path": str(self.folder)}]})

    def tearDown(self):
        super().tearDown()
        if hasattr(self, "wrong"):
            self.wrong.unlink()

    def test_black_all_success(self):

        # make sure we have a window to work with
        # s = sublime.load_settings("Preferences.sublime-settings")
        # s.set("close_windows_when_empty", False)
        # self.maxDiff = None

        with patch("sublime.ok_cancel_dialog", return_value=True):
            self.window.run_command("black_format_all")
        self.assertEqual(
            self.window.active_view().get_status(sublack.STATUS_KEY),
            sublack.REFORMATTED_MESSAGE,
            "reformat should be ok",
        )

    def test_black_all_fail(self):

        self.wrong = self.folder / "wrong.py"
        with open(str(self.wrong), "w") as ww:
            ww.write("ab ac = 2")

        with patch("sublime.ok_cancel_dialog", return_value=True):
            self.window.run_command("black_format_all")
        self.assertEqual(
            self.window.active_view().get_status(sublack.STATUS_KEY),
            sublack.REFORMAT_ERRORS,
            "reformat should be error",
        )


PRECOMMIT_BLACK_SETTINGS = {
    "black_command": "black",
    "black_on_save": True,
    "black_line_length": None,
    "black_fast": False,
    "black_debug_on": True,
    "black_default_encoding": "utf-8",
    "black_skip_string_normalization": False,
    "black_include": None,
    "black_py36": None,
    "black_exclude": None,
    "black_use_blackd": False,
    "black_blackd_host": "localhost",
    "black_blackd_port": "",
    "black_use_precommit": True,
}

precommit_config_path = Path(Path(__file__).parent, ".pre-commit-config.yaml")


@patch.object(sublack.blacker, "use_pre_commit", return_value=precommit_config_path)
@patch.object(sublack.commands, "is_python", return_value=True)
@patch.object(sublack.blacker, "get_settings", return_value=PRECOMMIT_BLACK_SETTINGS)
class TestPrecommit(TestCaseBlack):
    def test_black_file(self, s, c, p):
        project = {"folders": [{"path": str(Path(Path(__file__).parents[1]))}]}
        self.window.set_project_data(project)
        # with tempfile.TemporaryDirectory() as T:
        self.setText(unblacked)
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())
