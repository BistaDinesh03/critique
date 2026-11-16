"""The launcher uses the venv interpreter and never overwrites local settings."""

import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "quickstart.py"


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("critique_quickstart", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tmp_path / "checkout with spaces"
    root.mkdir()
    (root / "backend").mkdir()
    (root / ".env.example").write_text("APP_ENV=development\n", encoding="utf-8")
    (root / "requirements.txt").write_text("-r backend/requirements.txt\n", encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", root)
    return module, root


@pytest.mark.parametrize("platform, expected", [
    ("win32", "Scripts/python.exe"), ("darwin", "bin/python"), ("linux", "bin/python"),
])
def test_environment_interpreter_path(launcher, platform, expected):
    module, root = launcher
    assert module.environment_python(root / ".venv", platform) == root / ".venv" / expected


@pytest.mark.parametrize("existing", [False, True])
def test_prepare_and_start_uses_project_paths_and_preserves_settings(launcher, monkeypatch, existing):
    module, root = launcher
    python = module.environment_python(root / ".venv", module.sys.platform)
    if existing:
        python.parent.mkdir(parents=True)
        python.touch()
        (root / ".env").write_text("SECRET_KEY=local-test-value\n", encoding="utf-8")
    commands = []

    def run(args, **kwargs):
        commands.append((args, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.main(["--port", "8123"]) == 0
    assert any(args[1:3] == ["-m", "venv"] for args, _ in commands) is not existing
    pip = next((args, opts) for args, opts in commands if "install" in args)
    assert pip == ([str(python), "-m", "pip", "install", "-r", str(root / "requirements.txt")],
                   {"cwd": root, "check": True})
    assert commands[-1] == ([str(python), "-m", "uvicorn", "app.main:app", "--reload",
                            "--host", "127.0.0.1", "--port", "8123"], {"cwd": root / "backend"})
    expected = "SECRET_KEY=local-test-value\n" if existing else "APP_ENV=development\n"
    assert (root / ".env").read_text(encoding="utf-8") == expected


def test_missing_pip_is_bootstrapped(launcher, monkeypatch):
    module, root = launcher
    commands = []

    def run(args, **kwargs):
        commands.append(args)
        return SimpleNamespace(returncode=1 if "--version" in args else 0)

    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.main([]) == 0
    bootstrap = next(i for i, args in enumerate(commands) if "ensurepip" in args)
    install = next(i for i, args in enumerate(commands) if "install" in args)
    assert bootstrap < install


def test_dependency_failure_does_not_create_settings_or_start_server(launcher, monkeypatch):
    module, root = launcher
    commands = []

    def run(args, **kwargs):
        commands.append(args)
        if "install" in args:
            raise subprocess.CalledProcessError(1, args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.main([]) == 1
    assert not (root / ".env").exists()
    assert not any("uvicorn" in args for args in commands)


def test_server_exit_code_is_returned(launcher, monkeypatch):
    module, _ = launcher
    monkeypatch.setattr(module.subprocess, "run", lambda args, **kwargs:
                        SimpleNamespace(returncode=7 if "uvicorn" in args else 0))
    assert module.main([]) == 7
