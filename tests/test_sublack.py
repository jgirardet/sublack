    # -*- coding: utf-8 -*-

"""
test_sublack
----------------------------------
Tests for `sublack` module.
"""


# sublack
from sublack import sublack


def test_sublack():
    assert sublack.main() == "hello"

