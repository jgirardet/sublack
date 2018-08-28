import os
from unittest import TestCase, skip  # noqa
from unittest.mock import MagicMock, patch

import sublime
from fixtures import sublack, blacked, unblacked, diff


# @skip('mkoomk')
class TestBlackMethod(TestCase):
    def test_init(self):
        # test valid number of config options
        with patch.object(sublack.blacker, "get_settings") as m:
            m.return_value = ["hello"] * 7
            a = sublack.blacker.Black(MagicMock())
            self.assertEqual(a.config, ["hello"] * 7)

    def test_get_command_line(self):
        gcl = sublack.blacker.Black.get_command_line
        v = MagicMock()
        s = MagicMock()
        s.config = {
            "black_command": "black",
            "black_line_length": None,
            "black_fast": False,
        }
        s.view.file_name.return_value = "blabla.py"
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-"])

        s.config = {
            "black_command": "black",
            "black_line_length": 90,
            "black_fast": True,
        }
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "-l", "90", "--fast"])

        # test diff
        a = gcl(s, v, extra=["--diff"])
        self.assertEqual(a, ["black", "-", "--diff", "-l", "90", "--fast"])

        # test skipstring
        s.config = {"black_command": "black", "black_skip_string_normalization": True}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--skip-string-normalization"])

        # test include
        s.config = {"black_command": "black", "black_include": "hello"}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--include", "hello"])

        # test exclude
        s.config = {"black_command": "black", "black_exclude": "hello"}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--exclude", "hello"])

        # test py36
        s.config = {"black_command": "black", "black_py36": True}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--py36"])

        # test pyi
        s.config = {"black_command": "black"}
        s.view.file_name.return_value = "blabla.pyi"
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--pyi"])

    def test_windows_prepare(self):
        with patch.object(sublack.blacker, "sublime") as m:
            m.platform.return_value = "linux"
            wop = sublack.blacker.Black.windows_popen_prepare
            self.assertFalse(wop("r"))
        with patch.object(sublack.blacker, "sublime") as m:
            with patch.object(sublack.blacker, "subprocess"):
                m.platform.return_value = "windows"
                wop = sublack.blacker.Black.windows_popen_prepare
                self.assertTrue(wop("r"))

    def test_get_env(self):
        ge = sublack.blacker.Black.get_env
        env = os.environ.copy()

        with patch.object(sublack.blacker.locale, "getdefaultlocale", return_value=1):
            self.assertEqual(env, ge(True))

        with patch.object(
            sublack.blacker.locale, "getdefaultlocale", return_value=(None, None)
        ):
            with patch.object(sublack.blacker, "sublime") as m:
                m.platform.return_value = "linux"
                self.assertDictEqual(env, ge(True))

            with patch.object(sublack.blacker, "sublime") as m:
                m.platform.return_value = "osx"
                env["LC_CTYPE"] = "UTF-8"
                self.assertEqual(env, ge(True))

    def test_get_content_encoding(self):
        gc = sublack.blacker.Black.get_content
        s = MagicMock()
        s.view.encoding.return_value = "utf-32"
        c, e = gc(s)
        self.assertEqual(e, "utf-32")

        s.view.encoding.return_value = "Undefined"
        with patch.object(
            sublack.blacker, "get_encoding_from_file", return_value="utf-16"
        ):
            c, e = gc(s)
            self.assertEqual(e, "utf-16")

        s.config = {"black_default_encoding": "latin-1"}
        s.view.encoding.return_value = None
        c, e = gc(s)
        self.assertEqual(e, "latin-1")

    def test_get_content_content(self):
        gc = sublack.blacker.Black.get_content
        s = MagicMock()
        s.view.encoding.return_value = "utf-8"
        s.view.substr.return_value = "héllo"
        c, e = gc(s)
        self.assertEqual(c.decode("utf-8"), "héllo")

    def test_run_black(self):
        rb = sublack.blacker.Black.run_black
        s = MagicMock()
        s.get_cwd.return_value = None
        s.windows_popen_prepare.return_value = None
        a = rb(s, ["black", "-"], os.environ.copy(), None, "hello".encode())
        self.assertEqual(a[0], 0)
        self.assertEqual(a[1], b"hello\n")
        self.assertIn(b"reformatted", a[2])

        with patch.object(sublack.blacker, "sublime"):
            s.windows_popen_prepare.side_effect = OSError
            try:
                a = rb(s, ["black", "-"], os.environ.copy(), None, "hello".encode())
            except OSError as e:
                self.assertEqual(
                    str(e),
                    "You may need to install Black and/or configure 'black_command' in Sublack's Settings.",
                )

    def test_good_working_dir(self):
        gg = sublack.blacker.Black.get_good_working_dir

        # filename ok
        s = MagicMock()
        s.view.file_name.return_value = "/bla/bla.py"
        self.assertEqual("/bla", gg(s))

        # no filenmae, no window
        s.view.file_name.return_value = None
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

    def test_call(self):
        c = sublack.blacker.Black.__call__
        s = MagicMock()
        s.get_content.return_value = (1, "utf-8")
        s.config = {"black_use_blackd": False, "black_debug_on": False}

        # standard
        s.run_black.return_value = (0, b"hello\n", b"reformatted")
        c(s, "edit")
        s.view.replace.assert_called_with("edit", s.all, "hello\n")

        # failure
        s.reset_mock()
        s.run_black.return_value = (1, b"hello\n", b"reformatted")
        a = c(s, "edit")
        self.assertEqual(a, 1)

        # alreadyformatted
        s.reset_mock()
        s.run_black.return_value = (0, b"hello\n", b"unchanged")
        c(s, "edit")
        s.view.set_status.assert_called_with(
            sublack.consts.STATUS_KEY, sublack.consts.ALREADY_FORMATED_MESSAGE
        )

        # diff alreadyformatted
        s.reset_mock()
        s.run_black.return_value = (0, b"hello\n", b"unchanged")
        c(s, "edit", ["--diff"])
        s.view.set_status.assert_called_with(
            sublack.consts.STATUS_KEY, sublack.consts.ALREADY_FORMATED_MESSAGE
        )

        # diff
        s.reset_mock()
        s.run_black.return_value = (0, b"hello\n", b"reformatted")
        c(s, "edit", ["--diff"])
        s.do_diff.assert_called_with("edit", b"hello\n", "utf-8")


# @skip("demonstrating skipping")
@patch.object(sublack.commands, "is_python", return_value=True)
class TestBlack(TestCase):
    def setUp(self):
        self.view = sublime.active_window().new_file()
        # make sure we have a window to work with
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("close_windows_when_empty", False)
        self.maxDiff = None

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")

    def all(self):
        all_file = sublime.Region(0, self.view.size())
        return self.view.substr(all_file)

    def setText(self, string):
        self.view.run_command("append", {"characters": string})

    def test_blacked(self, s):
        self.setText(unblacked)
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())

    def test_nothing_todo(self, s):
        self.setText(blacked)
        self.view.run_command("black_file")
        self.assertEqual(blacked, self.all())
        self.assertEqual(
            self.view.get_status(sublack.consts.STATUS_KEY),
            sublack.consts.ALREADY_FORMATED_MESSAGE,
        )

    def test_dirty_stay_dirty(self, s):
        self.setText(blacked)
        self.assertTrue(self.view.is_dirty())
        self.view.run_command("black_file")
        self.assertTrue(self.view.is_dirty())
        self.assertEqual(blacked, self.all())

    def test_do_diff(self, s):
        # setup in case of fail
        # self.addCleanup(self.view.close)
        # self.addCleanup(self.view.set_scratch, True)

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
