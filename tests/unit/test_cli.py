import pytest

from tierproxy import _cli


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        _cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "doctor" in out
    assert "usage" in out
    assert "get" not in out


def test_cli_get_subcommand_removed() -> None:
    with pytest.raises(SystemExit):
        _cli.main(["get", "https://example.com"])


def test_cli_requires_subcommand() -> None:
    with pytest.raises(SystemExit):
        _cli.main([])
