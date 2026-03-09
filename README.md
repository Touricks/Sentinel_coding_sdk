<div align="center">

<img src="./static/frontPage.png" alt="Sentinel-Coding Logo" width="75%"/>

基于 Claude Code 的编程脚手架 SDK，让长期人机协作真正可靠

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![Claude Code](https://img.shields.io/badge/Claude_Code-Required-purple.svg)]()

[English](./README-EN.md) | 中文文档

</div>

---

## 它解决什么问题

长期的人机协作项目中，AI 的上下文会以三种方式退化：

1. **配置漂移**: `ARCHITECTURE.md` 写着 PostgreSQL，但三个 session 前代码已经切换到 SQLite。AI 继续生成 PostgreSQL 查询。
2. **工具路由混乱**: 40 个可用 skill，AI 忘记了哪些是本项目在用的，开始调用不相关的工具。
3. **反馈回路断裂**: 开发者发现"批量插入不要用 ORM"，但这个教训只活在聊天记录里。下一个 session，AI 又生成了 ORM 批量插入。

Sentinel 通过维护三个同步层来解决这些问题：**文档生命周期**、**工具路由**和**三层审查**。

---

## 谁适合用 / 谁不适合

**适合**:
- 使用 Claude Code 进行多 session 项目开发的开发者
- 项目规模已大到 AI 开始"忘记"之前的决策
- 希望 AI 生成的文档保持与代码同步

**不适合**:
- 一次性脚本或 throwaway 项目
- 不使用 Claude Code 的项目
- 需要多人实时协作的团队（当前设计面向单开发者工作流）

---

## 1 分钟快速开始

```bash
git clone https://github.com/your-username/sentinel-coding.git my-project
cd my-project && git init
pip install -r requirements.txt
```

在 Claude Code 中运行：

```
/start              # 引导式面试 → 生成 PRD, ARCHITECTURE, CLAUDE.md, progress.yaml
/routing            # 扫描可用工具 → 生成工具路由报告 (你审批)
/boundary           # 根据审批结果 → 生成工具边界声明
```

---

## 演示

<div align="center">

[![Demo Video](https://img.youtube.com/vi/fgbWpdtwSLU/maxresdefault.jpg)](https://youtu.be/fgbWpdtwSLU)

*点击图片观看演示视频*

</div>

---

## 你的项目会多出什么

| 文件 | 用途 | 管理者 |
|------|------|--------|
| `PRD.md` | 产品需求文档 | 人类（由 `/start` 生成，之后人类维护） |
| `ARCHITECTURE.md` | 架构快照 | 人类（由 `/start` 生成，之后人类维护） |
| `CLAUDE.md`（根目录） | 规则与约束 | 人类（compaction 提议，人类审批） |
| `progress.yaml` | Session 日志入口 | AI（由 `/progress` 追加） |
| `CLAUDE.md`（各目录） | 目录清单 | AI（chain-trigger 自动同步） |
| YAML front matter | 文件级元数据 | AI（chain-trigger 自动同步） |
| `docs/tool-routing-report.md` | 工具清单 | AI 生成，人类审批 |
| `.claude/rules/tool-boundary.md` | 工具边界声明 | AI（由 `/boundary` 生成） |

---

## 核心工作流

三大支柱：

1. **文档生命周期**: `/start` 启动 → chain-trigger 自动同步 → `/progress` 记录发现 → compaction 晋升至 `CLAUDE.md`
2. **工具路由**: `/routing` 清点工具 → 人类审批 → `/boundary` 生成声明 → 每个 session 自动加载
3. **三层审查**: Tier 1 确定性预检 → Tier 2 跨 LLM 审查（Codex） → Tier 3 自审回退

---

## 功能一览

| 命令 | 说明 |
|------|------|
| `/start` | 通过引导式面试启动新项目，生成 PRD、ARCHITECTURE 和 CLAUDE.md |
| `/routing` | 扫描全局 skill，对照项目上下文生成工具路由报告 |
| `/boundary` | 根据审批后的路由报告生成工具边界声明 |
| `/sentinel-loop` | 基于当前项目状态提议 Ralph Loop 迭代任务 |
| `/progress` | 生成结构化 progress.yaml 条目，含类型化 Candidate |
| `/export` | 合规检查 + 格式渲染，输出可提交的文档 |
| `/call-codex` | 从 Claude Code 中调用 Codex CLI 获取第二意见 |

---

## 架构概览

```
sentinel-coding/
├── .claude/skills/            # 7 个 slash 命令 (人类调用)
│   ├── start/                 # 项目启动
│   ├── routing/               # 工具扫描
│   ├── boundary/              # 边界生成
│   ├── sentinel-loop/         # 迭代开发
│   ├── progress/              # Session 日志
│   ├── export/                # 文档导出
│   └── call-codex/            # Codex 集成
├── .sentinel/                 # SDK 运行时 (隐藏目录)
│   ├── chain_trigger/         # 自动同步管线 (预检 → 交叉审查 → 自审)
│   ├── compaction/            # 知识晋升 (progress.yaml → CLAUDE.md)
│   ├── writeback/             # progress.yaml 读写
│   ├── export/                # AI 写作模式合规检查
│   ├── hooks/                 # Git pre-commit hook (软警告, 永不阻断)
│   ├── templates/             # 7 个文档模板
│   └── scripts/               # 生产提取脚本
└── docs/
    └── getting-started.md     # 详细文档
```

---

## 定制化

- **模板**: 编辑 `.sentinel/templates/` 中的文件修改生成文档的结构
- **合规规则**: 扩展 `.sentinel/export/compliance.py` 添加新的 AI 写作模式检测
- **技能**: 在 `.claude/skills/{name}/SKILL.md` 创建新 skill
- **钩子**: 修改 `.sentinel/hooks/lib/` 中的检查脚本
- **工具路由**: 编辑 `docs/tool-routing-report.md` 后重新运行 `/boundary`

---

## 局限性与假设

- 必须使用 Claude Code（不兼容其他 AI 编码工具）
- 需要 Python 3.11+（用于 `StrEnum`、类型联合语法等）
- Hook 只是软警告 — 提醒但不阻断提交
- `/call-codex` 需要单独安装 Codex CLI
- `/sentinel-loop` 需要安装 Ralph Loop 插件
- 设计面向单开发者工作流，不含多人冲突解决机制

---

## 安装

```bash
git clone https://github.com/your-username/sentinel-coding.git my-project
cd my-project && git init
pip install -r requirements.txt
# 在 Claude Code 中运行: /start
```

## Hook 行为（透明度）

- `pre-commit`: 运行 `check_headers.sh` 和 `check_dir_docs.sh`。在 stderr 输出警告。始终 exit 0。不阻断提交。不修改文件。

---

## 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何贡献。

---

## 许可证

MIT License — 参见 [LICENSE](LICENSE)
