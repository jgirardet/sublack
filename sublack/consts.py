import sublime
import pathlib

PACKAGE_NAME = "sublack"
SETTINGS_FILE_NAME = "{}.sublime-settings".format(PACKAGE_NAME)
SETTINGS_NS_PREFIX = "{}.".format(PACKAGE_NAME)
KEY_ERROR_MARKER = "__KEY_NOT_PRESENT_MARKER__"

# The status sections are ordered by key, so using 'sublk' will place it after
# the SublimeLinter stuff which uses 'subli...'.
STATUS_KEY = "sublk"
BLACK_ON_SAVE_VIEW_SETTING = "sublack.black_on_save"

ENCODING_PATTERN = r"^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)"

ALREADY_FORMATTED_MESSAGE = "Sublack: already well formated !"

REFORMATTED_MESSAGE = "Sublack: reformatted !"

CONFIG_OPTIONS = [
    "black_line_length",
    "black_fast",
    "black_skip_string_normalization",
    "black_command",
    "black_on_save",
    "black_log",
    "black_default_encoding",
    "black_include",
    "black_exclude",
    "black_py36",
    "black_use_blackd",
    "black_blackd_host",
    "black_blackd_port",
    "black_blackd_autostart",
]


HEADERS_TABLE = {
    "--fast": {"X-Fast-Or-Safe": "fast"},
    "--skip-string-normalization": {"X-Skip-String-Normalization": "1"},
    "--pyi": {"X-Python-Variant": {"X-Python-Variant": "pyi"}},
    "--py36": {"X-Python-Variant": {"X-Python-Variant": "3.6"}},
}

BLACKD_STARTED = "Blackd server started on port {}"
BLACKD_START_FAILED = "Blackd server failed to start on port {}"
BLACKD_STOPPED = "Blackd server stopped"
BLACKD_STOP_FAILED = "Blackd stopping failed. check logs."
