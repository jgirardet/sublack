"""
TODO : test headers
"""

from unittest.mock import patch

import sublime

from fixtures import sublack_module as sublack
from fixtures import sublack_server_module
from fixtures import blacked
from fixtures import unblacked
# from .fixtures import diff
from fixtures import TestCaseBlack


TESTPORT = "7929"


def setUpModule():
    if not sublack_server_module._start_blackd_server(TESTPORT):
        raise IOError("blackd server not running")


def tearDownModule():
    sublack_server_module.stop_blackd_server()


BASE_SETTINGS = {
    "black_blackd_host": "localhost",
    "black_blackd_port": TESTPORT,
    "black_command": "black",
    "black_debug_on": True,
    "black_confirm_formatall": False,
    "black_default_encoding": "utf-8",
    "black_fast": False,
    "black_line_length": None,
    "black_on_save": True,
    "black_py36": None,
    "black_skip_string_normalization": False,
    "black_use_blackd": True,
    "black_use_precommit": False
}


@patch.object(sublack.utils, "is_python", return_value=True)
@patch.object(sublack.utils, "get_settings", return_value=BASE_SETTINGS)
class TestBlackdServer(TestCaseBlack):
    def all(self):
        all_file = sublime.Region(0, self.view.size())
        return self.view.substr(all_file)

    def setText(self, string):
        self.view.run_command("append", {"characters": string})

    def test_blacked(self, *_):
        self.setText(unblacked)
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())

    def test_nothing_todo(self, *_):
        sublack.utils.clear_cache()
        self.setText(blacked)
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())
        self.assertEqual(
            self.view.get_status(sublack.consts.STATUS_KEY),
            sublack.consts.ALREADY_FORMATTED_MESSAGE,
        )

    def test_black_file_nothing_todo_cached(self, *_):
        sublack.utils.clear_cache()
        self.setText(blacked)
        self.view.run_command("black_file")
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())
        self.assertEqual(
            self.view.get_status(sublack.consts.STATUS_KEY),
            sublack.consts.ALREADY_FORMATTED_MESSAGE_CACHE,
        )

    # def test_do_diff(self, *_):
    #     """"black should be called even blacked"""

    #     self.setText(unblacked)
    #     self.view.set_name("base")
    #     backup = self.view
    #     self.view.run_command("black_diff")
    #     window = sublime.active_window()
    #     view = window.active_view()
    #     assert view, "No view found!"
    #     region = sublime.Region(0, view.size())
    #     region = sublime.Region(view.lines(region)[2].begin(), view.size())
    #     region = view.substr(region).strip()
    #     self.assertEqual(region, diff)
    #     self.assertEqual(
    #         view.settings().get("syntax"), "Packages/Diff/Diff.sublime-syntax"
    #     )
    #     self.view = backup
    #     view.set_scratch(True)
    #     view.close()


# @patch.object(sublack.utils, "is_python", return_value=True)
# class TestBlackdServerNotRunning(TestCaseBlack):
#     def setUp(self):
#         super().setUp()
#         self.BASE_SETTINGS = dict(BASE_SETTINGS)
#         self.BASE_SETTINGS["black_blackd_port"] = "123465789"

#     def test_blackd_not_running(self, *_):
#         with patch.object(
#             sublack.utils, "get_settings", return_value=self.BASE_SETTINGS
#         ):
#             with patch("sublime.message_dialog") as m:
#                 self.view.run_command("black_file")
#                 m.assert_called_with(
#                     "blackd not running on port 123465789, you can start it with blackd_start command"
#                 )
