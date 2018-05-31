import sublime
import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch

version = sublime.version()

sublack = sys.modules["sublack.sublack"]

fixture = """
class BlackFileCommand(sublime_plugin.TextCommand):
    a = bla

    def get_content(self):
        encoding = self.view.encoding()
"""


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

    def setText(self, string):
        self.view.run_command("insert", {"characters": string})


#     def getRow(self, row):
#         return self.view.substr(self.view.line(self.view.text_point(row, 0)))

#     # since ST3 uses python 2 and python 2 doesn't support @unittest.skip,
#     # we have to do primitive skipping
#     if version >= '3000':

    def test_put(self):
        a = "dazdazdazdazd"
        self.setText(fixture)
        all_file = sublime.Region(0, self.view.size())
        content = self.view.substr(all_file)
        self.assertEqual(fixture, content.rstrip(' '))

    # def test_hello_world_st3(self):
    #     self.view.run_command("hello_world")
    #     first_row = self.getRow(0)
    #     self.assertEqual(first_row, "hello world")

#     def test_hello_world(self):
#         self.setText("new ")
#         self.view.run_command("hello_world")
#         first_row = self.getRow(0)
#         self.assertEqual(first_row, "new hello world")


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
