# skills-link 插件说明

本目录继承上级 [../AGENTS.md](../AGENTS.md) 与根目录 [../../AGENTS.md](../../AGENTS.md) 的规则，本文只补充 `skills-link` 自身的业务约束。

## 1. 插件目标

`skills-link` 负责把本地 skills 源目录中的技能目录，以目录粒度软链接到目标目录，方便在目标环境中统一使用这些 skills。

## 2. 命令

当前插件对外提供以下命令：

- `agent-kit skills-link init`
- `agent-kit skills-link list`
- `agent-kit skills-link link`
- `agent-kit skills-link unlink`
- `agent-kit skills-link status`

对应实现入口：

- [src/skills_link/plugin_cli.py](src/skills_link/plugin_cli.py)

## 3. 配置

配置文件位置：

- `~/.config/agent-kit/plugins/skills-link/config.jsonc`

当前配置核心字段：

- `plugin_id`
- `config_version`
- `source_dir`
- `target_dir`

配置读写实现：

- [src/skills_link/config.py](src/skills_link/config.py)

## 4. 业务规则

- 只识别 `source_dir` 下一层直接子目录中包含 `SKILL.md` 的目录。
- 只按目录粒度处理 skill，不做文件级选择。
- `link` 只创建目录软链接，不复制文件。
- 若目标位置已存在同名文件、目录或不受管链接，一律视为冲突，不覆盖。
- `unlink` 只删除指向当前 `source_dir` 的受管软链接，不删除真实目录或外部链接。
- 当前仅支持 macOS / Linux，不处理 Windows。

核心业务实现：

- [src/skills_link/logic.py](src/skills_link/logic.py)

## 5. 修改本插件时重点验证

- `init` 是否正确写入插件本地 `config.jsonc`
- `list` 是否正确识别 `linked`、`not_linked`、`broken_link`、`conflict`
- `link` 是否只创建受管软链接并正确报告冲突
- `unlink` 是否只删除受管软链接
- `status` 是否正确汇总 source/target 可用性和状态计数

相关测试：

- [tests/test_skill_link_cli.py](tests/test_skill_link_cli.py)
- [tests/test_skill_link_logic.py](tests/test_skill_link_logic.py)
