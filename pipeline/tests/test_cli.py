# Written with AI assistance (Claude Code). See AI_USE.md.
"""Phase 0 CLI skeleton (A6): every command exists, and unbuilt ones say which phase builds them."""

import subprocess
import sys

import pytest

from ariadne import __version__, cli

COMMANDS = {
    "derive": 2,
    "plan": 3,
    "validate": 2,
    "package": 4,
    "build-site": 8,
}


def test_help_lists_every_command(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for name in [*COMMANDS, "fetch"]:
        assert name in out


def test_fetch_is_built_and_takes_force(capsys):
    assert "fetch" in cli.BUILT
    with pytest.raises(SystemExit) as exc:
        cli.main(["fetch", "--help"])
    assert exc.value.code == 0
    assert "--force" in capsys.readouterr().out


def test_version_flag_prints_the_package_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


@pytest.mark.parametrize(("command", "phase"), COMMANDS.items())
def test_unbuilt_commands_exit_2_and_name_their_phase(capsys, command, phase):
    args = [command, "--config", "config/sites/x.yaml"] if command == "build-site" else [command]
    args += ["--site", "boxwork"] if command != "build-site" else []
    code = cli.main(args)
    assert code == 2
    err = capsys.readouterr().err
    assert f"Phase {phase}" in err
    assert "not built yet" in err


def test_no_command_prints_help_and_exits_2(capsys):
    assert cli.main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_module_entry_point_runs():
    out = subprocess.run(
        [sys.executable, "-m", "ariadne", "--help"], capture_output=True, text=True, check=True
    ).stdout
    assert "build-site" in out
