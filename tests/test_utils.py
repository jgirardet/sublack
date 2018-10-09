from unittest import TestCase, skip  # noqa
from unittest.mock import MagicMock, patch

from fixtures import sublack, pre_commit_config
import sublime
import re
import tempfile

Path = sublack.utils.Path


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
            "black_skip_numeric_underscore_normalization": 4,
            "black_py36": 4,
            "black_use_blackd": 4,
            "black_blackd_host": 4,
            "black_blackd_port": 4,
            "black_blackd_autostart": 4,
            "black_use_precommit": 4,
        }

        res = {
            "black_command": 4,
            "black_on_save": 4,
            "black_line_length": 1,
            "black_fast": 1,
            "black_log": 4,
            "black_default_encoding": 4,
            "black_skip_string_normalization": 2,
            "black_skip_numeric_underscore_normalization": 4,
            "black_py36": 3,
            "black_use_blackd": 4,
            "black_blackd_host": 4,
            "black_blackd_port": 4,
            "black_blackd_autostart": 4,
            "black_use_precommit": 4,
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
        v.substr.return_value = "mkplpùlùplùplù"
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

    def test_find_pyproject(self):

        with tempfile.TemporaryDirectory() as T:
            # T = tempfile.TemporaryDirectory()
            root = Path(T)

            class View(str):
                def window():
                    return View

                def extract_variables():
                    return {"project_path": T}

                def folders():
                    return []

            # nothing
            self.assertIsNone(sublack.utils.find_root_file(View, "pyproject.toml"))
            pp = root / "pyproject.toml"
            pp.touch()
            self.assertTrue(pp.exists())
            # pyproject in project
            self.assertEqual(
                sublack.utils.find_root_file(View, "pyproject.toml"),
                root / "pyproject.toml",
            )

            View.extract_variables = lambda: {}
            # re nothing
            self.assertIsNone(sublack.utils.find_root_file(View, "pyproject.toml"))
            # pyproject in folders
            View.folders = lambda: ["", T]
            self.assertEqual(
                sublack.utils.find_root_file(View, "pyproject.toml"),
                root / "pyproject.toml",
            )

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
            f = sublack.utils.Path(T, "rien")
            written = f.write_text("hello")

            # test write
            self.assertEqual(written, 5)
            self.assertEqual(f.open().read(), "hello")

            # test read
            self.assertEqual(f.read_text(), "hello")
