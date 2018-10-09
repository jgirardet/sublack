"""
TODO : test headers
"""

from unittest.mock import patch

import sublime
from fixtures import sublack, blacked, unblacked, diff, TestCaseBlack

blackd_proc = sublack.server.BlackdServer()


def setUpModule():
    global blackd_proc
    if not blackd_proc.run():
        raise IOError("blackd server not running")


def tearDownModule():
    global blackd_proc
    blackd_proc.stop()


BASE_SETTINGS = {
    "black_command": "black",
    "black_on_save": True,
    "black_line_length": None,
    "black_fast": False,
    "black_debug_on": True,
    "black_default_encoding": "utf-8",
    "black_skip_string_normalization": True,
    "black_include": None,
    "black_py36": None,
    "black_exclude": None,
    "black_use_blackd": True,
    "black_blackd_host": "localhost",
    "black_blackd_port": blackd_proc.port,
    "black_use_precommit": False,
}


@patch.object(sublack.commands, "is_python", return_value=True)
@patch.object(sublack.blacker, "get_settings", return_value=BASE_SETTINGS)
class TestBlackdServer(TestCaseBlack):
    def all(self):
        all_file = sublime.Region(0, self.view.size())
        return self.view.substr(all_file)

    def setText(self, string):
        self.view.run_command("append", {"characters": string})

    def test_blacked(self, s, c):
        self.setText(unblacked)
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())

    def test_nothing_todo(self, s, c):
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

    def test_do_diff(self, s, c):
        """"black should be called even blacked"""

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


@patch.object(sublack.commands, "is_python", return_value=True)
class TestBlackdServerNotRunning(TestCaseBlack):
    def setUp(self):
        super().setUp()
        self.BASE_SETTINGS = dict(BASE_SETTINGS)
        self.BASE_SETTINGS["black_blackd_port"] = "123465789"

    def test_blackd_not_runnint(self, s):
        with patch.object(
            sublack.blacker, "get_settings", return_value=self.BASE_SETTINGS
        ):
            with patch("sublime.message_dialog") as m:
                self.view.run_command("black_file")
                m.assert_called_with(
                    "blackd not running on port 123465789, you can start it with blackd_start command"
                )
