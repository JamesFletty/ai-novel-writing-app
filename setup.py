#!/usr/bin/env python3
"""Cross-platform development setup for AI Novel Writer."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parent


def run(command: Sequence[str], *, cwd: Path = ROOT) -> None:
    """Run a setup command and fail with its exit status."""
    printable = " ".join(str(part) for part in command)
    print(f"[setup] {printable}")
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def require_prerequisites() -> str:
    """Validate versions required by the current dependencies."""
    if sys.version_info < (3, 11):
        raise SystemExit(
            f"Python 3.11+ is required by the GitHub Copilot SDK; found {platform.python_version()}"
        )

    node = shutil.which("node")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not node or not npm:
        raise SystemExit("Node.js 18+ and npm are required")

    node_version = subprocess.check_output([node, "--version"], text=True).strip().lstrip("v")
    try:
        node_major = int(node_version.split(".", 1)[0])
    except ValueError as exc:
        raise SystemExit(f"Could not parse Node.js version: {node_version}") from exc
    if node_major < 18:
        raise SystemExit(f"Node.js 18+ is required; found {node_version}")

    print(f"[setup] Python {platform.python_version()}, Node.js {node_version}")
    return npm


def backend_python(venv: Path) -> Path:
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def setup_backend() -> Path:
    backend = ROOT / "backend"
    venv = backend / "venv"
    if not venv.exists():
        run([sys.executable, "-m", "venv", str(venv)])

    python = backend_python(venv)
    run([python, "-m", "pip", "install", "--upgrade", "pip"], cwd=backend)
    run([python, "-m", "pip", "install", "-r", "requirements.txt"], cwd=backend)

    # GitHub recommends this one-time download for the Python Copilot SDK.
    run([python, "-m", "copilot", "download-runtime"], cwd=backend)

    env_file = backend / ".env"
    if not env_file.exists():
        shutil.copyfile(backend / ".env.example", env_file)
        print("[setup] Created backend/.env from .env.example")

    run([python, "-c", "from db.database import init_db; init_db()"], cwd=backend)
    return python


def setup_frontend(npm: str) -> None:
    frontend = ROOT / "frontend"
    install_command = [npm, "ci"] if (frontend / "package-lock.json").exists() else [npm, "install"]
    run(install_command, cwd=frontend)


def verify(python: Path, npm: str) -> None:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    run([python, "-m", "pytest", "-q"], cwd=backend)
    run([npm, "test"], cwd=frontend)
    run([npm, "run", "build"], cwd=frontend)


def main() -> None:
    print("AI Novel Writer setup")
    npm = require_prerequisites()
    python = setup_backend()
    setup_frontend(npm)
    verify(python, npm)

    activate = "venv\\Scripts\\activate" if platform.system() == "Windows" else "source venv/bin/activate"
    print("\nSetup complete. Before live generation, authenticate this machine with the GitHub account that owns your Copilot plan.")
    print(f"Backend:  cd backend && {activate} && uvicorn app:app --reload")
    print("Frontend: cd frontend && npm start")
    print("Open:     http://localhost:3000")
    print("Docs:     http://localhost:8000/docs")


if __name__ == "__main__":
    main()
