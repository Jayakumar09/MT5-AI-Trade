#!/usr/bin/env python3
"""QUANT PILOT — one-command launcher.

Starts the FastAPI backend (port 8000) and the Vite frontend (port 5173).
Copies .env.example -> .env on first run (Demo Mode ON).

Usage:  python run.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "5173")


def banner() -> None:
    print(
        r"""
 ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗████████╗    ██████╗ ██╗██╗      ██████╗ ████████╗
██╔═══██╗██║   ██║██╔══██╗████╗  ██║╚══██╔══╝    ██╔══██╗██║██║     ██╔═══██╗╚══██╔══╝
██║   ██║██║   ██║███████║██╔██╗ ██║   ██║       ██████╔╝██║██║     ██║   ██║   ██║   
██║▄▄ ██║██║   ██║██╔══██║██║╚██╗██║   ██║       ██╔═══╝ ██║██║     ██║   ██║   ██║   
╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║   ██║       ██║     ██║███████╗╚██████╔╝   ██║   
 ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝       ╚═╝     ╚═╝╚══════╝ ╚═════╝    ╚═╝   
"""
    )
    print("  QUANT PILOT — by JAYAKUMAR.ai  |  Liquidity Sweep Multi-Agent Trading Desk\n")


def ensure_env() -> None:
    if not ENV_FILE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        print(f"[setup] Copied {ENV_EXAMPLE.name} -> {ENV_FILE.name} (Demo Mode ON)")


def start_backend() -> subprocess.Popen:
    env = dict(os.environ)
    env.setdefault("MODE", "DEMO")
    print(f"[backend] uvicorn main:app -> http://localhost:{BACKEND_PORT}")
    return subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(BACKEND_DIR),
        env=env,
    )


def start_frontend() -> subprocess.Popen | None:
    if not (FRONTEND_DIR / "node_modules").exists():
        print("[frontend] node_modules missing — run: cd frontend && npm install")
        return None
    print(f"[frontend] vite dev server -> http://localhost:{FRONTEND_PORT}")
    npm = "npm.cmd" if os.name == "nt" else "npm"
    return subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT)],
        cwd=str(FRONTEND_DIR),
        env=dict(os.environ),
    )


def main() -> int:
    banner()
    ensure_env()
    backend = start_backend()
    time.sleep(3)
    frontend = start_frontend()
    print()
    print("=" * 64)
    print(f"  Backend  : http://localhost:{BACKEND_PORT}")
    print(f"  API docs : http://localhost:{BACKEND_PORT}/docs")
    print(f"  Health   : http://localhost:{BACKEND_PORT}/health")
    print(f"  Frontend : http://localhost:{FRONTEND_PORT}")
    print("=" * 64)
    print("  Demo Mode is ON — no broker, no API key needed.")
    print("  Press Ctrl+C to stop both servers.")
    print()
    try:
        webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                print(f"[backend] exited with code {backend.returncode} — restart with: python run.py")
                return backend.returncode or 1
    except KeyboardInterrupt:
        print("\n[shutdown] stopping servers…")
        for proc in (frontend, backend):
            if proc and proc.poll() is None:
                proc.terminate()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())