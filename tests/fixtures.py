import sys
import sublime
import pathlib

from unittest import TestCase
from unittesting import DeferrableTestCase


sublack_module = sys.modules["sublack.sublack"]
sublack_consts_module = sys.modules["sublack.sublack.consts"]
sublack_server_module = sys.modules["sublack.sublack.server"]
sublack_utils_module = sys.modules["sublack.sublack.utils"]


# def get_sublack():
#     return sys.modules["sublack.sublack"]


blacked = """def get_encoding_from_file(view):

    region = view.line(sublime.Region(0))

    encoding = get_encoding_from_region(region, view)
    if encoding:
        return encoding
    else:
        encoding = get_encoding_from_region(view.line(region.end() + 1), view)
        return encoding
    return None
"""

unblacked = r"""
def get_encoding_from_file( view):

    region = view.line( sublime.Region(0))

    encoding = get_encoding_from_region( region, view)
    if encoding:
        return encoding
    else:
        encoding = get_encoding_from_region(view.line(region.end() + 1), view)
        return encoding
    return None"""

diff = r"""@@ -1,12 +1,11 @@
+def get_encoding_from_file(view):
 # type: ignore - these lines must include a single space
-def get_encoding_from_file( view):
+    region = view.line(sublime.Region(0))
 # type: ignore - these lines must include a single space
-    region = view.line( sublime.Region(0))
-
-    encoding = get_encoding_from_region( region, view)
+    encoding = get_encoding_from_region(region, view)
     if encoding:
         return encoding
     else:
         encoding = get_encoding_from_region(view.line(region.end() + 1), view)
         return encoding
-    return None
\ No newline at end of file
+    return None"""

folding1 = """class A:
    def a(self):


        def b():
            pass
"""

folding1_expected = """class A:
    def a(self):
        def b():
            pass
"""

folding2 = """

class A:
    def a():
        def b():
            pass
"""

folding2_expected = """class A:
    def a():
        def b():
            pass
"""


def view():
    return sublime.active_window().new_file()


# precommit

pre_commit_config = {
    "hook_id": """repos:
-   repo: local
    hooks:
    - id: black
      name: black
      language: system
      entry: black
      types: [python]""",
    "repo_repo": """repos:
-   repo: https://github.com/ambv/black
    rev: 18.6b4
    hooks:
    -   id: black
        args: [--safe, --quiet]
        language_version: python3""",
    "nothing": """-   repo: https://github.com/pre-commit/pygrep-hooks
    rev: v1.0.0
    hooks:
    -   id: rst-backticks
-   repo: local
    hooks:
    -   id: rst
        name: rst
        entry: rst-lint --encoding utf-8
        files: ^(CHANGELOG.rst|HOWTORELEASE.rst|README.rst|changelog/.*)$
        language: python
        additional_dependencies: [pygments, restructuredtext_lint]""",
}


class TestCaseBlack(TestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self.view = self.window.new_file()
        self.window.focus_view(self.view)
        # make sure we have a window to work with
        settings = sublime.load_settings("Preferences.sublime-settings")
        settings.set("close_windows_when_empty", False)
        self.maxDiff = None

        self.folder = pathlib.Path(__file__).parents[1]
        self.old_data = self.window.project_data()

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            self.view.close()

        self.window.set_project_data(self.old_data)

    def all(self):
        all_file = sublime.Region(0, self.view.size())
        return self.view.substr(all_file)

    def setText(self, string: str):
        self.view.run_command("append", {"characters": string})


class TestCaseBlackAsync(DeferrableTestCase):
    def setUp(self):
        self.window = sublime.active_window()
        self.view = self.window.new_file()
        # make sure we have a window to work with
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("close_windows_when_empty", False)
        self.maxDiff = None

        self.folder = pathlib.Path(__file__).parents[1]
        self.old_data = self.window.project_data()

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            window = self.view.window()
            assert window, "No window found!"
            window.focus_view(self.view)
            window.run_command("close_file")

        self.window.set_project_data(self.old_data)

    def all(self):
        all_file = sublime.Region(0, self.view.size())
        return self.view.substr(all_file)

    def setText(self, string):
        self.view.run_command("append", {"characters": string})
