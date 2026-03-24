from __future__ import annotations

from pathlib import Path


def test_root_agents_requires_skill_for_plugin_post_commit_release():
    content = Path("AGENTS.md").read_text(encoding="utf-8")

    assert "./.agents/skills/plugin-release-followup/" in content
    assert "packages/<plugin>" in content
    assert "功能提交完成后" in content
    assert "必须" in content


def test_packages_agents_requires_followup_release_for_all_first_party_plugins():
    content = Path("packages/AGENTS.md").read_text(encoding="utf-8")

    assert "./.agents/skills/plugin-release-followup/" in content
    assert "多插件" in content
    assert "不允许只发布其中一部分" in content


def test_project_local_skill_exists_with_required_workflow_constraints():
    content = Path(".agents/skills/plugin-release-followup/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "plugin-release-followup" in content
    assert "packages/<plugin>" in content
    assert "./scripts/release/ak-release.sh" in content
    assert "先功能提交" in content
    assert "后续发布提交" in content
    assert "patch" in content
    assert "字典序" in content
