# Agent Kit 仓库说明

本文件面向在本仓库中工作的 agent，目标是降低误判、减少重复探索，并保持实现方向一致。

## 1. 语言与文档规范

- 所有 agent 与用户的交流默认使用中文。
- Git 提交信息必须使用中文。
- 仓库中的 Markdown 文件、设计说明、使用文档、变更说明以中文为主。
- 文档中的代码、命令、字段名、协议字段、包名、类名、函数名、专用技术名词保持英文。
- 代码中的注释以中文为主，必要时保留英文术语。
- 运行时 `log`、CLI 提示、错误提示以中文为主；如果某些字段属于稳定协议或外部接口，字段名保持英文。

## 2. 项目目标

`agent-kit` 是一个可扩展的 Python CLI 平台，目标是提供统一入口管理多个官方插件，并通过子命令执行插件能力。

当前推荐的命令模型是：

- `agent-kit plugins <action>`：管理插件
- `agent-kit <plugin-id> <action>`：执行插件

第一方插件当前只有一个：

- `skills-link`

## 3. 当前实现的核心设计

### 3.1 运行模型

- Core 不直接在当前进程内 import 插件执行主要功能。
- 每个插件运行在自己的独立环境中。
- Core 负责注册表读取、安装、更新、卸载、版本校验、命令转发。
- 插件实际执行通过子进程调用自己的统一入口 `agent-kit-plugin`。

这是当前仓库最重要的架构边界，不要重新引入“core 直接加载插件业务实现”的 in-process 模型，除非明确做架构升级。

### 3.2 配置与数据分层

项目遵循配置、数据、缓存分离：

- 配置目录：`~/.config/agent-kit`
- 数据目录：`~/.local/share/agent-kit`
- 缓存目录：`~/.cache/agent-kit`

对应实现见：

- [src/agent_kit/paths.py](src/agent_kit/paths.py)

插件相关路径规则：

- 插件配置：`~/.config/agent-kit/plugins/<plugin-id>/config.jsonc`
- 插件安装态：`~/.local/share/agent-kit/plugins/<plugin-id>/plugin.json`
- 插件虚拟环境：`~/.local/share/agent-kit/plugins/<plugin-id>/venv`
- 注册表缓存：`~/.cache/agent-kit/registry.json`

### 3.3 官方注册表模型

- 仓库内置基础注册表，同时支持远程官方注册表缓存。
- 只有 `agent-kit plugins refresh` 会刷新本地注册表缓存。
- `install`、`update`、`list`、`info` 默认只读取本地有效注册表，不主动联网。
- 插件安装只允许通过官方 `plugin_id` 触发，不接受任意 PyPI 包名或任意 Git URL。

注册表相关文件：

- 仓库副本：[registry/official.json](registry/official.json)
- 包内副本：[src/agent_kit/official_registry.json](src/agent_kit/official_registry.json)
- 读取逻辑：[src/agent_kit/registry.py](src/agent_kit/registry.py)

注意：

- 上面两个官方注册表文件必须保持同步。
- 若新增或修改官方插件条目，必须同时更新测试。

### 3.4 插件协议

每个插件必须满足以下契约：

- 在自己的环境中暴露统一可执行入口：`agent-kit-plugin`
- 支持 `agent-kit-plugin --plugin-metadata`
- 元数据至少返回：
  - `plugin_id`
  - `installed_version`
  - `api_version`
  - `config_version`

Core 在安装和运行时会依赖该协议做校验。相关实现见：

- [src/agent_kit/plugin_manager.py](src/agent_kit/plugin_manager.py)

## 4. 仓库结构

### 4.1 Core

- [pyproject.toml](pyproject.toml)：workspace 根配置
- [src/agent_kit/cli.py](src/agent_kit/cli.py)：根 CLI 与命令转发
- [src/agent_kit/plugin_manager.py](src/agent_kit/plugin_manager.py)：插件生命周期管理
- [src/agent_kit/registry.py](src/agent_kit/registry.py)：注册表加载与合并
- [src/agent_kit/jsonc.py](src/agent_kit/jsonc.py)：JSONC 读写
- [src/agent_kit/context.py](src/agent_kit/context.py)：基础交互上下文

### 4.2 插件

当前插件目录：

- [packages/skills-link](packages/skills-link)

关键文件：

- [packages/skills-link/src/skills_link/plugin_cli.py](packages/skills-link/src/skills_link/plugin_cli.py)
- [packages/skills-link/src/skills_link/config.py](packages/skills-link/src/skills_link/config.py)
- [packages/skills-link/src/skills_link/logic.py](packages/skills-link/src/skills_link/logic.py)

`skills-link` 当前职责：

- 识别 source 目录下包含 `SKILL.md` 的直接子目录
- 以目录为粒度进行软链接管理
- 提供 `init`、`list`、`link`、`unlink`、`status`

## 5. 开发约束

### 5.1 Python 与依赖管理

- 使用 `uv` 作为依赖与环境管理工具。
- 根仓库是 `uv workspace`。
- 新增插件时优先按 workspace 子包方式接入。

常用命令：

- `uv run pytest`
- `uv run agent-kit --help`
- `uv run agent-kit plugins list`

### 5.2 新增插件时必须满足的最小要求

新增一个官方插件时，至少完成这些事项：

1. 在 `packages/` 下新增独立包。
2. 插件分发名、目录名、`plugin_id` 默认使用短名称，不要再添加 `agent-kit-` 前缀。
3. Python 模块名使用对应的下划线形式，例如 `skills_link`。
4. 暴露 `agent-kit-plugin` script。
5. 实现 `--plugin-metadata`。
6. 定义自己的 `config.jsonc` 结构与 `config_version`。
7. 在两个官方注册表文件中增加条目。
8. 增加 core 生命周期测试和插件自己的 CLI/逻辑测试。

### 5.3 版本语义

这里有两套版本，不要混淆：

- 插件代码版本：包版本，例如 `installed_version`
- 插件配置版本：配置结构版本，例如 `config_version`

Core 会在运行插件前检查配置版本是否与插件元数据兼容。v1 默认不做自动迁移，不兼容时直接阻止执行。

## 6. 测试与验证

重要测试文件：

- [tests/test_core_cli.py](tests/test_core_cli.py)
- [tests/test_plugin_manager.py](tests/test_plugin_manager.py)
- [packages/skills-link/tests/test_skill_link_cli.py](packages/skills-link/tests/test_skill_link_cli.py)
- [packages/skills-link/tests/test_skill_link_logic.py](packages/skills-link/tests/test_skill_link_logic.py)

修改建议：

- 改 core 行为时，优先补 `tests/test_core_cli.py` 或 `tests/test_plugin_manager.py`
- 改插件行为时，优先补插件自己的 CLI/逻辑测试
- 在声称完成前至少执行一次 `uv run pytest`

## 7. 重要注意事项

- 当前实现已经从早期 “entry point + in-process toolkit” 模型迁移到“独立环境 + 子进程插件”模型。
- 若看到历史设计文档与当前代码不一致，以当前代码与测试为准，并在必要时同步更新文档。
- [docs/superpowers/specs/2026-03-16-agent-kit-cli-design.md](docs/superpowers/specs/2026-03-16-agent-kit-cli-design.md) 记录了较早阶段的设计思路，阅读时要注意和现实现状区分。
- 修改注册表、插件安装逻辑、元数据协议时，必须同时检查：
  - CLI 输出
  - `plugin.json` 写入结构
  - JSONC 配置读写
  - 安装/运行时版本校验

## 8. 推荐工作方式

- 先确认本次修改落在 core 还是某个插件。
- 先看测试，再改实现。
- 优先做小步修改，保持 CLI 行为和测试一起收敛。
- 如果修改会影响协议字段、目录结构或命令形态，务必同步更新文档与测试。
