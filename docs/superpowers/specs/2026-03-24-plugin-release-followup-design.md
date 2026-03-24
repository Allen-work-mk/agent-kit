# 插件提交后补发布流程设计

## 摘要

当前仓库已经具备插件发布脚本：

- `./scripts/release/ak-release.sh`
- `scripts/release/release_plugin.py`

但仓库尚未建立一条强制约束，要求 agent 在修改第一方插件并完成功能提交后，继续补做插件版本发布提交与 tag。这样会导致 agent 只完成功能提交，却遗漏后续的版本升级、`uv.lock` 更新、registry 同步和 tag 创建。

本设计新增两层约束：

1. 在仓库 `AGENTS.md` 中明确：当改动涉及 `packages/<plugin>/` 下的第一方插件时，agent 不能只停在功能提交，必须继续执行发布补流程。
2. 在项目目录中新增一个仓库专用 skill：

```bash
./.agents/skills/plugin-release-followup/
```

该 skill 专门负责“插件功能提交后的补发布编排”，而不是负责业务代码修改本身。

## 目标

- 强制 agent 在第一方插件改动后补做版本发布流程
- 把规则写入仓库内文档，而不是依赖口头约定
- 把“插件改动识别 + 发布脚本调用 + 多插件顺序”固化到项目内 skill 中
- 保持当前发布脚本入口不变，继续复用：
  - `./scripts/release/ak-release.sh`

## 非目标

- 不修改当前插件发布脚本的核心发布语义
- 不把这个 skill 做成全局 skill
- 不把这个 skill 设计成通用 release framework
- 不改变“先功能提交，再发布提交”的现有提交模型

## 现状

当前仓库状态：

- 第一方插件位于 `packages/<plugin>/`
- 插件发布入口是 `./scripts/release/ak-release.sh`
- 发布脚本已经负责：
  - bump 版本
  - 执行 `uv lock`
  - 更新两个 registry 副本
  - 创建发布提交
  - 创建插件级 tag

当前缺口：

- agent 在普通开发流程中，没有被强制要求在插件改动后补做发布
- `AGENTS.md` 尚未声明这条约束
- 仓库中没有专门处理这条流程的项目内 skill

## 设计概览

### 1. 规则层

新增仓库级约束：

- 当 agent 的改动涉及 `packages/<plugin>/` 下任意第一方插件时，不能只做功能提交
- 功能提交完成后，必须继续执行插件发布补流程
- 发布补流程必须通过项目内 skill 执行，不能依赖 agent 自行临时拼接步骤

### 2. skill 层

新增项目内 skill：

```bash
./.agents/skills/plugin-release-followup/
```

该 skill 的职责非常窄，只处理：

- 检测哪些第一方插件发生了改动
- 在功能提交完成后，逐个调用发布脚本
- 生成连续的发布提交与插件级 tag

该 skill 不负责：

- 业务代码修改
- 功能实现设计
- 替代普通开发 skill

## AGENTS.md 落点

### 根目录 `AGENTS.md`

新增一条全局流程规则，用于覆盖所有第一方插件：

- 当 agent 的改动涉及 `packages/<plugin>/` 下任意第一方插件时，完成功能提交后必须继续补做插件发布流程
- 该流程必须使用项目内 skill `./.agents/skills/plugin-release-followup/`

### `packages/AGENTS.md`

新增插件目录下的具体执行规则：

- 在 `packages/` 或任意插件目录下工作时，只要本次改动涉及第一方插件并准备提交，必须触发上述 skill
- 不允许只提交功能改动而省略后续发布提交
- 多插件改动时，不允许只发布其中一部分

这样根目录负责“全局约束”，`packages/AGENTS.md` 负责“插件工作区内的具体执行要求”。

## skill 设计

### skill 名称

固定为：

```bash
./.agents/skills/plugin-release-followup/
```

### skill 最小结构

第一版最小结构：

```bash
./.agents/skills/plugin-release-followup/
└── SKILL.md
```

第一版不强制引入额外 `references/` 或 `scripts/`，先保持简洁。

### skill 触发条件

当同时满足以下条件时，agent 必须使用该 skill：

1. 本次工作改动涉及 `packages/<plugin>/`
2. 该插件属于第一方插件
3. agent 准备提交，或已经完成功能提交，需要进入收尾流程

### skill 流程

#### 阶段一：提交前检测

skill 先识别本次改动影响了哪些第一方插件：

- 从工作区 diff 或提交范围中提取受影响插件目录
- 形成受影响插件列表
- 如果没有插件目录改动，则 skill 退出，不接管后续流程

#### 阶段二：功能提交

agent 先完成正常功能提交。

该提交只承载功能改动，不混入发布脚本自动生成的版本 bump 与 registry 更新。

#### 阶段三：提交后补发布

功能提交完成后，skill 按受影响插件列表逐个执行：

```bash
./scripts/release/ak-release.sh <plugin-id> <bump-type>
```

每个插件各自产生：

- 一个发布提交
- 一个插件级 tag

### 多插件策略

如果一次功能提交改动了多个插件：

- 允许一次功能提交后产生多个连续发布提交
- 所有受影响插件都必须发布
- 固定按 `plugin_id` 字典序逐个发布

采用字典序是为了让行为稳定、可预测，并避免依赖 diff 顺序或临时人工排序。

### bump 类型策略

skill 不应随意猜测版本类型。

固定规则：

- 如果当前任务上下文已经明确版本语义，则直接使用该类型
- 如果上下文没有明确，skill 默认使用 `patch`
- 第一版不允许在无明确信号时自动推断为 `minor` 或 `major`

也就是说，默认值只收敛到 `patch`。

## 为什么仅写 AGENTS.md 不够

只写 `AGENTS.md` 只能表达“应该做”，不能稳定表达“如何做”。

本需求本质上包含一条有状态的收尾流程：

- 检测插件改动
- 区分功能提交与发布提交
- 识别多插件场景
- 逐个执行发布脚本

因此需要 skill 把流程编排固定下来，否则 agent 很容易：

- 忘记发布补动作
- 漏掉某个插件
- 提交顺序错误
- 在多插件场景下只处理一个插件

## 用户可见行为

本设计不会改变插件发布脚本入口本身，仍然沿用：

```bash
./scripts/release/ak-release.sh <plugin-id> <patch|minor|major>
```

变化发生在 agent 工作约束上：

- agent 修改插件并提交后，不能直接结束任务
- agent 需要继续触发发布脚本完成版本发布收尾

## 测试与验收建议

实现阶段至少需要覆盖：

1. `AGENTS.md` 与 `packages/AGENTS.md` 已写入强制规则
2. 项目内 skill 已创建到 `./.agents/skills/plugin-release-followup/`
3. skill 文案明确触发条件、顺序和多插件策略
4. skill 文案明确默认 bump 为 `patch`
5. 文档中不存在“只建议、不强制”的模糊措辞

## 风险与取舍

### 风险

- 仅靠文档规则可能触发不稳定
- 仅靠 skill 而不写 `AGENTS.md`，则仓库约束缺乏显式来源

### 取舍结论

采用“双层约束”：

- `AGENTS.md` 负责规则声明
- 项目内 skill 负责流程执行

这是当前约束强度与维护成本之间最平衡的方案。
