PACKAGE_NAME = "sublack"
SETTINGS_FILE_NAME = f"{PACKAGE_NAME}.sublime-settings"
SETTINGS_NS_PREFIX = f"{PACKAGE_NAME}."
KEY_ERROR_MARKER = "__KEY_NOT_PRESENT_MARKER__"

# The status sections are ordered by key, so using 'sublk' will place it after
# the SublimeLinter stuff which uses 'subli...'.
STATUS_KEY = "sublk"
BLACK_ON_SAVE_VIEW_SETTING = "sublack.black_on_save"

ENCODING_PATTERN = r"^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)"

ALREADY_FORMATTED_MESSAGE = "sublack: already well formatted"
ALREADY_FORMATTED_MESSAGE_CACHE = "sublack (cache): already well formatted"

REFORMATTED_MESSAGE = "sublack: reformatted"
REFORMATTED_ALL_PARTIAL_MESSAGE = "sublack: partially reformatted all"
REFORMATTED_ALL_MESSAGE = "sublack: reformatted all"
REFORMAT_ERRORS = "sublack: reformatting error, check console for logs"

CONFIG_OPTIONS = [
    "black_line_length",
    "black_fast",
    "black_skip_string_normalization",
    "black_command",
    "black_on_save",
    "black_log",
    "black_log_to_file",
    "black_default_encoding",
    "black_py36",
    "black_target_version",
    "black_use_blackd",
    "black_blackd_host",
    "black_blackd_port",
    "black_blackd_autostart",
    "black_use_precommit",
    "black_confirm_formatall",
]


HEADERS_TABLE = {
    "--fast": {"X-Fast-Or-Safe": "fast"},
    "--skip-string-normalization": {"X-Skip-String-Normalization": "1"},
    "--pyi": {"X-Python-Variant": "pyi"},
    "--py36": {"X-Python-Variant": "py36"},
}

BLACKD_STARTED = "blackd server started on port {}"
BLACKD_START_FAILED = "blackd server failed to start on port {}"
BLACKD_STOPPED = "blackd server stopped"
BLACKD_STOP_FAILED = "failed to stop blackd, check console for logs."
BLACKD_ALREADY_RUNNING = "blackd server is already running on port {}"
