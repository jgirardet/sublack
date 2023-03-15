import sublime

from . import utils


class FoldingError(Exception):
    pass


def get_folded_lines(view: sublime.View):
    """return line number corresponding to each folded statement.
    Turned to 1-based to fit ast numbers."""
    return [view.rowcol(f.begin())[0] + 1 for f in view.unfold(sublime.Region(0, view.size()))]


def get_region_to_refold(line: int, view: sublime.View):
    """return a Region to fit with "left arrow click" to fold"""
    sel = view.sel()
    start = view.text_point(line + 1, 0)
    sel.clear()
    sel.add(sublime.Region(start, start))
    view.run_command("expand_selection", args={"to": "indentation"})

    region = sublime.Region(sel[0].begin() - 1, sel[0].end() - 1)
    sel.clear()

    return region


def get_refolds(view: sublime.View, to_folds: list):
    """return all region to refold"""
    return [get_region_to_refold(line, view) for line in to_folds]


def get_index_with_ast(body: str):
    """extract an index for each ast node using the sublime python version"""
    import ast

    try:
        return [
            getattr(node, "lineno") for node in ast.walk(ast.parse(body)) if hasattr(node, "lineno")
        ]
    except SyntaxError as err:
        utils.get_log().error(
            """Sublack can't parse this python version to apply folding.
            Maybe you should set "python_interpreter" to specify the desired python version"""
        )
        raise FoldingError(err.msg)
    except Exception as err:
        raise FoldingError(str(err))


def get_ast_index(body: str):
    """extract an index/lineno for each ast node. lineno is 1 based."""
    try:
        return get_index_with_ast(body)
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
    utils.get_log().debug("folded lines : %s", folded_lines)
    utils.get_log().debug("old folding index/lines: %s", old)
    utils.get_log().debug("new new folding index/lines : %s", new)
    refolds = get_refolds(view, get_new_lines(old, new, folded_lines))
    utils.get_log().debug("new folding region: %s ", refolds)
    view.fold(refolds)
