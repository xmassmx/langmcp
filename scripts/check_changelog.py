#!/usr/bin/env python3
"""Require CHANGELOG.md updates when user-facing code changes."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

CHANGELOG = "CHANGELOG.md"
SOURCE_PREFIXES = ("src/", "tests/")


def git_diff_names(base: str, head: str, *, merge: bool) -> list[str]:
    op = "..." if merge else ".."
    out = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base}{op}{head}"],
        text=True,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def requires_changelog(paths: list[str]) -> bool:
    return any(path.startswith(SOURCE_PREFIXES) for path in paths)


def changelog_updated(paths: list[str]) -> bool:
    return CHANGELOG in paths


def check(base: str, head: str, *, merge: bool) -> int:
    paths = git_diff_names(base, head, merge=merge)
    if not paths:
        return 0
    if not requires_changelog(paths):
        return 0
    if changelog_updated(paths):
        return 0
    print(
        "CHANGELOG.md must be updated when files under src/ or tests/ change.\n"
        "Add an entry under ## [Unreleased] in CHANGELOG.md.",
        file=sys.stderr,
    )
    print("\nChanged paths (sample):", file=sys.stderr)
    for path in paths[:20]:
        print(f"  - {path}", file=sys.stderr)
    if len(paths) > 20:
        print(f"  ... and {len(paths) - 20} more", file=sys.stderr)
    return 1


def resolve_refs(args: argparse.Namespace) -> tuple[str, str, bool] | None:
    if args.base:
        return args.base, args.head, True

    event = os.environ.get("GITHUB_EVENT_NAME")
    if event == "pull_request":
        base_ref = os.environ.get("GITHUB_BASE_REF")
        if not base_ref:
            print("Missing GITHUB_BASE_REF for pull_request event.", file=sys.stderr)
            return None
        return f"origin/{base_ref}", "HEAD", True

    if event == "push":
        before = os.environ.get("GITHUB_EVENT_BEFORE", "")
        sha = os.environ.get("GITHUB_SHA", "")
        if not sha or before == "0" * 40 or not before:
            return None
        return before, sha, False

    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        help="Base ref for comparison (e.g. origin/main). Uses GitHub env when omitted.",
    )
    parser.add_argument("--head", default="HEAD", help="Head ref (default: HEAD).")
    args = parser.parse_args(argv)

    resolved = resolve_refs(args)
    if resolved is None:
        return 0
    base, head, merge = resolved
    return check(base, head, merge=merge)


if __name__ == "__main__":
    sys.exit(main())
