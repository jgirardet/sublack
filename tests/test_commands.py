from __future__ import annotations

import fixtures
import pathlib
import sublime
import time

from unittest import TestCase
from unittest.mock import patch


@patch.object(fixtures.sublack_utils_module, "is_python", return_value=True)
class TestBlack(fixtures.TestCaseBlack):
    def test_black_file(self, _):
        self.setText(fixtures.unblacked)
        self.view.run_command("black_file")
        self.assertEqual(fixtures.blacked, self.all())

    def test_black_file_nothing_todo(self, _):
        # clear cache
        fixtures.sublack_utils_module.clear_cache()

        self.setText(fixtures.blacked)
        self.view.run_command("black_file")
        self.assertEqual(fixtures.blacked, self.all())
        self.assertEqual(
            self.view.get_status(fixtures.sublack_module.consts.STATUS_KEY),
            fixtures.sublack_module.consts.ALREADY_FORMATTED_MESSAGE,
        )

    def test_black_file_nothing_todo_cached(self, _):
        # clear cache
        fixtures.sublack_utils_module.clear_cache()

        self.setText(fixtures.blacked)
        self.view.run_command("black_file")

        self.view.run_command("black_file")
        self.assertEqual(fixtures.blacked, self.all())
        self.assertEqual(
            self.view.get_status(fixtures.sublack_module.consts.STATUS_KEY),
            fixtures.sublack_module.consts.ALREADY_FORMATTED_MESSAGE_CACHE,
        )

    def test_black_file_dirty_stay_dirty(self, _):
        self.setText(fixtures.blacked)
        self.assertTrue(self.view.is_dirty())
        self.view.run_command("black_file")
        self.assertTrue(self.view.is_dirty())
        self.assertEqual(fixtures.blacked, self.all())

    def test_black_diff(self, _):
        self.setText(fixtures.unblacked)
        starting_view = self.view
        starting_view.set_name("base")
        starting_view.run_command("black_diff")
        window = sublime.active_window()
        diff_view = window.active_view()
        assert diff_view, "No active view found!"
        region = sublime.Region(0, diff_view.size())
        region = sublime.Region(diff_view.lines(region)[2].begin(), diff_view.size())
        region_content = diff_view.substr(region)
        diff_lines = region_content.splitlines()
        expected_lines = fixtures.diff.splitlines()
        for index, (dl, el) in enumerate(zip(diff_lines, expected_lines), 1):
            if dl == el:
                continue

            raise AssertionError(f"'{dl}' != '{el}' on line: {index}")

        self.assertEqual(region_content.strip(), fixtures.diff.strip())
        self.assertEqual(
            diff_view.settings().get("syntax"), "Packages/Diff/Diff.sublime-syntax"
        )
        diff_view.set_scratch(True)
        diff_view.close()

    def test_folding1(self, _):
        self.setText(fixtures.folding1)
        self.view.fold(sublime.Region(25, 62))
        self.view.run_command("black_file")
        self.assertEqual(fixtures.folding1_expected, self.all())
        self.assertEquals(
            self.view.unfold(sublime.Region(0, self.view.size())),
            [sublime.Region(25, 59)],
        )

    def test_folding2(self, _):
        self.setText(fixtures.folding2)
        self.view.fold(sublime.Region(10, 57))
        self.view.run_command("black_file")
        self.assertEqual(fixtures.folding2_expected, self.all())
        self.assertEquals(
            self.view.unfold(sublime.Region(0, self.view.size())),
            [sublime.Region(8, 55)],
        )


class TestBlackdServer(TestCase):
    def setUp(self):
        self.port = str(fixtures.sublack_module.get_open_port())
        SETTINGS = {"fixtures.sublack_module.black_blackd_port": self.port}

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

    def test_start_and_stop_blackd(self, post=False, port: str | None = None):
        # Because the blackd_start command runs asynchronously on a timeout
        # we need to break the execution loop to allow the async function
        # to be called. So this function is broken into two parts, pre and post.
        # Pre calls blackd_start, async itself, from a timeout, thus providing a
        # break in the execution. It also then calls itself again, but only running
        # the post functionality, which tests if blackd is running on the test port.
        # This provides a syncronous asyncronous way of running this test.
        # I am certain there is a much better method of doing this, so will have to come
        # back to it when I am less sleep deprived...
        if not post:
            port = port or fixtures.sublack_utils_module.get_open_port()

            def _start_blackd():
                self.view.run_command("blackd_start", {"port": port})
                self.test_start_and_stop_blackd(post=True, port=port)

            sublime.set_timeout_async(_start_blackd, 0)
            return

        start_time = time.time()
        blackd_starting = fixtures.sublack_server_module.is_blackd_starting()
        while blackd_starting:
            time.sleep(0.5)
            blackd_starting = fixtures.sublack_server_module.is_blackd_starting()
            if time.time() - start_time > 20:
                raise AssertionError("Timed out waiting for blackd to start")

        assert port, "port should not be None!"
        self.assertTrue(
            fixtures.sublack_utils_module.is_blackd_running_on_port(port),
            "ensure blackd is running for the test",
        )

        # self.assertEqual(
        #     self.view.get_status(fixtures.sublack_module.STATUS_KEY),
        #     fixtures.sublack_module.BLACKD_STARTED.format(self.port),
        #     "should tell it starts",
        # )

        # # already running aka port in use
        # with patch("sublime.message_dialog"):
        #     self.view.run_command("blackd_start")
        # self.assertEqual(
        #     self.view.get_status(fixtures.sublack_module.STATUS_KEY),
        #     fixtures.sublack_module.BLACKD_ALREADY_RUNNING.format(self.port),
        #     "sould tell it fails",
        # )

        sublime.run_command("blackd_stop")

    def test_stopblackd(self):
        return
        # set up
        # stop any existing blackd server first
        # else we lose track of the pid:
        test_port = fixtures.sublack_utils_module.get_open_port()
        self.view.run_command("blackd_start", {"port": test_port})
        time.sleep(2)
        self.assertTrue(
            fixtures.sublack_utils_module.is_blackd_running_on_port(test_port),
            "ensure blackd is running for the test",
        )

        # already running, normal way
        sublime.run_command("blackd_stop")
        # self.assertRaises(
        #     requests.ConnectionError,
        #     lambda: requests.post(
        #         "http://localhost:" + self.port, "server should be down"
        #     ),
        # )
        # self.assertEqual(
        #     self.view.get_status(fixtures.sublack_module.STATUS_KEY),
        #     fixtures.sublack_module.BLACKD_STOPPED,
        #     "should tell it stops",
        # )

        # # already stopped
        # sublime.run_command("blackd_stop")
        # self.assertEqual(
        #     self.view.get_status(fixtures.sublack_module.STATUS_KEY),
        #     fixtures.sublack_module.BLACKD_STOP_FAILED,
        #     "status tell stop failed",
        # )


class TestFormatAll(fixtures.TestCaseBlack):

    temp_folder: pathlib.Path | None = None
    files: list[pathlib.Path] = []

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls.temp_folder and cls.temp_folder.exists():
            print(tuple(cls.temp_folder.iterdir()))
            cls.temp_folder.rmdir()

    def setUp(self):
        super().setUp()
        self.temp_folder = self.folder / "tests/temp"
        if not self.temp_folder.exists():
            self.temp_folder.mkdir(parents=True)

        self.project_data = self.window.project_data()
        self.window.set_project_data(
            {"folders": [{"path": str(self.temp_folder)}]}
        )

    def tearDown(self):
        super().tearDown()
        for file in self.files:
            if not file.exists():
                continue

            file.unlink()

        self.files.clear()
        self.window.set_project_data(self.project_data)

    def test_black_all_success(self):
        view = self.window.active_view()
        assert view, "No active view found!"
        temp_folder = self.temp_folder
        assert temp_folder
        file = temp_folder / "test_success_001.py"
        self.files.append(file)
        with file.open("w") as _file:
            _file.write("a=1")

        file = temp_folder / "test_success_002.py"
        self.files.append(file)
        with file.open("w") as _file:
            _file.write("b=2")

        with patch("sublime.ok_cancel_dialog", return_value=True):
            self.window.run_command("black_format_all")

        self.assertEqual(
            view.get_status(fixtures.sublack_module.STATUS_KEY),
            fixtures.sublack_module.REFORMATTED_ALL_MESSAGE
        )

    def test_black_all_fail(self):
        temp_folder = self.temp_folder
        assert temp_folder
        file = temp_folder / "test_fail_001.py"
        self.files.append(file)
        with file.open("w") as _file:
            _file.write("ab ac = 2")

        with patch("sublime.ok_cancel_dialog", return_value=True):
            self.window.run_command("black_format_all")

        view = self.window.active_view()
        assert view, "No active view found!"
        self.assertEqual(
            view.get_status(fixtures.sublack_module.STATUS_KEY),
            fixtures.sublack_module.REFORMAT_ERRORS
        )


PRECOMMIT_BLACK_SETTINGS = {
    "black_on_save": True,
    "black_line_length": None,
    "black_fast": False,
    "black_debug_on": True,
    "black_use_precommit": True,
    "black_use_blackd": False,
    "black_default_encoding": "utf-8",
}

precommit_config_path = pathlib.Path(__file__).parent / ".pre-commit-config.yaml"


@patch.object(fixtures.sublack_utils_module, "use_pre_commit", return_value=precommit_config_path)
@patch.object(fixtures.sublack_utils_module, "is_python", return_value=True)
@patch.object(fixtures.sublack_utils_module, "get_settings", return_value=PRECOMMIT_BLACK_SETTINGS)
class TestPrecommit(fixtures.TestCaseBlack):
    def test_black_file(self, *_):
        project = {"folders": [{"path": str(pathlib.Path(pathlib.Path(__file__).parents[1]))}]}
        self.window.set_project_data(project)
        # with tempfile.TemporaryDirectory() as T:
        self.setText(fixtures.unblacked)
        self.view.run_command("black_file")
        self.assertEqual(fixtures.blacked, self.all())


# @patch.object(fixtures.sublack_module.commands, "is_python", return_value=True)
# @patch.object(fixtures.sublack_module.blacker, "get_settings", return_value=TEST_BLACK_SETTINGS)
# class TestCommandsAsync(TestCaseBlackAsync):
#     def test_black_file_keeps_view_port_position(self, s, c):


#            ***** to enable if oneday it works with unittesting ******


#         content = (
#             'a="'
#             + "a" * int(self.view.viewport_extent()[0]) * 2
#             + " "
#             + "a" * int(self.view.viewport_extent()[0]) * 2
#             + '"'
#         )
#         import time

#         print(content)
#         # Packages/Python/Python.sublime-syntax
#         #'Packages/MagicPython/grammars/MagicPython.tmLanguage'
#         self.view.set_syntax_file(
#             "Packages/MagicPython/grammars/MagicPython.tmLanguage"
#         )
#         self.setText(content)

#         viewport = self.view.viewport_position()
#         print(self.view.viewport_extent())
#         print(viewport)
#         self.view.run_command("black_file")

#         yield 2000
#         print(self.view.viewport_position())
#         self.assertEqual(viewport, self.view.viewport_position())
