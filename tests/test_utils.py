from unittest import TestCase
from unittest.mock import MagicMock, patch

from fixtures import sublack, pre_commit_config
import sublime
import re
import tempfile
import os
import pathlib

from pathlib import Path


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
        return self._variables  # {"project_path": T}

    def folders(self):
        return self._folders


class TestUtils(TestCase):
    def test_settings(self):
        self.maxDiff = None

        pyproject = {"line-length": 1, "fast": 1}

        flat = {"sublack.black_fast": 2, "sublack.black_skip_string_normalization": 2}

        nested = {"black_line_length": 3, "black_fast": 3, "black_py36": 3}

        globale = {
            "black_command": 4,
            "black_on_save": 4,
            "black_line_length": 4,
            "black_fast": 4,
            "black_log": 4,
            "black_default_encoding": 4,
            "black_skip_string_normalization": 4,
            "black_py36": 4,
            "black_target_version": 4,
            "black_use_blackd": 4,
            "black_blackd_host": 4,
            "black_blackd_port": 4,
            "black_blackd_autostart": 4,
            "black_use_precommit": 4,
            "black_confirm_formatall": 4,
        }

        res = {
            "black_command": 4,
            "black_on_save": 4,
            "black_line_length": 1,
            "black_fast": 1,
            "black_log": 4,
            "black_default_encoding": 4,
            "black_skip_string_normalization": 2,
            "black_py36": 3,
            "black_target_version": 4,
            "black_use_blackd": 4,
            "black_blackd_host": 4,
            "black_blackd_port": 4,
            "black_blackd_autostart": 4,
            "black_use_precommit": 4,
            "black_confirm_formatall": 4,
        }

        class View(str):
            def settings():
                flat["sublack"] = nested
                return flat

            def window():
                return View

            def extract_variables():
                return {}

            def folders():
                return []

        with patch.object(sublack.utils.sublime, "load_settings", return_value=globale):
            with patch.object(
                sublack.utils, "read_pyproject_toml", return_value=pyproject
            ):
                settings = sublack.utils.get_settings(View)

        ##### tests ##########

        # keep the number of settings
        self.assertEqual(
            len(globale), len(res), "should keep same number of setting item"
        )

        # good dispatch of settings
        self.assertEqual(settings, res)

        # check len consts.CONFIG_OPTIONS == sublime-settings file
        path = sublime.active_window().extract_variables().get("packages")
        path = Path(path, "sublack", "sublack.sublime-settings")
        c = open(str(path)).read()
        settings = re.findall(r"black_[a-z_0-9]+", c)
        self.assertEqual(set(settings), set(sublack.consts.CONFIG_OPTIONS))

    def test_get_encoding_from_region(self):
        v = MagicMock()
        v.substr.return_value = "mkplpÃƒÂ¹lÃƒÂ¹plÃƒÂ¹plÃƒÂ¹"
        x = sublack.utils.get_encoding_from_region(1, v)
        self.assertEqual(x, None)
        v.substr.return_value = "# -*- coding: latin-1 -*-"
        x = sublack.utils.get_encoding_from_region(1, v)
        self.assertEqual(x, "latin-1")

    @patch.object(
        sublack.utils, "get_encoding_from_region", return_value="premiere ligne"
    )
    def test_encoding_from_file(self, m):
        e = sublack.utils.get_encoding_from_file(MagicMock())
        self.assertEqual(e, "premiere ligne")
        m.side_effect = [None, "deuxieme ligne"]
        e = sublack.utils.get_encoding_from_file(MagicMock())
        self.assertEqual(e, "deuxieme ligne")

    def test_find_root_file_no_filename(self):
        with tempfile.TemporaryDirectory() as T:
            root = Path(T)
            view = View(Window())  # no file path
            self.assertIsNone(sublack.utils.find_root_file(view, "some.file"))

    def test_find_root_file_no_folder(self):
        with tempfile.TemporaryDirectory() as T:
            root = Path(T)
            view = View(Window({"file_path": "/bla/bla"}, []))  # no folder
            self.assertIsNone(sublack.utils.find_root_file(view, "some.file"))

    def test_find_root_file_no_folder_in_filepath(self):
        with tempfile.TemporaryDirectory() as T:
            root = Path(T)
            view = View(
                Window({"file_path": "/bla/bla"}, ["/ble"])
            )  # root folder not in filepath
            self.assertIsNone(sublack.utils.find_root_file(view, "some.file"))

    def test_find_root_file_no_root_file(self):
        with tempfile.TemporaryDirectory() as T:
            root = Path(T)
            view = View(Window({"file_path": str(Path(T, "working.py"))}, [T]))
            self.assertIsNone(sublack.utils.find_root_file(view, "some.file"))

    def test_find_root_file_all_in_root_folder(self):
        with tempfile.TemporaryDirectory() as T:
            root = Path(T)
            pp = root / "some.file"
            pp.touch()

            view = View(Window({"file_path": str(Path(T, "working.py"))}, [T]))
            self.assertEqual(sublack.utils.find_root_file(view, "some.file"), pp)

    def test_find_root_file_filepath_in_subdirs(self):
        with tempfile.TemporaryDirectory() as T:
            root = Path(T)
            pp = root / "some.file"
            pp.touch()

            view = View(
                Window(
                    {"file_path": str(Path(T, "some", "sub", "dirs", "working.py"))},
                    [T],
                )
            )
            self.assertEqual(sublack.utils.find_root_file(view, "some.file"), pp)

    def test_find_root_file_filepath_in_subdirs_with_root_file(self):
        with tempfile.TemporaryDirectory() as T:
            common = Path(T, "some", "sub", "dirs")
            common.mkdir(parents=True)
            pp = common / "some.file"
            pp.touch()

            view = View(Window({"file_path": str(common / "working.py")}, [T]))
            self.assertEqual(sublack.utils.find_root_file(view, "some.file"), pp)

    def test_find_root_file_find_closest(self):
        with tempfile.TemporaryDirectory() as T:

            root = Path(T)
            pp = root / "some.file"
            pp.touch()

            sub = root / "some" / "sub"
            sub.mkdir(parents=True)
            subpp = sub / "some.file"
            subpp.touch()

            view = View(
                Window(
                    {"file_path": str(Path(T, "some", "sub", "dirs", "working.py"))},
                    [T],
                )
            )
            self.assertEqual(sublack.utils.find_root_file(view, "some.file"), subpp)

    def test_read_pyproject(self):
        normal = '[other]\nbla = "bla"\n\n[tool.black]\nfast = true\nline-length = 1'
        error = '[other]bla = "bla"\n\n[tool.black]\nfast = true\nline-length = 1'
        with tempfile.TemporaryDirectory() as T:
            # no pyproject_found
            self.assertEqual({}, sublack.utils.read_pyproject_toml(None))
            # nothing in it
            pp = Path(T, "pyproject.toml")
            pp.touch()
            self.assertEqual({}, sublack.utils.read_pyproject_toml(pp))
            # successful way
            with open(str(pp), "w") as f:
                f.write(normal)
            config = sublack.utils.read_pyproject_toml(pp)
            self.assertEqual(config, {"fast": True, "line-length": 1})
            # error in cofonig
            with open(str(pp), "w") as f:
                f.write(error)
            config = sublack.utils.read_pyproject_toml(pp)
            self.assertEqual(config, {})

    def test_clear_cache(self):
        cache = sublack.utils.cache_path() / "formatted"
        with cache.open("w") as f:
            f.write("balbalbalbalbal")
        self.assertEqual(cache.open().read(), "balbalbalbalbal")
        sublack.utils.clear_cache()
        self.assertFalse(cache.open().read())

    def test_use_precommit(self):
        print("test use precommit")
        with tempfile.TemporaryDirectory() as T:
            path = Path(T, ".pre-commit-config.yaml")

            # no file
            self.assertFalse(sublack.utils.use_pre_commit(None))

            path.write_text("")
            self.assertFalse(sublack.utils.use_pre_commit(path))

            # validfile hook
            path.write_text(pre_commit_config["hook_id"])
            self.assertTrue(sublack.utils.use_pre_commit(path))

            # validfile repo
            path.write_text(pre_commit_config["repo_repo"])
            self.assertTrue(sublack.utils.use_pre_commit(path))

            # validfile repo
            path.write_text(pre_commit_config["nothing"])
            self.assertFalse(sublack.utils.use_pre_commit(path))

    def test_class_path(self):
        with tempfile.TemporaryDirectory() as T:
            f = Path(T, "rien")
            written = f.write_text("hello")

            # test write
            self.assertEqual(written, 5)
            self.assertEqual(f.open().read(), "hello")

            # test read
            self.assertEqual(f.read_text(), "hello")

    def test_get_env(self):
        ge = sublack.utils.get_env
        env = os.environ.copy()

        with patch.object(sublack.utils.locale, "getdefaultlocale", return_value=1):
            self.assertEqual(env, ge())

        with patch.object(
            sublack.utils.locale, "getdefaultlocale", return_value=(None, None)
        ):
            with patch.object(sublack.utils, "sublime") as m:
                m.platform.return_value = "linux"
                self.assertDictEqual(env, ge())

            with patch.object(sublack.utils, "sublime") as m:
                m.platform.return_value = "osx"
                env["LC_CTYPE"] = "UTF-8"
                self.assertEqual(env, ge())
