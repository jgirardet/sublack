import sublime
import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch
import os

version = sublime.version()

sublack = sys.modules["sublack.sublack"]


blacked = (
    """
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
)

unblacked = (
    """
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
)

diff = (
    """
--- <stdin>  (original)
+++ <stdin>  (formatted)
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
)


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
        self.setText(unblacked)
        self.view.set_name("base")
        backup = self.view
        self.view.run_command("black_diff")
        w = sublime.active_window()
        self.view = w.active_view()
        res = self.all()
        self.assertEqual(res, diff)
        self.view.close()
        self.view = backup


class TestBlackMethod(TestCase):
    def test_get_command_line(self):
        gcl = sublack.Black.get_command_line
        v = MagicMock()
        s = MagicMock()
        s.config = {"black_command": "black", "line_length": None, "fast": False}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-"])
        s.config = {"black_command": "black", "line_length": 90, "fast": True}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "-l", "90", "--fast"])
        a = gcl(s, v, extra=["--diff"])
        self.assertEqual(a, ["black", "-", "-l", "90", "--fast", "--diff"])

    def test_windows_prepare(self):
        with patch.object(sublack, "sys") as m:
            m.platform = "Linux"
            wop = sublack.Black.windows_popen_prepare
            self.assertFalse(wop("r"))

    def test_get_env(self):
        ge = sublack.Black.get_env
        env = os.environ.copy()
        with patch.object(sublack, "platform") as m:
            m.system = "Linux"
            self.assertEqual(env, ge(True))
        with patch.object(sublack.platform, "system", return_value="Darwin") as m:
            with patch.object(
                sublack.locale, "getdefaultlocale", return_value=(None, None)
            ):
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

        s.config = {"default_encoding": "latin-1"}
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

    def test_run_black(self):
        rb = sublack.Black.run_black
        s = MagicMock()
        s.windows_popen_prepare.return_value = None
        a = rb(s, ["black", "-"], os.environ.copy(), "hello".encode())
        self.assertEqual(a[0], 0)
        self.assertEqual(a[1], b"hello\n")
        self.assertEqual(a[2], b"reformatted -\n")

        with patch.object(sublack, "sublime") as m:
            s.windows_popen_prepare.side_effect = OSError
            try:
                a = rb(s, ["black", "-"], os.environ.copy(), "hello".encode())
            except OSError as e:
                self.assertEqual(
                    str(e),
                    "You may need to install Black and/or configure 'black_command' in Sublack's Settings.",
                )

    def test_call(self):
        pass


class TestFunctions(TestCase):
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


"""
Todo
------

- windows prepare on windows test_env
"""
