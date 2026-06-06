#!/usr/bin/env python3
"""Launch the LangMCP Inspector UI with bundled dummy data."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "apps" / "inspector"
PORT = 5173


def npm_command() -> str:
    return "npm.cmd" if sys.platform == "win32" else "npm"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=APP_DIR, check=check, text=True)


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait_for_server(port: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_port_open(port):
            return True
        time.sleep(0.1)
    return False


def ensure_dependencies(install: bool) -> None:
    if (APP_DIR / "node_modules").is_dir():
        return
    if not install:
        raise SystemExit(
            "apps/inspector/node_modules is missing. Re-run with --install or run "
            "`cd apps/inspector && npm install` first."
        )
    print("Installing inspector frontend dependencies...")
    run([npm_command(), "install"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--screen",
        choices=["health", "threads", "thread", "all"],
        default="all",
        help="Dummy screen to open (default: all).",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Run npm install if frontend dependencies are missing.",
    )
    args = parser.parse_args()

    ensure_dependencies(args.install)

    url_base = f"http://127.0.0.1:{PORT}/inspector.html"
    screens = ["health", "threads", "thread"] if args.screen == "all" else [args.screen]
    urls = [f"{url_base}?mock={screen}" for screen in screens]

    proc: subprocess.Popen[str] | None = None
    if is_port_open(PORT):
        print(f"Reusing existing preview server at http://127.0.0.1:{PORT}/")
    else:
        print(f"Starting Vite preview server in {APP_DIR}...")
        proc = subprocess.Popen(
            [npm_command(), "run", "preview:dummy", "--", "--strictPort"],
            cwd=APP_DIR,
            text=True,
        )
        if not wait_for_server(PORT):
            proc.terminate()
            raise SystemExit(f"Preview server did not start on port {PORT}.")

    try:
        for url in urls:
            print(f"Opening {url}")
            webbrowser.open(url)
        if proc is None:
            print("Existing server was left running.")
            return 0
        print("Press Ctrl+C to stop the preview server.")
        proc.wait()
    except KeyboardInterrupt:
        print("\nStopping preview server...")
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
