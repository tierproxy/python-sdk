import re

from tierproxy import __version__


def test_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+(?:[a-z]+\d*)?$", __version__), __version__
