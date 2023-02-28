import os
from unittest import TestCase
from unittest.mock import MagicMock

from fixtures import sublack
from fixtures import sublack_utils
from fixtures import view
from fixtures import TestCaseBlack

import sublime
import pathlib
import tempfile


class TestBlackMethod(TestCaseBlack):
    def _get_view(self):
        window = sublime.active_window()
        view = window.active_view()
        assert view, "view is not defined"
        return view

    def test_get_command_line(self):
        view = self._get_view()
        black = sublack.blacker.Black(view)
        black.config = {
            "black_command": None,
            "black_line_length": None,
            "black_fast": False,
        }
        command = black.get_black_command()
        black_path = sublack_utils.get_vendor_black_path()
        self.assertEqual(command, [black_path, "-"])

        black.config = {
            "black_command": "black",
            "black_line_length": 90,
            "black_fast": True,
        }
        command = black.get_black_command()
        expected_command = [black_path, "-", "-l", "90", "--fast"]
        self.assertEqual(command, expected_command)

        # test diff
        command = black.get_black_command(extra=["--diff"])
        expected_command = [black_path, "-", "--diff", "-l", "90", "--fast"]
        self.assertEqual(command, expected_command)

        # test skipstring
        black.config = {"black_command": "black", "black_skip_string_normalization": True}
        command = black.get_black_command()
        expected_command = [black_path, "-", "--skip-string-normalization"]
        self.assertEqual(command, expected_command)

        # test py36
        black.config = {"black_command": "black", "black_py36": True}
        command = black.get_black_command()
        expected_command = [black_path, "-", "--py36"]
        self.assertEqual(command, expected_command)

        # test tearget target-version
        black.config = {"black_command": "black", "black_target_version": ["py36"]}
        command = black.get_black_command()
        expected_command = [black_path, "-", "--target-version", "py36"]
        self.assertEqual(command, expected_command)

        # test tearget target-version
        black.config = {"black_command": "black", "black_target_version": ["py36", "py37"]}
        command = black.get_black_command()
        expected_command = [black_path, "-", "--target-version", "py36", "--target-version", "py37"]
        self.assertEqual(command, expected_command)

        # test pyi
        view = MagicMock()
        black.config = {"black_command": "black"}
        black.view = view
        view.file_name.return_value = "blabla.pyi"
        command = black.get_black_command()
        expected_command = [black_path, "-", "--pyi"]
        self.assertEqual(command, expected_command)

    def test_get_content_encoding(self):
        self.view.set_encoding("utf-8")
        black = sublack.blacker.Black(self.view)
        _, encoding = black.get_content()
        self.assertEqual(encoding, self.view.encoding())

    def test_get_content(self):
        self.view.set_encoding("utf-8")
        self.setText("hÃ©llo")
        black = sublack.blacker.Black(self.view)
        content, _ = black.get_content()
        self.assertEqual(content.decode("utf-8"), "hÃ©llo")

    def _get_black_instance(self):
        return sublack.blacker.Black()

    def test_run_black(self):
        black = self._get_black_instance()
        blackd_command = sublack_utils.get_vendor_black_path()
        return_code, out, error = black.run_black(
            [blackd_command, "-"], os.environ.copy(), None, "hello".encode()
        )
        self.assertEqual(return_code, 0)
        self.assertEqual(out, b"hello\n")
        self.assertIn(b"reformatted", error)

    def test_good_working_dir(self):
        gg = sublack.blacker.Black.get_good_working_dir

        # filename ok
        s = MagicMock()
        s.view.file_name.return_value = "/bla/bla.py"
        self.assertEqual("/bla", gg(s))

        # no filenmae, no window
        s.view.file_name.return_value = None
        s.variables.get.return_value = ""
        s.view.window.return_value = None
        self.assertEqual(None, gg(s))

        # not folders
        e = MagicMock()
        s.view.window.return_value = e
        e.folders.return_value = []
        self.assertEqual(None, gg(s))

        # folder dir
        e.folders.return_value = ["/bla", "ble"]
        self.assertEqual("/bla", gg(s))


class TestCache(TestCase):
    def setUp(self):
        # data
        self.view = view()
        self.ah = str(hash("a"))
        self.bh = str(hash("b"))
        self.cmd1 = ["cmd1"]
        self.cache = self.ah + "|||" + str(self.cmd1) + "\n" + self.bh + "|||" + str(self.cmd1)
        # view
        self.black = sublack.blacker.Black(self.view)

        # temp file
        temp = tempfile.NamedTemporaryFile(delete=True)
        temp.close()
        self.black.formatted_cache = pathlib.Path(temp.name)
        with self.black.formatted_cache.open(mode="w") as f:
            f.write(self.cache)

    def tearDown(self):
        self.black.formatted_cache.unlink()
        self.view.set_scratch(True)
        self.view.window().run_command("close_file")

    def test_is_cached(self):

        # test first line present
        self.assertTrue(self.black.is_cached("a", self.cmd1))

        # test second line present
        self.assertTrue(self.black.is_cached("b", self.cmd1))

        # test content ok cmd not ok
        self.assertFalse(self.black.is_cached("b", ["cmd2"]))

        # test contnent not cmd ok
        self.assertFalse(self.black.is_cached("c", self.cmd1))

    def test_add_to_cache(self):

        # test already in , not added
        self.assertFalse(self.black.add_to_cache("a", self.cmd1))

        # test added and contenu
        self.assertTrue(self.black.add_to_cache("c", self.cmd1))
        self.assertEqual(
            self.black.formatted_cache.open().read(),
            "{}|||['cmd1']\n{}|||['cmd1']\n{}|||['cmd1']".format(str(hash("c")), self.ah, self.bh),
        )

    def test_limite_cache_size(self):
        ligne = self.ah + "|||" + str(self.cmd1) + "\n"
        with self.black.formatted_cache.open("wt") as f:
            f.write(251 * ligne)

        self.black.add_to_cache("b", self.cmd1)

        new_line = "{}|||['cmd1']".format(self.bh)
        cached = self.black.formatted_cache.open().read().splitlines()
        self.assertEqual(len(cached), 251)
        self.assertEqual(cached[:2], [new_line] + [ligne.strip()])


class TestBlackdClass(TestCase):
    def test_format_header(self):
        self.maxDiff = None

        # dep
        cmd = (
            "black - -l 25 --fast --skip-string-normalization --py36 --target-version py37".split()
        )
        h = sublack.blacker.Blackd.format_headers(cmd)
        h["X-Python-Variant"] = set(h["X-Python-Variant"].split(","))
        self.assertEqual(
            h,
            {
                "X-Line-Length": "25",
                "X-Skip-String-Normalization": "1",
                "X-Python-Variant": set(["py3.6", "py3.7"]),
                "X-Fast-Or-Safe": "fast",
            },
        )

        # standard
        cmd = "black - -l 25 --fast --skip-string-normalization --py36".split()
        h = sublack.blacker.Blackd.format_headers(cmd)
        self.assertEqual(
            h,
            {
                "X-Line-Length": "25",
                "X-Skip-String-Normalization": "1",
                "X-Python-Variant": "py3.6",
                "X-Fast-Or-Safe": "fast",
            },
        )

        # target-version
        cmd = "black - -l 25 --fast --skip-string-normalization --target-version py36 --target-version py37".split()
        h = sublack.blacker.Blackd.format_headers(cmd)
        h["X-Python-Variant"] = set(h["X-Python-Variant"].split(","))
        self.assertEqual(
            h,
            {
                "X-Line-Length": "25",
                "X-Skip-String-Normalization": "1",
                "X-Python-Variant": set(["py3.6", "py3.7"]),
                "X-Fast-Or-Safe": "fast",
            },
        )
