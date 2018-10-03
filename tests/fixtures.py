import sys
import sublime

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


view = lambda: sublime.active_window().active_view()
