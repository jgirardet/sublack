import sublime
import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch
import os
import tempfile

version = sublime.version()

sublack = sys.modules["sublack.sublack"]


blacked = """
def get_encoding_from_file(view):

    region = view.line(sublime.Region(0))

    encoding = get_encoding_from_region(region, view)
    if encoding:
        return encoding
    else:
        encoding = get_encoding_from_region(view.line(region.end() + 1), view)
        return encoding
    return None
""".strip()


unblacked = """
def get_encoding_from_file( view):

    region = view.line( sublime.Region(0))

    encoding = get_encoding_from_region( region, view)
    if encoding:
        return encoding
    else:
        encoding = get_encoding_from_region(view.line(region.end() + 1), view)
        return encoding
    return None
""".strip()

diff = """
@@ -1,11 +1,12 @@
-def get_encoding_from_file( view):
+def get_encoding_from_file(view):
 
-    region = view.line( sublime.Region(0))
+    region = view.line(sublime.Region(0))
 
-    encoding = get_encoding_from_region( region, view)
+    encoding = get_encoding_from_region(region, view)
     if encoding:
         return encoding
     else:
         encoding = get_encoding_from_region(view.line(region.end() + 1), view)
         return encoding
     return None
+
""".strip()


class TestBlackMethod(TestCase):
    def test_init(self):
        # test valid number of config options
        with patch.object(sublack, "get_settings") as m:
            m.return_value = ["hello"] * 7
            a = sublack.Black(MagicMock())
            self.assertEqual(a.config, ["hello"] * 7)

    def test_get_command_line(self):
        gcl = sublack.Black.get_command_line
        v = MagicMock()
        s = MagicMock()
        s.use_pyproject.return_value = False
        s.config = {
            "black_command": "black",
            "black_line_length": None,
            "black_fast": False,
            "black_autouse_pyproject": True,
        }
        s.view.file_name.return_value = "blabla.py"
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-"])

        s.config = {
            "black_command": "black",
            "black_line_length": 90,
            "black_fast": True,
            "black_autouse_pyproject": True,
        }
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "-l", "90", "--fast"])

        # test diff
        a = gcl(s, v, extra=["--diff"])
        self.assertEqual(a, ["black", "-", "--diff", "-l", "90", "--fast"])

        # test skipstring
        s.config = {
            "black_command": "black",
            "black_skip_string_normalization": True,
            "black_autouse_pyproject": True,
        }
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--skip-string-normalization"])

        # test pyi
        s.config = {"black_command": "black", "black_autouse_pyproject": True}
        s.view.file_name.return_value = "blabla.pyi"
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--pyi"])

        # autouse_pyproject
        s.use_pyproject.return_value = True  # tearup
        s.config = {
            "black_command": "black",
            "black_skip_string_normalization": True,
            "black_autouse_pyproject": True,
        }
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-"])
        s.use_pyproject.return_value = False  # Teardown

    def test_windows_prepare(self):
        with patch.object(sublack, "sublime") as m:
            m.platform.return_value = "linux"
            wop = sublack.Black.windows_popen_prepare
            self.assertFalse(wop("r"))
        with patch.object(sublack, "sublime") as m:
            with patch.object(sublack, "subprocess"):
                m.platform.return_value = "windows"
                wop = sublack.Black.windows_popen_prepare
                self.assertTrue(wop("r"))

    def test_get_env(self):
        ge = sublack.Black.get_env
        env = os.environ.copy()

        with patch.object(sublack.locale, "getdefaultlocale", return_value=1):
            self.assertEqual(env, ge(True))

        with patch.object(
            sublack.locale, "getdefaultlocale", return_value=(None, None)
        ):
            with patch.object(sublack, "sublime") as m:
                m.platform.return_value = "linux"
                self.assertDictEqual(env, ge(True))

            with patch.object(sublack, "sublime") as m:
                m.platform.return_value = "osx"
                env["LC_CTYPE"] = "UTF-8"
                self.assertEqual(env, ge(True))

    def test_get_content_encoding(self):
        gc = sublack.Black.get_content
        s = MagicMock()
        s.view.encoding.return_value = "utf-32"
        c, e = gc(s)
        self.assertEqual(e, "utf-32")

        s.view.encoding.return_value = "Undefined"
        with patch.object(sublack, "get_encoding_from_file", return_value="utf-16"):
            c, e = gc(s)
            self.assertEqual(e, "utf-16")

        s.config = {"black_default_encoding": "latin-1"}
        s.view.encoding.return_value = None
        c, e = gc(s)
        self.assertEqual(e, "latin-1")

    def test_get_content_content(self):
        gc = sublack.Black.get_content
        s = MagicMock()
        s.view.encoding.return_value = "utf-8"
        s.view.substr.return_value = "héllo"
        c, e = gc(s)
        self.assertEqual(c.decode("utf-8"), "héllo")

    def test_get_cwd(self):
        gc = sublack.Black.get_cwd
        s = MagicMock()
        s.view.file_name.return_value = "/blabla/blabla/file.py"
        self.assertEqual(gc(s), "/blabla/blabla")

    def test_run_black(self):
        rb = sublack.Black.run_black
        s = MagicMock(**{"get_cwd.return_value": None})
        s.windows_popen_prepare.return_value = None
        a = rb(s, ["black", "-"], os.environ.copy(), "hello".encode())
        self.assertEqual(a[0], 0)
        self.assertEqual(a[1], b"hello\n")
        self.assertIn(b"reformatted", a[2])

        with patch.object(sublack, "sublime"):
            s.windows_popen_prepare.side_effect = OSError
            try:
                a = rb(s, ["black", "-"], os.environ.copy(), "hello".encode())
            except OSError as e:
                self.assertEqual(
                    str(e),
                    "You may need to install Black and/or configure 'black_command' in Sublack's Settings.",
                )

    def test_use_pyproject(self):

        up = sublack.Black.use_pyproject
        with tempfile.TemporaryDirectory() as p:

            # no pyproject
            s = MagicMock(**{"variables": {"folder": p}})
            self.assertFalse(up(s))

            # no  black in pyproejct
            with open(os.path.join(p, "pyproject.toml"), "w") as o:
                o.write("bla\nbla\nbla\nbla\nbla\nbla\n")
            self.assertFalse(up(s))

            # black in pyproject
            with open(os.path.join(p, "pyproject.toml"), "w") as o:
                o.write("bla\nbla\nbla\nbla\nbla\nbla\n[tool.black]")
            self.assertTrue(up(s))

    def test_call(self):
        c = sublack.Black.__call__
        s = MagicMock()
        s.get_content.return_value = (1, "utf-8")

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
        s.view.window.return_value.status_message.assert_called_with(
            sublack.ALREADY_FORMATED_MESSAGE
        )

        # diff alreadyformatted
        s.reset_mock()
        s.run_black.return_value = (0, b"hello\n", b"unchanged")
        c(s, "edit", ["--diff"])
        s.view.window.return_value.status_message.assert_called_with(
            sublack.ALREADY_FORMATED_MESSAGE
        )

        # diff
        s.reset_mock()
        s.run_black.return_value = (0, b"hello\n", b"reformatted")
        c(s, "edit", ["--diff"])
        s.do_diff.assert_called_with("edit", b"hello\n", "utf-8")


class TestFunctions(TestCase):
    maxDiff = None

    @patch.object(sublack, "sublime", return_value="premiere ligne")
    def test_get_settings(self, subl):
        def fake_get(param, default=None):
            flat = {"sublack.black_on_save": True}
            nested = {"black_debug_on": True}
            if param == "sublack":
                return nested
            elif param.split(".")[0] == "sublack":
                return flat.get(param, sublack.KEY_ERROR_MARKER)
            else:
                raise ValueError("settings must be nested or flat sublack")

        gs = sublack.get_settings

        subl.load_settings.return_value = {
            "black_command": "black",
            "black_on_save": False,
            "black_line_length": None,
            "black_fast": False,
            "black_debug_on": False,
            "black_default_encoding": "utf-8",
            "black_skip_string_normalization": False,
            "black_autouse_pyproject": True,
        }
        v = MagicMock()
        c = MagicMock()
        v.settings.return_value = c
        c.get = fake_get

        res = {
            "black_command": "black",
            "black_on_save": True,
            "black_line_length": None,
            "black_fast": False,
            "black_debug_on": True,
            "black_default_encoding": "utf-8",
            "black_skip_string_normalization": False,
            "black_autouse_pyproject": True,
        }

        # settings are all from setting file except on_save
        self.assertDictEqual(res, gs(v))

    def test_get_encoding_from_region(self):
        v = MagicMock()
        v.substr.return_value = "mkplpùlùplùplù"
        x = sublack.get_encoding_from_region(1, v)
        self.assertEqual(x, None)
        v.substr.return_value = "# -*- coding: latin-1 -*-"
        x = sublack.get_encoding_from_region(1, v)
        self.assertEqual(x, "latin-1")

    @patch.object(sublack, "get_encoding_from_region", return_value="premiere ligne")
    def test_encoding_from_file(self, m):
        e = sublack.get_encoding_from_file(MagicMock())
        self.assertEqual(e, "premiere ligne")
        m.side_effect = [None, "deuxieme ligne"]
        e = sublack.get_encoding_from_file(MagicMock())
        self.assertEqual(e, "deuxieme ligne")


@patch.object(sublack, "is_python", return_value=True)
class TestHBlack(TestCase):
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
        return self.view.substr(all_file).strip()

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

    def test_pyproject_toml(self, s):

        self.view.window().run_command("close_file")

        pj = os.path.join

        with tempfile.TemporaryDirectory() as p:

            file = pj(p, "module", "rien.py")

            os.makedirs(pj(p, "module"))
            with open(file, "w") as o:
                o.write('a = ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]')

            with open(pj(p, "pyproject.toml"), "w") as o:
                o.write("[tool.black]\nline-length = 5")

            with open(pj(p, ".git"), "w") as o:
                o.write("a git file")

            view = sublime.active_window().open_file(file)
            view.window().focus_view(view)
            view.run_command("black_file")
            r = sublime.Region(0, view.size())
            res = view.substr(r).strip()
            self.view = view  # for teardown

            self.assertEqual(
                res,
                """a = [
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
]""",
            )
