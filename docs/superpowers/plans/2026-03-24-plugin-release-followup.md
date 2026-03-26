# 插件提交后补发布流程 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为所有第一方插件建立强制的“功能提交后补做发布提交”约束，并把流程固化到项目内 skill 与 `AGENTS.md` 中。

**Architecture:** 采用“双层约束”方案。根目录与 `packages/AGENTS.md` 负责声明仓库级规则，项目内 skill `./.agents/skills/plugin-release-followup/` 负责具体流程编排，包括插件改动检测、提交顺序约束和多插件连续发布策略。实现期间通过测试锁定文档与 skill 的关键内容，避免规则退化成模糊说明。

**Tech Stack:** Markdown, pytest, repository-local Codex skills, existing release shell script `./scripts/release/ak-release.sh`

---

## Chunk 1: 规则与 skill 存在性校验

### Task 1: 为规则与 skill 增加回归测试

**Files:**
- Create: `tests/test_plugin_release_followup_policy.py`
- Verify: `AGENTS.md`
- Verify: `packages/AGENTS.md`
- Verify: `.agents/skills/plugin-release-followup/SKILL.md`

- [ ] **Step 1: 写失败测试，锁定根目录 AGENTS 规则**

```python
from pathlib import Path


def test_root_agents_requires_skill_for_plugin_post_commit_release():
    content = Path("AGENTS.md").read_text(encoding="utf-8")
    assert "./.agents/skills/plugin-release-followup/" in content
    assert "packages/<plugin>" in content
    assert "功能提交完成后" in content
    assert "必须" in content
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/test_plugin_release_followup_policy.py -k root_agents -v`  
Expected: FAIL，提示根目录 `AGENTS.md` 里缺少新规则

- [ ] **Step 3: 追加失败测试，锁定 packages/AGENTS 规则与 skill 内容**

```python
def test_packages_agents_requires_followup_release_for_all_first_party_plugins():
    content = Path("packages/AGENTS.md").read_text(encoding="utf-8")
    assert "./.agents/skills/plugin-release-followup/" in content
    assert "多插件" in content
    assert "不允许只发布其中一部分" in content


def test_project_local_skill_exists_with_required_workflow_constraints():
    content = Path(".agents/skills/plugin-release-followup/SKILL.md").read_text(encoding="utf-8")
    assert "plugin-release-followup" in content
    assert "packages/<plugin>" in content
    assert "./scripts/release/ak-release.sh" in content
    assert "先功能提交" in content
    assert "后续发布提交" in content
    assert "patch" in content
    assert "字典序" in content
```

- [ ] **Step 4: 运行整组策略测试，确认失败点正确**

Run: `uv run pytest tests/test_plugin_release_followup_policy.py -v`  
Expected: FAIL，只因文档/skill 尚未创建或未满足约束

- [ ] **Step 5: 提交测试脚手架**

```bash
git add tests/test_plugin_release_followup_policy.py
git commit -m "补充插件补发布流程策略测试"
```

### Task 2: 更新 AGENTS 规则

**Files:**
- Modify: `AGENTS.md`
- Modify: `packages/AGENTS.md`
- Verify: `docs/superpowers/specs/2026-03-24-plugin-release-followup-design.md`

- [ ] **Step 1: 在根目录 AGENTS.md 增加全局提交流程约束**

需要新增一段明确规则，内容必须包含：

- 改动涉及 `packages/<plugin>/` 下任意第一方插件时，不能只停在功能提交
- 功能提交完成后，必须继续补做插件发布流程
- 该流程必须使用项目内 skill `./.agents/skills/plugin-release-followup/`

- [ ] **Step 2: 在 packages/AGENTS.md 增加插件目录下的具体执行要求**

需要新增一段明确规则，内容必须包含：

- 在 `packages/` 或任意第一方插件目录下工作并准备提交时，必须触发该 skill
- 不允许只提交功能改动而省略后续发布提交
- 多插件改动时，不允许只发布其中一部分

- [ ] **Step 3: 运行策略测试，确认 AGENTS 相关断言转绿**

Run: `uv run pytest tests/test_plugin_release_followup_policy.py -k 'root_agents or packages_agents' -v`  
Expected: PASS

- [ ] **Step 4: 检查文案是否仍与 spec 一致**

Run: `sed -n '1,240p' AGENTS.md && printf '\n---\n' && sed -n '1,240p' packages/AGENTS.md`  
Expected: 新规则与 spec 中的路径、顺序、强制措辞一致

- [ ] **Step 5: 提交 AGENTS 更新**

```bash
git add AGENTS.md packages/AGENTS.md
git commit -m "补充插件提交后补发布约束"
```

## Chunk 2: 项目内 skill 创建

### Task 3: 使用 skill creator 产出项目内 skill

**Files:**
- Create: `.agents/skills/plugin-release-followup/SKILL.md`
- Optional Create: `.agents/skills/plugin-release-followup/agents/openai.yaml`（仅在项目内技能发现需要 UI 元数据时）
- Verify: `/Users/elex-mb0203/.agents/skills/skill-creator/SKILL.md`
- Verify: `/Users/elex-mb0203/.codex/skills/.system/skill-creator/SKILL.md`

- [ ] **Step 1: 先阅读 skill creator 指南，按其流程起草 skill**

Run:  
`sed -n '1,220p' /Users/elex-mb0203/.agents/skills/skill-creator/SKILL.md`  
`sed -n '1,220p' /Users/elex-mb0203/.codex/skills/.system/skill-creator/SKILL.md`

Expected: 明确项目内 skill 的最小结构、frontmatter 和触发描述写法

- [ ] **Step 2: 编写项目内 skill 的 frontmatter**

`SKILL.md` 头部至少包含：

```yaml
---
name: plugin-release-followup
description: 当修改 agent-kit 仓库中 `packages/<plugin>/` 下的第一方插件并准备提交或已经完成功能提交时，必须使用本 skill 检测受影响插件，并在功能提交后继续调用 `./scripts/release/ak-release.sh` 完成补发布。多插件改动时也必须使用本 skill，按 `plugin_id` 字典序逐个发布。
---
```

- [ ] **Step 3: 编写 skill 主体流程**

`SKILL.md` 正文必须明确：

- 前置检测：识别受影响插件列表
- 功能提交：先做正常功能提交
- 后置发布：再逐个运行 `./scripts/release/ak-release.sh <plugin-id> <bump-type>`
- 多插件顺序：按 `plugin_id` 字典序
- bump 默认值：上下文未明确时默认 `patch`
- 禁止事项：
  - 不允许只停在功能提交
  - 不允许只发布部分插件
  - 不允许擅自把默认 bump 提升为 `minor` 或 `major`

- [ ] **Step 4: 运行策略测试，确认 skill 内容断言转绿**

Run: `uv run pytest tests/test_plugin_release_followup_policy.py -k skill -v`  
Expected: PASS

- [ ] **Step 5: 手工检查 skill 是否足够窄**

Run: `sed -n '1,260p' .agents/skills/plugin-release-followup/SKILL.md`  
Expected: skill 只管“插件提交后补发布”，不混入业务开发说明

- [ ] **Step 6: 提交项目内 skill**

```bash
git add .agents/skills/plugin-release-followup/SKILL.md
git commit -m "新增插件提交后补发布技能"
```

## Chunk 3: 验证与收尾

### Task 4: 完整验证规则与 skill 集成

**Files:**
- Verify: `AGENTS.md`
- Verify: `packages/AGENTS.md`
- Verify: `.agents/skills/plugin-release-followup/SKILL.md`
- Verify: `tests/test_plugin_release_followup_policy.py`

- [ ] **Step 1: 运行新增测试文件**

Run: `uv run pytest tests/test_plugin_release_followup_policy.py -v`  
Expected: 全部 PASS

- [ ] **Step 2: 运行整仓测试，确认没有回归**

Run: `uv run pytest`  
Expected: 全部 PASS

- [ ] **Step 3: 检查 diff 质量**

Run: `git diff --check`  
Expected: 无输出

- [ ] **Step 4: 核对工作区状态**

Run: `git status --short`  
Expected: 只剩下本任务预期文件，或为空

- [ ] **Step 5: 生成最终收尾提交**

如果前面按任务分批提交，则这里不再额外合并提交。  
如果执行时选择一次性提交，至少要保证提交信息为中文，例如：

```bash
git add AGENTS.md packages/AGENTS.md .agents/skills/plugin-release-followup/SKILL.md tests/test_plugin_release_followup_policy.py
git commit -m "建立插件提交后补发布约束"
```
