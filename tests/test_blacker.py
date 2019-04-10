import os
from unittest import TestCase, skip  # noqa
from unittest.mock import MagicMock, patch

from fixtures import sublack, view
import pathlib
import tempfile


class TestBlackMethod(TestCase):
    def test_get_command_line(self):
        gcl = sublack.blacker.Black.get_command_line
        v = MagicMock()
        s = MagicMock()
        s.config = {
            "black_command": "black",
            "black_line_length": None,
            "black_fast": False,
        }
        s.view.file_name.return_value = "blabla.py"
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-"])

        s.config = {
            "black_command": "black",
            "black_line_length": 90,
            "black_fast": True,
        }
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "-l", "90", "--fast"])

        # test diff
        a = gcl(s, v, extra=["--diff"])
        self.assertEqual(a, ["black", "-", "--diff", "-l", "90", "--fast"])

        # test skipstring
        s.config = {"black_command": "black", "black_skip_string_normalization": True}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--skip-string-normalization"])

        # test py36
        s.config = {"black_command": "black", "black_py36": True}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--py36"])

        # test tearget target-version
        s.config = {"black_command": "black", "black_target_version": ["py36"]}
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--target-version", "py36"])

        # test tearget target-version
        s.config = {"black_command": "black", "black_target_version": ["py36", "py37"]}
        a = gcl(s, v)
        self.assertEqual(
            a, ["black", "-", "--target-version", "py36", "--target-version", "py37"]
        )

        # test pyi
        s.config = {"black_command": "black"}
        s.view.file_name.return_value = "blabla.pyi"
        a = gcl(s, v)
        self.assertEqual(a, ["black", "-", "--pyi"])

    def test_windows_prepare(self):
        with patch.object(sublack.blacker, "sublime") as m:
            m.platform.return_value = "linux"
            wop = sublack.blacker.Black.windows_popen_prepare
            self.assertFalse(wop("r"))
        with patch.object(sublack.blacker, "sublime") as m:
            with patch.object(sublack.blacker, "subprocess"):
                m.platform.return_value = "windows"
                wop = sublack.blacker.Black.windows_popen_prepare
                self.assertTrue(wop("r"))

    def test_get_content_encoding(self):
        gc = sublack.blacker.Black.get_content
        s = MagicMock()
        s.view.encoding.return_value = "utf-32"
        c, e = gc(s)
        self.assertEqual(e, "utf-32")

        s.view.encoding.return_value = "Undefined"
        with patch.object(
            sublack.blacker, "get_encoding_from_file", return_value="utf-16"
        ):
            c, e = gc(s)
            self.assertEqual(e, "utf-16")

        s.config = {"black_default_encoding": "latin-1"}
        s.view.encoding.return_value = None
        c, e = gc(s)
        self.assertEqual(e, "latin-1")

    def test_get_content_content(self):
        gc = sublack.blacker.Black.get_content
        s = MagicMock()
        s.view.encoding.return_value = "utf-8"
        s.view.substr.return_value = "héllo"
        c, e = gc(s)
        self.assertEqual(c.decode("utf-8"), "héllo")

    def test_run_black(self):
        rb = sublack.blacker.Black.run_black
        s = MagicMock()
        s.get_cwd.return_value = None
        s.windows_popen_prepare.return_value = None
        a = rb(s, ["black", "-"], os.environ.copy(), None, "hello".encode())
        self.assertEqual(a[0], 0)
        self.assertEqual(a[1], b"hello\n")
        self.assertIn(b"reformatted", a[2])

        with patch.object(sublack.blacker, "sublime"):
            s.windows_popen_prepare.side_effect = OSError
            try:
                a = rb(s, ["black", "-"], os.environ.copy(), None, "hello".encode())
            except OSError as e:
                self.assertEqual(
                    str(e),
                    "You may need to install Black and/or configure 'black_command' in Sublack's Settings.",
                )

    def test_good_working_dir(self):
        gg = sublack.blacker.Black.get_good_working_dir

        # filename ok
        s = MagicMock()
        s.view.file_name.return_value = "/bla/bla.py"
        self.assertEqual("/bla", gg(s))

        # no filenmae, no window
        s.view.file_name.return_value = None
        s.variables.get.return_value = ""
        s.view.window.return_value = None
        self.assertEqual(None, gg(s))

        # not folders
        e = MagicMock()
        s.view.window.return_value = e
        e.folders.return_value = []
        self.assertEqual(None, gg(s))

        # folder dir
        e.folders.return_value = ["/bla", "ble"]
        self.assertEqual("/bla", gg(s))


class TestCache(TestCase):
    def setUp(self):
        # data
        self.view = view()
        self.ah = str(hash("a"))
        self.bh = str(hash("b"))
        self.cmd1 = ["cmd1"]
        self.cache = (
            self.ah + "|||" + str(self.cmd1) + "\n" + self.bh + "|||" + str(self.cmd1)
        )
        # view
        self.black = sublack.blacker.Black(self.view)

        # temp file
        temp = tempfile.NamedTemporaryFile(delete=True)
        temp.close()
        self.black.formatted_cache = pathlib.Path(temp.name)
        with self.black.formatted_cache.open(mode="w") as f:
            f.write(self.cache)

    def tearDown(self):
        self.black.formatted_cache.unlink()
        self.view.set_scratch(True)
        self.view.window().run_command("close_file")

    def test_is_cached(self):

        # test first line present
        self.assertTrue(self.black.is_cached("a", self.cmd1))

        # test second line present
        self.assertTrue(self.black.is_cached("b", self.cmd1))

        # test content ok cmd not ok
        self.assertFalse(self.black.is_cached("b", ["cmd2"]))

        # test contnent not cmd ok
        self.assertFalse(self.black.is_cached("c", self.cmd1))

    def test_add_to_cache(self):

        # test already in , not added
        self.assertFalse(self.black.add_to_cache("a", self.cmd1))

        # test added and contenu
        self.assertTrue(self.black.add_to_cache("c", self.cmd1))
        self.assertEqual(
            self.black.formatted_cache.open().read(),
            "{}|||['cmd1']\n{}|||['cmd1']\n{}|||['cmd1']".format(
                str(hash("c")), self.ah, self.bh
            ),
        )

    def test_limite_cache_size(self):
        ligne = self.ah + "|||" + str(self.cmd1) + "\n"
        with self.black.formatted_cache.open("wt") as f:
            f.write(251 * ligne)

        self.black.add_to_cache("b", self.cmd1)

        new_line = "{}|||['cmd1']".format(self.bh)
        cached = self.black.formatted_cache.open().read().splitlines()
        self.assertEqual(len(cached), 251)
        self.assertEqual(cached[:2], [new_line] + [ligne.strip()])


class TestBlackdClass(TestCase):
    def test_format_header(self):
        self.maxDiff = None

        # dep
        cmd = "black - -l 25 --fast --skip-string-normalization --py36 --target-version py37".split()
        h = sublack.blacker.Blackd.format_headers("self", cmd)
        h["X-Python-Variant"] = set(h["X-Python-Variant"].split(","))
        self.assertEqual(
            h,
            {
                "X-Line-Length": "25",
                "X-Skip-String-Normalization": "1",
                "X-Python-Variant": set(["py3.6", "py3.7"]),
                "X-Fast-Or-Safe": "fast",
            },
        )

        # standard
        cmd = "black - -l 25 --fast --skip-string-normalization --py36".split()
        h = sublack.blacker.Blackd.format_headers("self", cmd)
        self.assertEqual(
            h,
            {
                "X-Line-Length": "25",
                "X-Skip-String-Normalization": "1",
                "X-Python-Variant": "py3.6",
                "X-Fast-Or-Safe": "fast",
            },
        )

        # target-version
        cmd = "black - -l 25 --fast --skip-string-normalization --target-version py36 --target-version py37".split()
        h = sublack.blacker.Blackd.format_headers("self", cmd)
        h["X-Python-Variant"] = set(h["X-Python-Variant"].split(","))
        self.assertEqual(
            h,
            {
                "X-Line-Length": "25",
                "X-Skip-String-Normalization": "1",
                "X-Python-Variant": set(["py3.6", "py3.7"]),
                "X-Fast-Or-Safe": "fast",
            },
        )
