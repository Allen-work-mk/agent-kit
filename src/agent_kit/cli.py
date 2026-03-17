from __future__ import annotations

import typer
from typer import Context
from agent_kit.plugin_manager import PluginError, PluginManager


def create_app(
    *,
    manager_factory=PluginManager.from_defaults,
) -> typer.Typer:
    manager = manager_factory()
    app = typer.Typer(
        help="Extensible CLI for official agent-kit plugins.",
        no_args_is_help=True,
        add_completion=False,
        epilog=_build_epilog(manager),
    )

    plugins_app = typer.Typer(help="Manage official plugins.", no_args_is_help=True, add_completion=False)

    @plugins_app.command("refresh")
    def refresh_command() -> None:
        registry = manager.refresh_registry()
        if not registry:
            typer.echo("No plugins in registry.")
            return
        for plugin_id, entry in sorted(registry.items()):
            typer.echo(f"{plugin_id}: {entry.version}")

    @plugins_app.command("list")
    def list_command() -> None:
        for plugin in manager.list_plugins():
            typer.echo(
                f"{plugin.plugin_id}: status={plugin.status} "
                f"installed={plugin.installed_version or '-'} "
                f"available={plugin.available_version or '-'}"
            )

    @plugins_app.command("info")
    def info_command(plugin_id: str) -> None:
        info = manager.get_plugin_info(plugin_id)
        typer.echo(f"plugin_id: {info.plugin_id}")
        typer.echo(f"status: {info.status}")
        typer.echo(f"description: {info.description}")
        typer.echo(f"source_type: {info.source_type}")
        typer.echo(f"available_version: {info.available_version}")
        typer.echo(f"installed_version: {info.installed_version}")
        typer.echo(f"tag: {info.tag}")
        typer.echo(f"commit: {info.commit}")
        typer.echo(f"config_path: {info.config_path}")
        typer.echo(f"venv_path: {info.venv_path}")

    @plugins_app.command("install")
    def install_command(plugin_id: str) -> None:
        record = manager.install_plugin(plugin_id)
        typer.echo(f"installed {record.plugin_id} {record.installed_version}")

    @plugins_app.command("update")
    def update_command(plugin_id: str) -> None:
        record = manager.update_plugin(plugin_id)
        typer.echo(f"updated {record.plugin_id} {record.installed_version}")

    @plugins_app.command("remove")
    def remove_command(plugin_id: str, purge_config: bool = typer.Option(False, "--purge-config")) -> None:
        manager.remove_plugin(plugin_id, purge_config=purge_config)
        typer.echo(f"removed {plugin_id}")

    app.add_typer(plugins_app, name="plugins")

    for plugin in manager.runnable_plugins():
        app.command(
            plugin.plugin_id,
            help=plugin.description,
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        )(_build_plugin_command(manager, plugin.plugin_id))

    return app


def main() -> None:
    try:
        create_app()()
    except PluginError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def _build_plugin_command(manager: PluginManager, plugin_id: str):
    def plugin_command(ctx: Context) -> None:
        result = manager.run_plugin(plugin_id, list(ctx.args))
        if getattr(result, "stdout", ""):
            typer.echo(result.stdout, nl=False)
        if getattr(result, "stderr", ""):
            typer.echo(result.stderr, err=True, nl=False)
        if getattr(result, "returncode", 0):
            raise typer.Exit(code=result.returncode)

    return plugin_command


def _build_epilog(manager: PluginManager) -> str | None:
    broken = manager.broken_plugins()
    if not broken:
        return None
    lines = ["Installed but unavailable plugins:"]
    for plugin in broken:
        lines.append(f"- {plugin.plugin_id}: {plugin.reason}")
    return "\n".join(lines)
