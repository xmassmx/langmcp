"""Typer CLI: langmcp serve | langmcp doctor."""

from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path

import typer

from langmcp import __version__
from langmcp.config import redact_uri, sanitize_error_message
from langmcp.profiles import ProfileManager
from langmcp.server import run_server
from langmcp.tools.health import _probe_checkpointer, _probe_store

app = typer.Typer(
    name="langmcp",
    help="Development MCP server for LangGraph checkpoint and store inspection.",
    no_args_is_help=True,
)


def _load_profiles(config: Path | None) -> ProfileManager:
    return ProfileManager(config_path=config)


@app.command()
def serve(
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to langmcp.toml",
        exists=False,
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Default profile name (overridable per tool)",
    ),
) -> None:
    """Start the LangMCP stdio MCP server."""
    if profile:
        os.environ["LANGMCP_PROFILE"] = profile
    profiles = _load_profiles(config)
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
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to langmcp.toml",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile to diagnose",
    ),
) -> None:
    """Check profile connectivity, setup status, and package versions."""
    if profile:
        os.environ["LANGMCP_PROFILE"] = profile
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
    failed = False
    try:
        typer.echo("Testing checkpointer read access...")
        cp_ok, cp_setup, cp_warn = _probe_checkpointer(bundle)
        if cp_ok:
            typer.echo("  Checkpointer: connected (read OK)")
            if cp_setup:
                typer.echo("  Checkpointer setup: OK")
            elif cp_warn:
                typer.echo(f"  Checkpointer setup: warning — {cp_warn}", err=True)
        else:
            typer.echo(f"  Checkpointer: FAILED — {cp_warn}", err=True)
            failed = True

        if bundle.store:
            typer.echo("Testing store read access...")
            store_ok, store_setup, store_warn = _probe_store(bundle)
            if store_ok:
                typer.echo("  Store: connected (read OK)")
                if store_setup:
                    typer.echo("  Store setup: OK")
                elif store_warn:
                    typer.echo(f"  Store setup: warning — {store_warn}", err=True)
            else:
                typer.echo(f"  Store: FAILED — {store_warn}", err=True)
                failed = True
        else:
            typer.echo("  Store: skipped (not configured)")
    finally:
        bundle.close()

    _print_package_versions()
    if failed:
        typer.echo(
            "\nConnectivity check failed. Verify URIs and network access.",
            err=True,
        )
        raise typer.Exit(1)
    typer.echo(
        "\nIf setup reported warnings, run LangGraph migrations when you have write access: "
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
