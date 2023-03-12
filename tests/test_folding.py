from __future__ import annotations

import sublime

from fixtures import sublack_module
from unittest import TestCase

SAMPLE = """class A:
    def a():
        def b():
            pass
"""

A_EQUAL_INDEX = [1, 1, 1]
SAMPLE_INDEX = [1, 2, 3, 4]


class View:
    def __init__(self, content):
        self._content = content
        self._unfold: list | None = None
        self._sel: Sel | None = None

    def unfold(self, region):
        return self._unfold

    def rowcol(self, point):
        row = 0
        col = 0
        for index, i in enumerate(self._content):
            if index == point:
                return (row, col)

            col += 1

            if i == "\n":
                row += 1
                col = 0

    def text_point(self, row, col):
        row_in = 0
        col_in = 0
        for index, i in enumerate(self._content):
            if row_in == row and col_in == col:
                return index

            col_in += 1
            if i == "\n":
                row_in += 1
                col_in = 0

    def size(self):
        len(self._content)

    def sel(self):
        return self._sel


class Sel:
    def __init__(self, regions=[]):
        self._regions = regions

    def clear(self):
        self._regions = []

    def __getitem__(self, index):
        return self._regions[index]

    def add(self, new):
        self._regions.append(new)


class TestFolding(TestCase):
    def test_get_folded_lines(self):
        v = View(SAMPLE)
        self.assertEquals(len(SAMPLE), 56)

        v._unfold = [sublime.Region(8, 55)]
        t = sublack_module.folding.get_folded_lines(v)
        self.assertEquals(t, [1])

        v._unfold = [sublime.Region(21, 55)]
        t = sublack_module.folding.get_folded_lines(v)
        self.assertEquals(t, [2])

    def test_region_to_refold(self):
        v = View(SAMPLE)
        v._sel = Sel()

        def _run_command1(x, args):
            v._sel.clear()
            v._sel.add(sublime.Region(9, 56))

        v.run_command = _run_command1
        self.assertEquals(
            sublime.Region(8, 55), sublack_module.folding.get_region_to_refold(0, v)
        )

        def _run_command2(x, args):
            v._sel.clear()
            v._sel.add(sublime.Region(22, 56))

        v.run_command = _run_command2
        self.assertEquals(
            sublime.Region(21, 55), sublack_module.folding.get_region_to_refold(1, v)
        )

    def test_get_index_with_ast(self):
        body = b"a=1"
        self.assertEquals(
            sublack_module.folding.get_index_with_ast(body), A_EQUAL_INDEX
        )
        self.assertEquals(
            sublack_module.folding.get_index_with_ast(SAMPLE.encode()),
            SAMPLE_INDEX,
        )
        with self.assertRaises(sublack_module.folding.FoldingError):
            sublack_module.folding.get_index_with_ast(b"a=")

    def test_get_ast_index(self):
        body = b"a=1"
        self.assertEquals(
            sublack_module.folding.get_ast_index(body), A_EQUAL_INDEX
        )
        self.assertEquals(
            sublack_module.folding.get_ast_index(body), A_EQUAL_INDEX
        )
        self.assertEquals(sublack_module.folding.get_ast_index(b"a="), False)

    def test_get_new_lines(self):
        old = [1, 5, 9, 10, 12, 99, 1, 10, 99]
        new = [1, 8, 9, 11, 15, 99, 1, 20, 100]
        folded_lines = [1, 5, 10, 99]

        self.assertEquals(
            sorted(sublack_module.folding.get_new_lines(old, new, folded_lines)),
            [0, 7, 10, 98],
        )

    def test_get_new_lines_line0(self):
        old = [3, 4, 5, 6]
        new = [1, 2, 3, 4]

        folded_lines = [3]

        self.assertEquals(
            sorted(sublack_module.folding.get_new_lines(old, new, folded_lines)), [0]
        )
