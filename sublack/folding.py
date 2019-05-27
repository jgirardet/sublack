import sublime
import logging
from .consts import PACKAGE_NAME

LOG = logging.getLogger(PACKAGE_NAME)
from .utils import popen
import subprocess
import json


class FoldingError(Exception):
    pass


def get_folded_lines(view):
    """ return line number corresponding to each folded statement.
    Turned to 1-based to fit ast numbers."""
    return [
        view.rowcol(f.begin())[0] + 1
        for f in view.unfold(sublime.Region(0, view.size()))
    ]


def get_region_to_refold(line, view):
    """ return a Region to fit with "left arrow click" to fold"""
    sel = view.sel()
    start = view.text_point(line + 1, 0)
    sel.clear()
    sel.add(sublime.Region(start, start))
    view.run_command("expand_selection", args={"to": "indentation"})

    region = sublime.Region(sel[0].begin() - 1, sel[0].end() - 1)
    sel.clear()

    return region


def get_refolds(view, to_folds):
    """return all region to refold"""
    return [get_region_to_refold(line, view) for line in to_folds]


def get_index_with_interpreter(view, body, encoding):
    """ extract an index for each ast node using the specified interpreter"""
    python = view.settings().get("python_interpreter")
    cmd = """import ast;b={};print([
        getattr(node, "lineno", 0)
        for node in ast.walk(ast.parse(b.decode(encoding="{}")))
        if hasattr(node, "lineno")
    ])""".format(
        body, encoding
    )
    proc = popen([python, "-c", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.returncode == 0:
        return json.loads(out.decode())
    else:
        raise FoldingError(err.decode())


def get_index_with_python33(body):
    """ extract an index for each ast node using the sublime python version"""
    import ast

    try:
        return [
            getattr(node, "lineno")
            for node in ast.walk(ast.parse(body))
            if hasattr(node, "lineno")
        ]
    except SyntaxError as err:
        LOG.error(
            """Sublack can't parse this python version to apply folding.
            Maybe you should set "python_interpreter" to specify the desired python version"""
        )
        raise FoldingError(err.msg)
    except Exception as err:
        raise FoldingError(str(err))


def get_ast_index(view, body, encoding):
    """extract an index/lineno for each ast node. lineno is 1 based."""

    try:
        if view.settings().has("python_interpreter"):
            return get_index_with_interpreter(view, body, encoding)
        else:
            return get_index_with_python33(body)
    except FoldingError:
        return False


def get_new_lines(old, new, folded_lines):
    """get new lines comparing index. minus one a the end to 
    fit turn back to 0-based sublime line numbers"""
    old_index = {}  # dict to not add a line twice
    for index, line in enumerate(old):
        if line not in old_index and line in folded_lines:
            old_index[line] = index
        if len(old_index) == len(folded_lines):
            break

    return [new[x] - 1 for x in old_index.values()]


def refold_all(old, new, view, folded_lines):
    LOG.debug("folded lines : %s", folded_lines)
    # LOG.debug("old folding index/lines: %s", old)
    # LOG.debug("new new folding index/lines : %s", new)
    refolds = get_refolds(view, get_new_lines(old, new, folded_lines))
    LOG.debug("new folding region: %s ", refolds)
    view.fold(refolds)
