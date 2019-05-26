from unittest import TestCase, skipIf
from unittest.mock import MagicMock, patch

from fixtures import sublack, pre_commit_config
import sublime
import re
import tempfile
import os
import platform

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
        class View(str):
            @staticmethod
            def window():
                return View

            @staticmethod
            def extract_variables():
                return {"project_path": T}

            @staticmethod
            def folders():
                return []

        with tempfile.TemporaryDirectory() as T:
            # T = tempfile.TemporaryDirectory()
            root = Path(T)

            view = View()

            # nothing
            self.assertIsNone(sublack.utils.find_root_file(view, "pyproject.toml"))
            pp = root / "pyproject.toml"
            pp.touch()
            self.assertTrue(pp.exists())
            # pyproject in project
            self.assertEqual(
                sublack.utils.find_root_file(view, "pyproject.toml"),
                root / "pyproject.toml",
            )

        with tempfile.TemporaryDirectory() as T:
            view = View()
            deux = View()
            deux.folders = lambda: [T]
            view.extract_variables = lambda: {}
            view.window = lambda: deux
            # re nothing
            self.assertIsNone(sublack.utils.find_root_file(view, "pyproject.toml"))
            # pyproject in folders
            root = Path(T) / "pyproject.toml"
            root.touch()
            self.assertEqual(sublack.utils.find_root_file(view, "pyproject.toml"), root)

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


class TestPythonExecutable(TestCase):
    def test_is_python3_executable(self):

        # binary doesn't exist
        self.assertFalse(sublack.utils.is_python3_executable("rien"))

        # binary error
        self.assertFalse(sublack.utils.is_python3_executable("python --errorarg"))

        # version shw nothing
        with patch.object(sublack.utils.subprocess, "check_output", return_value=b""):
            self.assertFalse(sublack.utils.is_python3_executable("python3"))

        # version is not 3
        with patch.object(
            sublack.utils.subprocess, "check_output", return_value=b"2\n"
        ):
            self.assertFalse(sublack.utils.is_python3_executable("python3"))

    def test_is_python3_executable_is_python3(self):
        # version is  3
        with patch.object(
            sublack.utils.subprocess, "check_output", return_value=b"3\n"
        ):
            self.assertTrue(sublack.utils.is_python3_executable("python3"))

    @skipIf(platform.system() == "Windows", "unix tests")
    def test_find_python3_executable_unix(self):

        # standard case
        if platform.system() == "Darwin":
            self.assertTrue(sublack.utils.find_python3_executable().endswith("python3"))

        # if no python3 and python returns nothing
        with patch.object(
            sublack.utils.subprocess,
            "check_output",
            return_value=b"BLA=fzefzefef\nPATH=/pythonxx:/usr/bin/blaqsfs:",
        ):
            self.assertFalse(sublack.utils.find_python3_executable())

        # if  python3 in a path
        good_path = (
            b"/usr/local/bin/" if platform.system() == "Darwin" else b"/usr/bin/"
        )
        with patch.object(
            sublack.utils.subprocess,
            "check_output",
            return_value=b"BLA=fzefzefef\nPATH=/pythonxx:" + good_path + b":",
        ):

            self.assertEqual(
                sublack.utils.find_python3_executable(), good_path.decode() + "python3"
            )

        # # if no python3 but  python returns a python3 interpreter
        with patch.object(
            sublack.utils.subprocess,
            "check_output",
            return_value=b"BLA=fzefzefef\nPATH=/pythonxx:/usr/bin/:",
        ):
            with patch.object(
                sublack.Path, "exists", side_effect=[False, False, False, False, True]
            ):
                with patch.object(
                    sublack.utils, "is_python3_executable", return_value=True
                ):
                    self.assertEqual(
                        sublack.utils.find_python3_executable(), "/usr/bin/python"
                    )

    @skipIf(platform.system() != "Windows", "Windows tests")
    def test_find_python3_executable_windows(self):

        # standard case
        self.assertTrue(sublack.utils.find_python3_executable().endswith("python.exe"))

        # if no python3 and python returns a python2 interpreter
        with patch.object(
            sublack.utils.subprocess, "check_output", return_value=b"bla\r\npython2\r\n"
        ):
            with patch.object(
                sublack.utils, "is_python3_executable", side_effect=[False, False]
            ):
                self.assertFalse(sublack.utils.find_python3_executable())

        # if python3 is the first
        with patch.object(
            sublack.utils.subprocess, "check_output", return_value=b"bla\r\npython2\r\n"
        ):
            with patch.object(
                sublack.utils, "is_python3_executable", side_effect=[True, False]
            ):
                self.assertEqual(sublack.utils.find_python3_executable(), "bla")

        # if python3 is the last
        with patch.object(
            sublack.utils.subprocess,
            "check_output",
            return_value=b"bla\r\nC:\\Users\\bla\\AppData\\Local\\Programs\\Python\\Python37-32\\python.exe\r\n",
        ):
            with patch.object(
                sublack.utils, "is_python3_executable", side_effect=[False, True]
            ):
                self.assertEqual(
                    sublack.utils.find_python3_executable(),
                    "C:\\Users\\bla\\AppData\\Local\\Programs\\Python\\Python37-32\\python.exe",
                )

    def test_get_python3_executable_by_word(self):
        if platform.system() == "Windows":
            self.assertEqual(sublack.utils.get_python3_executable({}), "python")

        else:
            self.assertEqual(sublack.utils.get_python3_executable({}), "python3")

    def test_get_python3_executable_by_find(self):

        with patch.object(sublack.utils, "is_python3_executable", return_value=False):
            with patch.object(
                sublack.utils, "find_python3_executable", return_value="/bla/bla"
            ):
                self.assertEqual(sublack.utils.get_python3_executable({}), "/bla/bla")

    def test_get_python3_executable_by_black_command(self):

        with patch.object(
            sublack.utils, "is_python3_executable", side_effect=[False, False, True]
        ):
            with patch.object(
                sublack.utils, "find_python3_executable", return_value=False
            ):
                path = Path("/path", "to", "black")
                self.assertEqual(
                    sublack.utils.get_python3_executable({"black_command": str(path)}),
                    str(path.parent / "python"),
                )

        # not python3
        with patch.object(
            sublack.utils, "is_python3_executable", side_effect=[False, False, False]
        ):
            with patch.object(
                sublack.utils, "find_python3_executable", return_value=False
            ):
                self.assertEqual(
                    sublack.utils.get_python3_executable(
                        {"black_command": "/path/to/black"}
                    ),
                    False,
                )
