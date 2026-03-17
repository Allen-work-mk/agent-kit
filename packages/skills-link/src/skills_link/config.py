from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skills_link import CONFIG_VERSION, PLUGIN_ID
from skills_link.jsonc import load_jsonc, write_jsonc


@dataclass(slots=True, frozen=True)
class SkillLinkConfig:
    source_dir: Path
    target_dir: Path


def config_file_path(config_root: Path) -> Path:
    return config_root / "plugins" / PLUGIN_ID / "config.jsonc"


def load_config(config_root: Path) -> SkillLinkConfig | None:
    path = config_file_path(config_root)
    if not path.exists():
        return None

    data = load_jsonc(path)
    if not data:
        return None

    source_dir = data.get("source_dir")
    target_dir = data.get("target_dir")
    if not source_dir or not target_dir:
        return None

    return SkillLinkConfig(
        source_dir=Path(source_dir).expanduser(),
        target_dir=Path(target_dir).expanduser(),
    )


def save_config(config_root: Path, config: SkillLinkConfig) -> Path:
    return write_jsonc(
        config_file_path(config_root),
        {
            "plugin_id": PLUGIN_ID,
            "config_version": CONFIG_VERSION,
            "source_dir": str(config.source_dir),
            "target_dir": str(config.target_dir),
        },
    )
