# 项目基础框架

一套**执行规范 + 任务入口 + 执行记录**的组织方式，用来承载 FastAPI + Next.js + PostgreSQL 项目的开发过程。

这个仓库本身**不是可运行的应用**：没有后端服务、没有前端页面、没有依赖清单。它提供的是"任务怎么开始、怎么做、做成什么样算完"的约束，以及承载这些约束的目录结构。应用代码在第一个任务落地时才开始出现。

## 快速开始

1. 把设计文档仓库克隆到 `.design/`（只读，不入库），并在 `design.lock` 里记下依据的 commit。
2. 打开 `.agents/prompts/`，按任务类型选一份入口提示词。
3. 在 AI 会话里说 `读 .agents/prompts/<文件名> 执行`，然后贴一行输入。
4. 只有文件里标注【硬停机】的地方需要你回话，其余它会自己走完。

| 任务是什么 | 用哪份入口 | 计划会不会被审 |
| --- | --- | --- |
| 设计文档里的一个需求 | `feature-plan.prompt.md` | 不审，写完即定稿 |
| 同上，但风险较高 | `feature-plan-audited.prompt.md` | 独立会话/agent 审 1～3 轮 |
| 一个 bug、功能缺陷 | `issue-plan.prompt.md` | 不审 |
| 一个 bug 或线上事故，影响面大 | `issue-plan-audited.prompt.md` | 审 1～3 轮 |

选档的判据是"命中风险项没有"，不是"任务大小"：涉及鉴权、金额、不可逆数据、破坏性迁移、并发、对外契约、安全边界，或有线上事故，就走 audited 两份。具体判定表在 `spec/plans/plan-audit-guide.md` 0.2。

输入只有一行，格式每份文件第 1 段都写了：

```text
需求：.design/docs/orders/checkout.md#REQ-3.2
补充：只做后端，前端不动
```

```text
问题：结算页下单后订单状态停在 pending
预期依据：.design/docs/orders/checkout.md#REQ-3.2
环境：staging / commit 9f3c1ab
```

四份提示词的共同行为：先落盘一份实施计划（`tasks/plans/<topic>/<plan-id>/`），再按计划实施、测试、闭环，最后**停在"待提交"**——打印 diff 摘要与提交信息，等你说"提交"才真正提交。

## 目录

```text
.
├── AGENTS.md              # 给 AI 的工作约定（各工具共用这一份）
├── README.md              # 本文件，给人的导读
├── spec/                  # 规范：必须怎么做（入口 spec/README.md）
│   ├── README.md          #   索引：什么场景读哪份
│   ├── workflow/          #   主流程 + 缺陷修复流程
│   ├── plans/             #   计划撰写、计划审核、审核响应
│   ├── git/               #   提交信息格式与本地提交动作
│   ├── python/            #   Python 编码风格
│   ├── module/            #   后端模块结构
│   ├── frontend/          #   Next.js 前端结构
│   ├── testing/           #   分层测试（入口 + 后端/前端/E2E/回归/数据）
│   ├── logging/           #   日志
│   ├── alembic/           #   数据库迁移
│   ├── dependency/        #   依赖管理
│   └── ci_cd/             #   流水线、构建、部署
├── tasks/                 # 执行记录
│   ├── INDEX.md           #   任务索引（脚本生成，禁止手改）
│   └── plans/             #   一个任务一个目录：plan.md / STATUS.md / artifacts/
├── scripts/               # 工具脚本
├── docs/                  # 项目记录
│   ├── deps/              #   依赖决策、第三方服务登记
│   └── regression/        #   回归登记表 registry.yaml
├── .agents/
│   ├── prompts/           #   四份任务入口提示词
│   └── skills/            #   已安装技能包
└── skills-lock.json       # 技能来源与内容哈希
```

三个根目录的分工不要混：

| 目录 | 回答什么问题 | 谁写 |
| --- | --- | --- |
| `spec/` | 必须怎么做（规则、约束、模板） | 人维护，AI 只读 |
| `tasks/` | 这次做了什么、证据在哪 | AI 写，人看 |
| `docs/` | 项目级的长期记录（依赖为什么引、哪些缺陷已回归） | 人和 AI 都写 |

## 三条不能破的线

1. **设计文档只读**。`.design/` 只克隆不提交，`design.lock` 锁住依据的 commit。发现设计有问题，去设计仓提 issue，本地计划转 `Blocked`——不在项目仓改设计、也不打补丁。
2. **一个计划一次提交**。提交信息 `<type>(<plan-id>): <祈使句>`，带 `Refs` / `Plan` / `Test` 三个 trailer，能从这个提交反查到计划、再反查到设计。
3. **做完要有证据**。闭环五条（范围 / 验收 / 回归 / 记录 / 依赖）缺一条就不算完成，每条都要能在磁盘上指出文件。缺陷修复额外要求 `red.log` → `green.log` → `reverse-verify.log` 三份。

## 常用命令

```bash
# 重建任务索引（状态变化后、提交前跑）
python scripts/tasks-index.py

# 校验索引与计划目录是否一致（不一致退出码 1）
python scripts/tasks-index.py --check

# 打印索引，额外显示每个进行中计划停留了几天
python scripts/tasks-index.py --stdout

# 校验回归登记表与回归用例是否对得上（需要 pyyaml）
uv run python scripts/check_regression_registry.py --collected /tmp/collected.txt
```

`tasks/INDEX.md` 是生成物，从各计划的 `plan.md` 与 `STATUS.md` 推出来，**不要手改**。要改状态就改 `STATUS.md`，要改目标就改 `plan.md`，然后重新生成。

## 规范怎么查

入口是 `spec/README.md`，按"我要做什么"查表。几条常走的直链：

| 我要… | 读这份 |
| --- | --- |
| 搞清楚整体流程、两个入口、状态怎么转 | `spec/workflow/dev-workflow-guide.md` |
| 写计划、判断要不要落盘 | `spec/plans/plan-writing-guide.md` |
| 判断这份计划要不要审、怎么审 | `spec/plans/plan-audit-guide.md` |
| 修 bug、处理事故 | `spec/workflow/bugfix-workflow-guide.md` |
| 写提交信息、切提交 | `spec/git/commit-guide.md` |
| 写测试、处理回归 | `spec/testing/README.md` |
| 加依赖、接第三方 | `spec/dependency/dependency-guide.md` |
| 改表结构 | `spec/alembic/alembic-guide.md` |

## 版本与维护

- `spec/` 下的规范**只用大版本**：`1.0.0` → `2.0.0` → `3.0.0`。每次内容变更只递增第一个版本号，不使用 `1.1.0`、`1.0.1` 这类次版本与修订号，同时更新 front matter 的 `last_updated`。
- 新增规范：在 `spec/<主题>/` 下建文档，命名 `{主题}-guide.md` 或 `{主题}-guidelines.md`，然后更新 `spec/README.md` 的索引表。漏了索引等于没写——没人会翻到。
- `AGENTS.md` 与 `README.md` 的分工：前者是给 AI 的工作约定（硬约束、入口表、禁止事项），后者是给人的导读。两者冲突时以 `spec/` 为准；`spec/` 内部冲突按"正确性 > 保持现有行为 > 可读性 > 简洁性"取舍，并当次修掉。

## 当前状态

- 规范、四份入口提示词、两个脚本已就绪。`check_regression_registry.py` 依赖 `pyyaml`，尚未安装也未实跑。
- **应用代码尚未开始**：`backend/`、`frontend/` 都还不存在，`pyproject.toml` 与 `package.json` 也没有。第一个任务落地时会由计划的 Step 0 建出最小骨架。
- **`.design/` 与 `design.lock` 都还不存在**。第一个功能任务之前需要：克隆设计仓到 `.design/`，按 `spec/workflow/dev-workflow-guide.md` 2.1 的格式建立 `design.lock` 并记录 commit。在此之前，两份 feature 入口会停在"设计仓就位"这道硬停机上。
- `tasks/` 下还没有任何计划，`tasks/INDEX.md` 是空表。
