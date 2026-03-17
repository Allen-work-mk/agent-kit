# Agent Kit 仓库说明

本文件面向整个仓库中的 agent，负责定义全局规则、提供项目总体架构摘要，并把更具体的约束导航到对应目录下的 `AGENTS.md`。

## 1. 全局规则

- 所有 agent 与用户的交流默认使用中文。
- Git 提交信息必须使用中文。
- Markdown 文件、设计文档、说明文档以中文为主。
- 文档中的代码、命令、字段名、包名、类名、函数名、专用技术名词保持英文。
- 代码中的注释与 `log` 默认以中文为主；若属于稳定协议字段或外部接口，字段名保持英文。
- 子目录中的 `AGENTS.md` 默认继承本文件规则；子级只补充和细化，不覆盖本文件中的全局规则。

## 2. 项目总体架构摘要

`agent-kit` 是一个可扩展的 Python CLI 平台，统一入口是 `agent-kit`。

- Core 负责官方插件注册表、插件安装/更新/卸载、版本校验和命令转发。
- 插件运行在各自独立环境中，core 通过子进程调用插件统一入口 `agent-kit-plugin`。
- 当前第一方插件是 `skills-link`，用于把本地 skills 目录按目录粒度链接到目标目录。

## 3. 顶层目录导航

- [src/agent_kit](src/agent_kit)：core 实现
  具体约束见 [src/agent_kit/AGENTS.md](src/agent_kit/AGENTS.md)
- [packages](packages)：所有插件目录
  共享规则见 [packages/AGENTS.md](packages/AGENTS.md)
- [packages/skills-link](packages/skills-link)：当前第一方插件
  插件自身规则见 [packages/skills-link/AGENTS.md](packages/skills-link/AGENTS.md)
- [docs](docs)：设计文档与实施计划

## 4. AGENTS 分层规则

- 根目录 `AGENTS.md` 只放全局规则、总体架构摘要和导航。
- `src/agent_kit/AGENTS.md` 只放 core 相关约束。
- `packages/AGENTS.md` 只放插件共享协议与新增插件约束。
- `packages/<plugin>/AGENTS.md` 只放单个插件自己的业务规则。

## 5. 工作建议

- 先确认当前修改落在 core 还是某个插件目录。
- 进入具体目录后，优先阅读该目录最近的 `AGENTS.md`。
- 修改协议、目录结构或命令形态时，同步更新对应层级的 `AGENTS.md` 与测试。
