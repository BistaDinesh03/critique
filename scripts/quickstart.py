"""Prepare a local environment and start Critique on Windows, macOS or Linux."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def environment_python(directory, platform):
    return directory / ("Scripts/python.exe" if platform == "win32" else "bin/python")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Server address (default: loopback only)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    args = parser.parse_args(argv)
    python = environment_python(ROOT / ".venv", sys.platform)

    try:
        if not python.is_file():
            print("Creating .venv...", flush=True)
            subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], cwd=ROOT, check=True)

        # Environments created by tools such as uv may not include pip.
        pip = subprocess.run([str(python), "-m", "pip", "--version"], cwd=ROOT,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if pip.returncode:
            subprocess.run([str(python), "-m", "ensurepip", "--upgrade"], cwd=ROOT, check=True)
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
                       cwd=ROOT, check=True)

        try:
            with (ROOT / ".env").open("x", encoding="utf-8") as destination:
                with (ROOT / ".env.example").open(encoding="utf-8") as source:
                    shutil.copyfileobj(source, destination)
        except FileExistsError:
            pass

        print(f"Starting Critique at http://{args.host}:{args.port} (Ctrl+C to stop)", flush=True)
        result = subprocess.run([str(python), "-m", "uvicorn", "app.main:app", "--reload",
                                 "--host", args.host, "--port", str(args.port)], cwd=ROOT / "backend")
        return result.returncode
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Quick start failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
