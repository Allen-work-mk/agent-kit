from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import questionary
import typer

from agent_kit_skill_link import API_VERSION, CONFIG_VERSION, PLUGIN_ID, __version__
from agent_kit_skill_link.config import SkillLinkConfig, load_config, save_config
from agent_kit_skill_link.logic import (
    LinkResult,
    SkillStatus,
    UnlinkResult,
    discover_skill_statuses,
    ensure_supported_platform,
    link_skills,
    unlink_skills,
    validate_source_dir,
    validate_target_dir,
)


class InteractiveIO(Protocol):
    def echo(self, message: str) -> None: ...

    def warn(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...

    def prompt_text(self, message: str, default: str | None = None) -> str: ...

    def confirm(self, message: str, default: bool = False) -> bool: ...

    def select_many(self, message: str, choices: Sequence[str]) -> list[str]: ...


class QuestionaryIO:
    def echo(self, message: str) -> None:
        typer.echo(message)

    def warn(self, message: str) -> None:
        typer.echo(message)

    def error(self, message: str) -> None:
        typer.echo(message, err=True)

    def prompt_text(self, message: str, default: str | None = None) -> str:
        kwargs = {"default": default} if default is not None else {}
        answer = questionary.text(message, **kwargs).ask()
        if answer is None:
            raise typer.Abort()
        return answer

    def confirm(self, message: str, default: bool = False) -> bool:
        answer = questionary.confirm(message, default=default).ask()
        if answer is None:
            raise typer.Abort()
        return bool(answer)

    def select_many(self, message: str, choices: Sequence[str]) -> list[str]:
        answer = questionary.checkbox(
            message,
            choices=[questionary.Choice(title=choice, value=choice) for choice in choices],
        ).ask()
        if answer is None:
            raise typer.Abort()
        return list(answer)


@dataclass(slots=True)
class PluginRuntime:
    logger: logging.Logger
    cwd: Path
    config_root: Path
    data_root: Path
    cache_root: Path
    io: InteractiveIO


def default_runtime_factory() -> PluginRuntime:
    return PluginRuntime(
        logger=logging.getLogger(f"agent-kit.{PLUGIN_ID}"),
        cwd=Path.cwd(),
        config_root=Path(os.environ.get("AGENT_KIT_CONFIG_DIR", "~/.config/agent-kit")).expanduser(),
        data_root=Path(os.environ.get("AGENT_KIT_DATA_DIR", "~/.local/share/agent-kit")).expanduser(),
        cache_root=Path(os.environ.get("AGENT_KIT_CACHE_DIR", "~/.cache/agent-kit")).expanduser(),
        io=QuestionaryIO(),
    )


def build_app(runtime_factory=default_runtime_factory) -> typer.Typer:
    app = typer.Typer(help="Link selected local skills into a target directory.", no_args_is_help=True, add_completion=False)

    @app.callback(invoke_without_command=True)
    def app_callback(
        ctx: typer.Context,
        plugin_metadata: bool = typer.Option(
            False,
            "--plugin-metadata",
            help="Print plugin metadata as JSON.",
            is_eager=True,
        ),
    ) -> None:
        if plugin_metadata:
            typer.echo(
                json.dumps(
                    {
                        "plugin_id": PLUGIN_ID,
                        "installed_version": __version__,
                        "api_version": API_VERSION,
                        "config_version": CONFIG_VERSION,
                    }
                )
            )
            raise typer.Exit()

    @app.command("init")
    def init_command() -> None:
        runtime = runtime_factory()
        _run_init(runtime)

    @app.command("list")
    def list_command() -> None:
        runtime = runtime_factory()
        config = _require_config(runtime)
        _ensure_runtime_ready(runtime, config, require_target_exists=False)
        statuses = discover_skill_statuses(config)
        if not statuses:
            runtime.io.warn("No skills found in the configured source directory.")
            return
        for status in statuses:
            runtime.io.echo(f"{status.name} [{status.status}]")

    @app.command("link")
    def link_command() -> None:
        runtime = runtime_factory()
        config = _require_config(runtime)
        _ensure_runtime_ready(runtime, config, require_target_exists=True)
        statuses = discover_skill_statuses(config)
        available = [status.name for status in statuses if status.status == "not_linked"]
        if not available:
            runtime.io.warn("No skills are available to link.")
            return
        selected = runtime.io.select_many("Select skills to link", available)
        if not selected:
            runtime.io.warn("No skills selected.")
            return
        result = link_skills(config, selected)
        _report_link_result(runtime, result)
        if result.conflicts:
            raise typer.Exit(code=1)

    @app.command("unlink")
    def unlink_command() -> None:
        runtime = runtime_factory()
        config = _require_config(runtime)
        _ensure_runtime_ready(runtime, config, require_target_exists=True)
        statuses = discover_skill_statuses(config)
        removable = [status.name for status in statuses if status.status == "linked"]
        if not removable:
            runtime.io.warn("No managed links are available to unlink.")
            return
        selected = runtime.io.select_many("Select skills to unlink", removable)
        if not selected:
            runtime.io.warn("No skills selected.")
            return
        result = unlink_skills(config, selected)
        _report_unlink_result(runtime, result)

    @app.command("status")
    def status_command() -> None:
        runtime = runtime_factory()
        config = _require_config(runtime)
        source_available = config.source_dir.exists() and config.source_dir.is_dir()
        target_available = config.target_dir.exists() and config.target_dir.is_dir()
        statuses = discover_skill_statuses(config) if source_available else []
        counts = _status_counts(statuses)
        runtime.io.echo(f"source_dir: {config.source_dir}")
        runtime.io.echo(f"source_available: {_format_yes_no(source_available)}")
        runtime.io.echo(f"target_dir: {config.target_dir}")
        runtime.io.echo(f"target_available: {_format_yes_no(target_available)}")
        runtime.io.echo(f"total: {len(statuses)}")
        for name in ("linked", "not_linked", "broken_link", "conflict"):
            runtime.io.echo(f"{name}: {counts[name]}")

    return app


def main() -> None:
    build_app()()


def _require_config(runtime: PluginRuntime) -> SkillLinkConfig:
    config = load_config(runtime.config_root)
    if config is None:
        runtime.io.warn("skill-link is not configured. Starting init.")
        config = _run_init(runtime)
    return config


def _run_init(runtime: PluginRuntime) -> SkillLinkConfig:
    ensure_supported_platform()
    existing = load_config(runtime.config_root)
    source_dir = _prompt_for_source_dir(runtime, existing.source_dir if existing else None)
    target_dir = _prompt_for_target_dir(runtime, existing.target_dir if existing else None)
    config = SkillLinkConfig(source_dir=source_dir, target_dir=target_dir)
    path = save_config(runtime.config_root, config)
    runtime.io.echo(f"Saved configuration to {path}")
    return config


def _prompt_for_source_dir(runtime: PluginRuntime, default: Path | None) -> Path:
    while True:
        value = runtime.io.prompt_text(
            "Source skills directory",
            default=str(default) if default else None,
        )
        source_dir = Path(value).expanduser()
        try:
            validate_source_dir(source_dir)
            return source_dir
        except ValueError as exc:
            runtime.io.error(str(exc))


def _prompt_for_target_dir(runtime: PluginRuntime, default: Path | None) -> Path:
    while True:
        value = runtime.io.prompt_text(
            "Target skills directory",
            default=str(default) if default else None,
        )
        target_dir = Path(value).expanduser()
        if target_dir.exists():
            try:
                validate_target_dir(target_dir)
                return target_dir
            except ValueError as exc:
                runtime.io.error(str(exc))
                continue
        should_create = runtime.io.confirm(
            f"Create target directory {target_dir}?",
            default=True,
        )
        if not should_create:
            runtime.io.warn("Target directory is required.")
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir


def _report_link_result(runtime: PluginRuntime, result: LinkResult) -> None:
    for name in result.linked:
        runtime.io.echo(f"linked {name}")
    for name in result.conflicts:
        runtime.io.error(f"conflict for {name}; resolve it manually")


def _report_unlink_result(runtime: PluginRuntime, result: UnlinkResult) -> None:
    for name in result.unlinked:
        runtime.io.echo(f"unlinked {name}")
    for name in result.skipped:
        runtime.io.warn(f"skipped {name}; target is not a managed link")


def _status_counts(statuses: list[SkillStatus]) -> dict[str, int]:
    counts = {
        "linked": 0,
        "not_linked": 0,
        "broken_link": 0,
        "conflict": 0,
    }
    for status in statuses:
        counts[status.status] += 1
    return counts


def _ensure_runtime_ready(
    runtime: PluginRuntime,
    config: SkillLinkConfig,
    *,
    require_target_exists: bool,
) -> None:
    try:
        validate_source_dir(config.source_dir)
        validate_target_dir(config.target_dir)
    except ValueError as exc:
        runtime.io.error(str(exc))
        raise typer.Exit(code=1) from exc

    if require_target_exists and not config.target_dir.exists():
        runtime.io.error(f"target directory does not exist: {config.target_dir}")
        raise typer.Exit(code=1)


def _format_yes_no(value: bool) -> str:
    return "yes" if value else "no"
