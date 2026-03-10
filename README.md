<div align="center">

<img src="./static/frontPage.png" alt="Sentinel-Coding Logo" width="75%"/>

自动维护项目文档和工具配置，让 Claude Code 在长期项目里始终读到最新的项目状态

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![Claude Code](https://img.shields.io/badge/Claude_Code-Required-purple.svg)]()

[English](./README-EN.md) | 中文文档

</div>

---

## TL;DR

Sentinel 是一套 Claude Code 插件。它在你的代码仓库里维护一套自动同步的项目文档（项目级、目录级、文件级），让 Claude 每次开新 session 时读到的都是最新代码与架构状态，而不是过时的文档或上次会话留下的上下文。它同时管理工具使用规则——明确约束 Claude 该用哪些工具、不该碰哪些工具。

目标：AI 在第 50 个 session 时，对项目的理解和第 1 个 session 一样准确。

<div align="center">

[![Demo Video](https://img.youtube.com/vi/fgbWpdtwSLU/maxresdefault.jpg)](https://youtu.be/fgbWpdtwSLU)

*点击图片观看演示视频*

</div>

---

## 它具体在做什么

- **维护三层项目文档**：项目级架构快照、目录级模块清单、文件级说明（输入/输出/职责）—— 每一层都会在代码变更后自动同步
- **管理工具路由**：扫描项目可用的 skill 和 MCP 工具，生成路由声明，告诉 Claude 当前项目该用什么、不该用什么
- **保存跨 session（会话） 的经验教训**：把开发过程中发现的约束和踩过的坑结构化记录下来，下个 session 自动加载，避免重复犯错

---

## 你可能遇到过这些问题

如果用 Claude Code 做过超过一周的项目，下面这些情况你大概率遇到过。它们的共同点不是"prompt 写得不够好"，而是项目信息没有跟着代码一起更新，AI 读到了过时的上下文。

**1. 文档与代码脱节，AI 毫不知情**

你三周前把数据库从 PostgreSQL 切到了 SQLite，但 ARCHITECTURE.md 没更新。Claude 开新 session，读到旧文档，照着 PostgreSQL 的方式写代码——而且写得头头是道，看起来完全没问题。直到你跑测试才发现不对。

**2. 工具太多了，AI 选错了**

项目里装了几十个 skill 和 MCP 工具，但没有明确约束哪些是当前项目在用的。Claude 选了一个功能相近但数据范围不对的工具，拿到了空结果，然后得出"数据不存在"的结论——推理过程没有任何错误，只是问错了工具。

**3. 踩过的坑无法跨会话继承**

上个 session 里你发现"批量插入不能用 ORM，要用原生 SQL"，Claude 当场改好了。下个 session，同样的场景，Claude 又生成了 ORM 批量插入——因为那个发现只活在上次的聊天记录里，没有被写进任何持久化的文档。

Sentinel 通过自动同步文档、约束工具路由、结构化保存经验，把这三类问题从"靠人记得去维护"变成"系统自动处理"。

---

## 谁适合用 / 谁不适合

**适合**：
- 使用 Claude Code 进行多 session 项目开发的开发者
- 项目规模已大到 AI 开始"忘记"之前的决策
- 希望项目文档能跟着代码自动更新，而不是靠人手动维护

**不适合**：
- 短期脚本或用完即弃的项目
- 不使用 Claude Code 的项目
- 需要多人实时协作的团队（当前设计主要面向独立开发者工作流）

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
| `/submit-issue` | 直接从 Claude Code 提交 Bug 报告或功能请求到 GitHub |

---

## 架构概览

```
sentinel-coding/
├── .claude/skills/            # 8 个 slash 命令 (人类调用)
│   ├── start/                 # 项目启动
│   ├── routing/               # 工具扫描
│   ├── boundary/              # 边界生成
│   ├── sentinel-loop/         # 迭代开发
│   ├── progress/              # Session 日志
│   ├── export/                # 文档导出
│   ├── call-codex/            # Codex 集成
│   └── submit-issue/          # Issue 提交
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
- `/submit-issue` 需要安装并认证 GitHub CLI（`gh auth login`）
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
