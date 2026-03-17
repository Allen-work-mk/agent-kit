from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


def require_module(name: str):
    try:
        return importlib.import_module(name)
    except Exception as exc:  # pragma: no cover - used for red phase
        pytest.fail(f"could not import {name}: {exc}")


def make_layout(paths_module, tmp_path: Path):
    return paths_module.AgentKitLayout(
        config_root=tmp_path / "config",
        data_root=tmp_path / "data",
        cache_root=tmp_path / "cache",
    )


def test_jsonc_loader_accepts_comments_and_keeps_urls(tmp_path: Path):
    jsonc = require_module("agent_kit.jsonc")
    path = tmp_path / "config.jsonc"
    path.write_text(
        '{\n'
        '  // comment\n'
        '  "url": "https://example.com/path",\n'
        '  "value": 1\n'
        '}\n',
        encoding="utf-8",
    )

    data = jsonc.load_jsonc(path)

    assert data == {"url": "https://example.com/path", "value": 1}


def test_registry_refresh_updates_cache_and_cached_entries_override_builtin(tmp_path: Path):
    paths_module = require_module("agent_kit.paths")
    registry_module = require_module("agent_kit.registry")
    layout = make_layout(paths_module, tmp_path)
    builtin_registry = {
        "schema_version": 1,
        "plugins": {
            "skill-link": {
                "plugin_id": "skill-link",
                "display_name": "Skill Link",
                "description": "builtin",
                "source_type": "git",
                "git_url": "https://example.com/repo.git",
                "subdirectory": "packages/agent-kit-skill-link",
                "version": "0.1.0",
                "tag": "v0.1.0",
                "commit": "old",
                "api_version": 1,
                "min_core_version": "0.1.0",
            }
        },
    }
    remote_registry = {
        "schema_version": 1,
        "plugins": {
            "skill-link": {
                "plugin_id": "skill-link",
                "display_name": "Skill Link",
                "description": "remote",
                "source_type": "git",
                "git_url": "https://example.com/repo.git",
                "subdirectory": "packages/agent-kit-skill-link",
                "version": "0.2.0",
                "tag": "v0.2.0",
                "commit": "new",
                "api_version": 1,
                "min_core_version": "0.1.0",
            }
        },
    }

    store = registry_module.RegistryStore(
        layout=layout,
        builtin_registry_loader=lambda: builtin_registry,
        registry_fetcher=lambda url: json.dumps(remote_registry),
    )

    refreshed = store.refresh()
    effective = store.load_effective_registry()

    assert refreshed["skill-link"].version == "0.2.0"
    assert effective["skill-link"].description == "remote"
    assert layout.registry_cache_path.exists()


def test_install_rejects_plugin_ids_not_in_registry(tmp_path: Path):
    paths_module = require_module("agent_kit.paths")
    registry_module = require_module("agent_kit.registry")
    manager_module = require_module("agent_kit.plugin_manager")
    layout = make_layout(paths_module, tmp_path)
    store = registry_module.RegistryStore(
        layout=layout,
        builtin_registry_loader=lambda: {"schema_version": 1, "plugins": {}},
        registry_fetcher=lambda url: "{}",
    )
    manager = manager_module.PluginManager(layout=layout, registry_store=store)

    with pytest.raises(manager_module.PluginError, match="Unknown official plugin"):
        manager.install_plugin("skill-link")


def test_install_rolls_back_when_plugin_metadata_mismatches(tmp_path: Path):
    paths_module = require_module("agent_kit.paths")
    registry_module = require_module("agent_kit.registry")
    manager_module = require_module("agent_kit.plugin_manager")
    layout = make_layout(paths_module, tmp_path)
    store = registry_module.RegistryStore(
        layout=layout,
        builtin_registry_loader=lambda: {
            "schema_version": 1,
            "plugins": {
                "skill-link": {
                    "plugin_id": "skill-link",
                    "display_name": "Skill Link",
                    "description": "plugin",
                    "source_type": "pypi",
                    "package_name": "agent-kit-skill-link",
                    "version": "0.1.0",
                    "api_version": 1,
                    "min_core_version": "0.1.0",
                }
            },
        },
        registry_fetcher=lambda url: "{}",
    )
    manager = manager_module.PluginManager(layout=layout, registry_store=store)

    manager.command_runner = lambda *args, **kwargs: None
    manager.probe_plugin_metadata = lambda plugin_id: {
        "plugin_id": "wrong-plugin",
        "installed_version": "0.1.0",
        "api_version": 1,
        "config_version": 1,
    }
    manager.probe_distribution_metadata = lambda entry: {
        "package_name": "agent-kit-skill-link",
        "version": "0.1.0",
        "direct_url": None,
    }

    with pytest.raises(manager_module.PluginError, match="plugin metadata mismatch"):
        manager.install_plugin("skill-link")

    assert not layout.plugin_data_dir("skill-link").exists()


def test_install_supports_git_source_and_records_latest_version(tmp_path: Path):
    paths_module = require_module("agent_kit.paths")
    registry_module = require_module("agent_kit.registry")
    manager_module = require_module("agent_kit.plugin_manager")
    layout = make_layout(paths_module, tmp_path)
    store = registry_module.RegistryStore(
        layout=layout,
        builtin_registry_loader=lambda: {
            "schema_version": 1,
            "plugins": {
                "skill-link": {
                    "plugin_id": "skill-link",
                    "display_name": "Skill Link",
                    "description": "plugin",
                    "source_type": "git",
                    "git_url": "https://example.com/repo.git",
                    "subdirectory": "packages/agent-kit-skill-link",
                    "version": "0.2.0",
                    "tag": "v0.2.0",
                    "commit": "abc123",
                    "package_name": "agent-kit-skill-link",
                    "api_version": 1,
                    "min_core_version": "0.1.0",
                }
            },
        },
        registry_fetcher=lambda url: "{}",
    )
    manager = manager_module.PluginManager(layout=layout, registry_store=store)

    manager.command_runner = lambda *args, **kwargs: None
    manager.probe_plugin_metadata = lambda plugin_id: {
        "plugin_id": "skill-link",
        "installed_version": "0.2.0",
        "api_version": 1,
        "config_version": 1,
    }
    manager.probe_distribution_metadata = lambda entry: {
        "package_name": "agent-kit-skill-link",
        "version": "0.2.0",
        "direct_url": {"url": "https://example.com/repo.git", "vcs_info": {"vcs": "git", "commit_id": "abc123"}},
    }

    record = manager.install_plugin("skill-link")

    assert record.installed_version == "0.2.0"
    assert record.latest_known_version == "0.2.0"
    assert record.source_type == "git"
    assert record.source_ref.endswith("@abc123#subdirectory=packages/agent-kit-skill-link")


def test_remove_plugin_keeps_config_by_default_and_can_purge(tmp_path: Path):
    paths_module = require_module("agent_kit.paths")
    registry_module = require_module("agent_kit.registry")
    manager_module = require_module("agent_kit.plugin_manager")
    layout = make_layout(paths_module, tmp_path)
    store = registry_module.RegistryStore(
        layout=layout,
        builtin_registry_loader=lambda: {"schema_version": 1, "plugins": {}},
        registry_fetcher=lambda url: "{}",
    )
    manager = manager_module.PluginManager(layout=layout, registry_store=store)

    layout.plugin_config_dir("skill-link").mkdir(parents=True, exist_ok=True)
    layout.plugin_data_dir("skill-link").mkdir(parents=True, exist_ok=True)
    layout.plugin_state_path("skill-link").write_text("{}", encoding="utf-8")

    manager.remove_plugin("skill-link")
    assert layout.plugin_config_dir("skill-link").exists()
    assert not layout.plugin_data_dir("skill-link").exists()

    layout.plugin_data_dir("skill-link").mkdir(parents=True, exist_ok=True)
    layout.plugin_state_path("skill-link").write_text("{}", encoding="utf-8")
    manager.remove_plugin("skill-link", purge_config=True)
    assert not layout.plugin_config_dir("skill-link").exists()


def test_run_plugin_blocks_on_config_version_mismatch(tmp_path: Path):
    paths_module = require_module("agent_kit.paths")
    registry_module = require_module("agent_kit.registry")
    manager_module = require_module("agent_kit.plugin_manager")
    jsonc_module = require_module("agent_kit.jsonc")
    layout = make_layout(paths_module, tmp_path)
    store = registry_module.RegistryStore(
        layout=layout,
        builtin_registry_loader=lambda: {"schema_version": 1, "plugins": {}},
        registry_fetcher=lambda url: "{}",
    )
    manager = manager_module.PluginManager(layout=layout, registry_store=store)
    layout.plugin_data_dir("skill-link").mkdir(parents=True, exist_ok=True)
    layout.plugin_config_dir("skill-link").mkdir(parents=True, exist_ok=True)
    jsonc_module.write_jsonc(
        layout.plugin_config_path("skill-link"),
        {"config_version": 2, "source_dir": "/tmp/source", "target_dir": "/tmp/target"},
    )
    layout.plugin_state_path("skill-link").write_text(
        json.dumps(
            {
                "plugin_id": "skill-link",
                "installed_version": "0.1.0",
                "latest_known_version": "0.1.0",
                "source_type": "git",
                "source_ref": "ref",
                "api_version": 1,
                "config_version": 1,
                "venv_path": str(layout.plugin_venv_dir("skill-link")),
                "executable_path": str(layout.plugin_executable_path("skill-link")),
                "installed_at": "2026-03-17T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    manager.probe_plugin_metadata = lambda plugin_id: {
        "plugin_id": "skill-link",
        "installed_version": "0.1.0",
        "api_version": 1,
        "config_version": 1,
    }

    with pytest.raises(manager_module.PluginError, match="config version mismatch"):
        manager.run_plugin("skill-link", ["status"])
