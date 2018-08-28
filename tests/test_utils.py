from unittest import TestCase, skip  # noqa
from unittest.mock import MagicMock, patch

from fixtures import sublack


class TestUtils(TestCase):
    maxDiff = None

    @patch.object(sublack.utils, "sublime", return_value="premiere ligne")
    def test_get_settings(self, subl):
        def fake_get(param, default=None):
            flat = {"sublack.black_on_save": True}
            nested = {"black_debug_on": True}
            if param == "sublack":
                return nested
            elif param.split(".")[0] == "sublack":
                return flat.get(param, sublack.consts.KEY_ERROR_MARKER)
            else:
                raise ValueError("settings must be nested or flat sublack")

        gs = sublack.utils.get_settings

        subl.load_settings.return_value = {
            "black_command": "black",
            "black_on_save": False,
            "black_line_length": None,
            "black_fast": False,
            "black_debug_on": False,
            "black_default_encoding": "utf-8",
            "black_skip_string_normalization": False,
            "black_include": None,
            "black_exclude": None,
            "black_py36": None,
            "black_use_blackd": False,
            "black_blackd_host": "localhost",
            "black_blackd_port": "45484",
        }
        v = MagicMock()
        c = MagicMock()
        v.settings.return_value = c
        c.get = fake_get

        res = {
            "black_command": "black",
            "black_on_save": True,
            "black_line_length": None,
            "black_fast": False,
            "black_debug_on": True,
            "black_default_encoding": "utf-8",
            "black_skip_string_normalization": False,
            "black_include": None,
            "black_py36": None,
            "black_exclude": None,
            "black_use_blackd": False,
            "black_blackd_host": "localhost",
            "black_blackd_port": "45484",
        }

        # settings are all from setting file except on_save
        self.assertDictEqual(res, gs(v))

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
