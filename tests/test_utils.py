from __future__ import annotations

import fixtures
import sublime
import re
import tempfile
import os
import pathlib

from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch


class View(str):
    def __init__(self, window):
        self._window = window

    def window(self):
        return self._window


class Window:
    def __init__(self, variables={}, folders=[]):
        self._variables = variables
        self._folders = folders

    def extract_variables(self):
        return self._variables

    def folders(self):
        return self._folders


class TestUtils(TestCase):
    def test_settings(self):
        self.maxDiff = None

        pyproject = {"line-length": 1, "fast": 1}

        flat: dict[str, int | dict[str, int]] = {
            "sublack.black_fast": 2, "sublack.black_skip_string_normalization": 2
        }

        nested = {"black_line_length": 3, "black_fast": 3, "black_py36": 3}

        globale = {
            "black_blackd_autostart": 4,
            "black_blackd_host": 4,
            "black_blackd_port": 4,
            "black_command": 4,
            "black_confirm_formatall": 4,
            "black_default_encoding": 4,
            "black_fast": 4,
            "black_line_length": 4,
            "black_log": 4,
            "black_log_to_file": 4,
            "black_on_save": 4,
            "black_py36": 4,
            "black_skip_string_normalization": 4,
            "black_target_version": 4,
            "black_use_blackd": 4,
            "black_use_precommit": 4,
        }

        res = {
            "black_blackd_autostart": 4,
            "black_blackd_host": 4,
            "black_blackd_port": 4,
            "black_command": 4,
            "black_confirm_formatall": 4,
            "black_default_encoding": 4,
            "black_fast": 1,
            "black_line_length": 1,
            "black_log": 4,
            "black_log_to_file": 4,
            "black_on_save": 4,
            "black_py36": 3,
            "black_skip_string_normalization": 2,
            "black_target_version": 4,
            "black_use_blackd": 4,
            "black_use_precommit": 4,
        }

        class View(str):
            @staticmethod
            def settings():
                flat["sublack"] = nested
                return flat

            @staticmethod
            def window():
                return View

            @staticmethod
            def extract_variables():
                return {}

            @staticmethod
            def folders():
                return []

        with patch.object(fixtures.sublack_module.utils.sublime, "load_settings", return_value=globale):
            with patch.object(
                fixtures.sublack_module.utils, "read_pyproject_toml", return_value=pyproject
            ):
                settings = fixtures.sublack_module.utils.get_settings(View)  # type: ignore  # noqa

        # tests #

        # keep the number of settings
        self.assertEqual(
            len(globale), len(res), "should keep same number of setting item"
        )
        # good dispatch of settings
        self.assertEqual(settings, res)

        # check len consts.CONFIG_OPTIONS == sublime-settings file
        path = sublime.active_window().extract_variables().get("packages")
        assert path, "Path is undefined"
        path = pathlib.Path(path, "sublack", "sublack.sublime-settings")
        c = open(str(path)).read()
        settings = re.findall(r"black_[a-z_0-9]+", c)
        self.assertEqual(set(settings), set(fixtures.sublack_consts_module.CONFIG_OPTIONS))

    def test_get_encoding_from_region(self):
        view = MagicMock()
        view.substr.return_value = "mkplpÃƒÂ¹lÃƒÂ¹plÃƒÂ¹plÃƒÂ¹"
        encoding = fixtures.sublack_utils_module.get_encoding_from_region(1, view)
        self.assertEqual(encoding, "")
        view.substr.return_value = "# -*- coding: latin-1 -*-"
        encoding = fixtures.sublack_utils_module.get_encoding_from_region(1, view)
        self.assertEqual(encoding, "latin-1")

    @patch.object(
        fixtures.sublack_utils_module, "get_encoding_from_region", return_value="premiere ligne"
    )
    def test_encoding_from_file(self, m):
        e = fixtures.sublack_utils_module.get_encoding_from_file(MagicMock())
        self.assertEqual(e, "premiere ligne")
        m.side_effect = [None, "deuxieme ligne"]
        e = fixtures.sublack_utils_module.get_encoding_from_file(MagicMock())
        self.assertEqual(e, "deuxieme ligne")

    def test_find_root_file_no_filename(self):
        with tempfile.TemporaryDirectory() as T:
            # root = pathlib.Path(T)
            view = View(Window())  # no file path
            self.assertIsNone(fixtures.sublack_utils_module.find_root_file(view, "some.file"))  # type: ignore  # noqa

    def test_find_root_file_no_folder(self):
        with tempfile.TemporaryDirectory() as T:
            # root = pathlib.Path(T)
            view = View(Window({"file_path": "/bla/bla"}, []))  # no folder
            self.assertIsNone(fixtures.sublack_utils_module.find_root_file(view, "some.file"))  # type: ignore  # noqa

    def test_find_root_file_no_folder_in_filepath(self):
        with tempfile.TemporaryDirectory() as T:
            # root = pathlib.Path(T)
            view = View(
                Window({"file_path": "/bla/bla"}, ["/ble"])
            )  # root folder not in filepath
            self.assertIsNone(fixtures.sublack_utils_module.find_root_file(view, "some.file"))  # type: ignore  # noqa

    def test_find_root_file_no_root_file(self):
        with tempfile.TemporaryDirectory() as T:
            # root = pathlib.Path(T)
            view = View(Window({"file_path": str(pathlib.Path(T, "working.py"))}, [T]))
            self.assertIsNone(fixtures.sublack_utils_module.find_root_file(view, "some.file"))  # type: ignore  # noqa

    def test_find_root_file_all_in_root_folder(self):
        with tempfile.TemporaryDirectory() as T:
            root = pathlib.Path(T)
            pp = root / "some.file"
            pp.touch()

            view = View(Window({"file_path": str(pathlib.Path(T, "working.py"))}, [T]))
            self.assertEqual(fixtures.sublack_utils_module.find_root_file(view, "some.file"), pp)  # type: ignore  # noqa

    def test_find_root_file_filepath_in_subdirs(self):
        with tempfile.TemporaryDirectory() as T:
            root = pathlib.Path(T)
            pp = root / "some.file"
            pp.touch()

            view = View(
                Window(
                    {"file_path": str(pathlib.Path(T, "some", "sub", "dirs", "working.py"))},
                    [T],
                )
            )
            self.assertEqual(fixtures.sublack_utils_module.find_root_file(view, "some.file"), pp)  # type: ignore  # noqa

    def test_find_root_file_filepath_in_subdirs_with_root_file(self):
        with tempfile.TemporaryDirectory() as T:
            common = pathlib.Path(T, "some", "sub", "dirs")
            common.mkdir(parents=True)
            pp = common / "some.file"
            pp.touch()

            view = View(Window({"file_path": str(common / "working.py")}, [T]))
            self.assertEqual(fixtures.sublack_utils_module.find_root_file(view, "some.file"), pp)  # type: ignore  # noqa

    def test_find_root_file_find_closest(self):
        with tempfile.TemporaryDirectory() as T:

            root = pathlib.Path(T)
            pp = root / "some.file"
            pp.touch()

            sub = root / "some" / "sub"
            sub.mkdir(parents=True)
            subpp = sub / "some.file"
            subpp.touch()

            view = View(
                Window(
                    {"file_path": str(pathlib.Path(T, "some", "sub", "dirs", "working.py"))},
                    [T],
                )
            )
            self.assertEqual(fixtures.sublack_utils_module.find_root_file(view, "some.file"), subpp)  # type: ignore  # noqa

    def test_read_pyproject(self):
        normal = '[other]\nbla = "bla"\n\n[tool.black]\nfast = true\nline-length = 1'
        error = '[other]bla = "bla"\n\n[tool.black]\nfast = true\nline-length = 1'
        with tempfile.TemporaryDirectory() as T:
            # no pyproject_found
            self.assertEqual({}, fixtures.sublack_utils_module.read_pyproject_toml(None))
            # nothing in it
            pp = pathlib.Path(T, "pyproject.toml")
            pp.touch()
            self.assertEqual({}, fixtures.sublack_utils_module.read_pyproject_toml(pp))
            # successful way
            with open(str(pp), "w") as f:
                f.write(normal)
            config = fixtures.sublack_utils_module.read_pyproject_toml(pp)
            self.assertEqual(config, {"fast": True, "line-length": 1})
            # error in cofonig
            with open(str(pp), "w") as f:
                f.write(error)
            config = fixtures.sublack_utils_module.read_pyproject_toml(pp)
            self.assertEqual(config, {})

    def test_clear_cache(self):
        cache = fixtures.sublack_utils_module.cache_path() / "formatted"
        with cache.open("w") as f:
            f.write("balbalbalbalbal")
        self.assertEqual(cache.open().read(), "balbalbalbalbal")
        fixtures.sublack_utils_module.clear_cache()
        self.assertFalse(cache.open().read())

    def test_use_precommit(self):
        with tempfile.TemporaryDirectory() as T:
            path = pathlib.Path(T, ".pre-commit-config.yaml")

            # no file
            self.assertFalse(fixtures.sublack_utils_module.use_pre_commit(None))

            path.write_text("")
            self.assertFalse(fixtures.sublack_utils_module.use_pre_commit(path))

            # validfile hook
            path.write_text(fixtures.pre_commit_config["hook_id"])
            self.assertTrue(fixtures.sublack_utils_module.use_pre_commit(path))

            # validfile repo
            path.write_text(fixtures.pre_commit_config["repo_repo"])
            self.assertTrue(fixtures.sublack_utils_module.use_pre_commit(path))

            # validfile repo
            path.write_text(fixtures.pre_commit_config["nothing"])
            self.assertFalse(fixtures.sublack_utils_module.use_pre_commit(path))

    def test_class_path(self):
        with tempfile.TemporaryDirectory() as T:
            f = pathlib.Path(T, "rien")
            written = f.write_text("hello")

            # test write
            self.assertEqual(written, 5)
            self.assertEqual(f.open().read(), "hello")

            # test read
            self.assertEqual(f.read_text(), "hello")

    def test_get_env(self):
        # self.maxDiff = None
        get_env = fixtures.sublack_utils_module.get_env
        env = os.environ.copy()

        with patch.object(fixtures.sublack_utils_module.locale, "getdefaultlocale", return_value=1):
            self.assertEqual(env, get_env())

        with patch.object(
            fixtures.sublack_utils_module.locale, "getdefaultlocale", return_value=(None, None)
        ):
            with patch.object(fixtures.sublack_utils_module, "get_platform", return_value="linux"):
                self.assertDictEqual(env, get_env())

            with patch.object(fixtures.sublack_utils_module, "get_platform", return_value="osx"):
                env["LC_CTYPE"] = "UTF-8"
                self.assertEqual(env, get_env())
