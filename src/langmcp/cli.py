"""Typer CLI: langmcp serve | langmcp doctor."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path
from typing import Optional

import typer

from langmcp import __version__
from langmcp.config import redact_uri
from langmcp.profiles import ProfileManager
from langmcp.server import run_server

app = typer.Typer(
    name="langmcp",
    help="Development MCP server for LangGraph checkpoint and store inspection.",
    no_args_is_help=True,
)


def _load_profiles(config: Path | None) -> ProfileManager:
    return ProfileManager(config_path=config)


@app.command()
def serve(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to langmcp.toml",
        exists=False,
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Default profile name (overridable per tool)",
    ),
) -> None:
    """Start the LangMCP stdio MCP server."""
    profiles = _load_profiles(config)
    if profile:
        import os

        os.environ["LANGMCP_PROFILE"] = profile
        profiles = ProfileManager(config_path=config)
    if not profiles.read_only_enforced:
        typer.echo(
            "Error: LangMCP v0.1 requires read_only=true. "
            "Set [defaults] read_only = true in langmcp.toml.",
            err=True,
        )
        raise typer.Exit(1)
    try:
        profiles.get_profile()
    except KeyError as exc:
        if not profiles.config_path:
            typer.echo(
                "Warning: No langmcp.toml found. Create one from examples/langmcp.example.toml.",
                err=True,
            )
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    run_server(profiles)


@app.command()
def doctor(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to langmcp.toml",
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile to diagnose",
    ),
) -> None:
    """Check profile connectivity, setup status, and package versions."""
    profiles = _load_profiles(config)
    typer.echo(f"langmcp {__version__}")
    if profiles.config_path:
        typer.echo(f"Config: {profiles.config_path}")
    else:
        typer.echo("Config: (not found — using env overrides only)")
    if not profiles.list_profiles():
        typer.echo("No profiles configured. Copy examples/langmcp.example.toml to langmcp.toml")
        _print_package_versions()
        raise typer.Exit(0)

    try:
        name, cfg = profiles.get_profile(profile)
    except KeyError as exc:
        typer.echo(f"Profile error: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"Active profile: {name}")
    typer.echo(f"  Checkpointer: {redact_uri(cfg.checkpointer)}")
    if cfg.store:
        typer.echo(f"  Store: {redact_uri(cfg.store)}")
    else:
        typer.echo("  Store: (not configured)")
    typer.echo(f"  Read-only: {profiles.read_only_enforced}")

    from langmcp.adapters.factory import get_adapters

    bundle = get_adapters(profiles, name)
    try:
        typer.echo("Running checkpointer.setup()...")
        bundle.checkpointer.setup()
        typer.echo("  Checkpointer: OK")
    except Exception as exc:
        typer.echo(f"  Checkpointer: FAILED — {exc}", err=True)
    if bundle.store:
        try:
            typer.echo("Running store.setup()...")
            bundle.store.setup()
            typer.echo("  Store: OK")
        except Exception as exc:
            typer.echo(f"  Store: FAILED — {exc}", err=True)
    else:
        typer.echo("  Store: skipped (not configured)")
    bundle.close()

    _print_package_versions()
    typer.echo(
        "\nIf setup failed, run LangGraph migrations: "
        "https://docs.langchain.com/oss/python/langgraph/add-memory"
    )


def _print_package_versions() -> None:
    typer.echo("\nPackage versions:")
    for pkg in (
        "langmcp",
        "langgraph",
        "langgraph-checkpoint",
        "langgraph-checkpoint-postgres",
        "langgraph-checkpoint-sqlite",
        "langgraph-checkpoint-redis",
        "mcp",
    ):
        try:
            typer.echo(f"  {pkg}: {importlib.metadata.version(pkg)}")
        except importlib.metadata.PackageNotFoundError:
            typer.echo(f"  {pkg}: (not installed)")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
