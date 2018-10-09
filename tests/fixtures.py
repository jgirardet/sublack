import sys
import sublime
from unittest import TestCase

sublack = sys.modules["sublack.sublack"]


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

unblacked = """
def get_encoding_from_file( view):

    region = view.line( sublime.Region(0))

    encoding = get_encoding_from_region( region, view)
    if encoding:
        return encoding
    else:
        encoding = get_encoding_from_region(view.line(region.end() + 1), view)
        return encoding
    return None"""

diff = """@@ -1,12 +1,12 @@
+def get_encoding_from_file(view):
 
-def get_encoding_from_file( view):
+    region = view.line(sublime.Region(0))
 
-    region = view.line( sublime.Region(0))
-
-    encoding = get_encoding_from_region( region, view)
+    encoding = get_encoding_from_region(region, view)
     if encoding:
         return encoding
     else:
         encoding = get_encoding_from_region(view.line(region.end() + 1), view)
         return encoding
     return None
+"""


view = lambda: sublime.active_window().new_file()


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
        # make sure we have a window to work with
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("close_windows_when_empty", False)
        self.maxDiff = None

        self.folder = sublack.utils.Path(__file__).parents[1]
        self.old_data = self.window.project_data()

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")

        self.window.set_project_data(self.old_data)

    def all(self):
        all_file = sublime.Region(0, self.view.size())
        return self.view.substr(all_file)

    def setText(self, string):
        self.view.run_command("append", {"characters": string})
