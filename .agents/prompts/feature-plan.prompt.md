---
description: 接一个设计文档中的需求，写实施计划并直接执行到"待提交"（不审核）
version: 1.0.0
last_updated: 2026-11-15
kind: feature / no-audit
inputs:
  - "需求：.design/docs/<module>/<file>.md#<需求标识>"
  - "补充（可选）：限制条件"
---

# 功能任务 · 写实施计划并直接执行

输入是**设计文档里的一个需求**。产出是一个计划目录、按计划改完的代码、以及停在"待提交"的一次提交候选。

<!-- 公共段：§0 与 §6 与本目录另三份逐字一致（标记 common:exec / common:wrapup）。改一处必须四份同改，版本一起升。 -->

<!-- common:exec -->
## 0. 执行约定

- 本文件是**执行指令**：读完即开工，不要复述本文件、不要问"是否开始"。
- 除标注 **【硬停机】** 的位置外，不提问、不等确认。信息不全时按本文默认推定继续，推定内容写进 `plan.md` 的「决策记录」，并在最终输出里单列"推定项"。
- 规则来源：`spec/` > 本文件。文中写"见 `spec/<目录>/<文件>.md` 第 N 章"的都必须实际打开读，不得凭印象执行——本文件只规定顺序与出口条件，不复述规则。
- 每完成一步就更新 `STATUS.md` 的 `Next Action`，不要攒到结束。
- 禁止：跳过 `plan.md` 直接改代码；修改 `.design/` 内任何文件；未经记录扩大范围（多改一个文件也算）；编造日期、命令输出、测试结果。
- 输出语言：简体中文。路径一律写仓库相对路径。
<!-- /common:exec -->

## 1. 输入

```text
需求：<设计文档路径>#<需求标识>
补充（可选）：<限制，例如"只做后端，前端不动"；没有就整行省略>
```

- 设计文档路径是 `.design/` 下的相对路径，例如 `.design/docs/orders/checkout.md`。
- 需求标识可以是 `REQ-3.2` 这类编号、章节号，或能被唯一检索到的标题片段。
- 缺需求标识且文档里需求多于一条 → **【硬停机】** 列出候选（章节标题 + 首句），要求指定一个。
- 缺文档路径 → 在 `.design/` 下按关键词检索；命中 0 条或多条 → **【硬停机】** 给出结果。
- 「补充」优先于文档：文档要 3 个接口、补充写"只做查询接口"，则范围只含查询接口，并在「决策记录」记一句。

## 2. 前置检查（任一不过即停）

| # | 检查 | 方法 | 不过时 |
| --- | --- | --- | --- |
| 1 | 设计仓就位 | `.design/` 与 `design.lock` 都存在 | **【硬停机】**提示先 clone 到 `.design/` 并按 lock 切 commit |
| 2 | 版本锁定 | `git -C .design rev-parse HEAD` 等于 `design.lock` 的 `commit` | **【硬停机】**不要自行升级：报告两个 SHA 后停，等确认；确认升级后在「决策记录」写原因 |
| 3 | 需求唯一命中 | 只匹配标题行：`grep -nE '^#{1,6}.*<标识>' <文件>`；目录行与正文交叉引用不计 | **【硬停机】**给出候选；同一标识命中多个标题时，取层级最深的一节并记「决策记录」 |
| 4 | 无重复计划 | 扫 `tasks/plans/*/*`，没有同 slug 或同需求标识的计划 | **【硬停机】**报告已存在目录，等确认续做还是新开 |
| 5 | 落盘门槛 | 按 `spec/plans/plan-writing-guide.md` 0.1 与 0.2 共同判定（0.1 命中即建，否则按 0.2 免建） | **【硬停机】**命中 0.2 的免建情形（单文件文案、纯只读调查）→ 不建目录，给改动说明后结束 |

- `design.lock` 缺失**不允许绕过**：`Source` 无法与 lock 一致，写出来的计划必然被审核判"出处不可核"。按第 2 行【硬停机】处理。
- 仓库当前可能只有规范、没有应用代码。此时「范围-改」写**目标路径（新建）**，目录结构以 `spec/module/module-guide.md` 与 `spec/frontend/frontend-guide.md` 为准。

## 3. 需求 → 计划

### 3.1 读

读需求段落**全文**，再读它的上下游（依赖说明、数据模型、接口约定、错误码、验收相关章节）。只读不改。

### 3.2 抽取（三级降级，按文档实际形态选一级）

| 文档形态 | 抽取方式 | `Metadata.Source` |
| --- | --- | --- |
| 已成任务卡（有 id 与验收标准） | 直接引用，验收逐条照搬 | `design@<sha>#<卡 id>` |
| 有需求条目/章节，无卡 | 从正文抽目标、验收、范围、前置条件 | `design@<sha>#<需求标识>` |
| 只有散落描述 | 按第 1 段硬停机处理，不自行编需求 | — |

- `Revision` 取文档里该需求的版本/修订号；没有则写 `1`，并在「决策记录」注"文档未标版本"。
- 验收标准必须可判定（命令 + 期望输出 / 接口返回 / 页面行为）。抽不出判定条件的条目**不要编**：写成 `- [ ] <原文> —— 待确认判定方式`，并在最终输出列出待确认项。
- 一张需求对应一个计划。需求里明显包含多件可独立交付的事 → 只做第一件，其余写「遗留问题」，并在输出里建议拆成多个需求。
- **【硬停机】**只要 `plan.md` 里还存在任一"待确认判定方式"条目，本计划最高只能到 `Planned`：`Next Action` 写"等待确认第 N 条验收判定方式"，输出后停。不许带着未确认的验收标准开工——第 6.3 节第 2 条会永远凑不出证据。

### 3.3 定标识

| 项 | 规则 |
| --- | --- |
| `topic` | 受影响的模块或领域，`kebab-case`（`orders`、`user-center`）。从「范围-改」的路径前缀取；无代码时从文档模块名转 kebab。**不用** `feature`、`task` 这类词 |
| `plan-id` | `YYYYMMDD-<slug>-NN`。`slug` 是需求的短英文动作短语；`NN` = 扫描 `tasks/plans/<topic>/` 下同日同 slug 的已有目录数 + 1，两位补零，从 `01` 起 |
| `Type` | 新增能力写 `feature`；不改外部行为、只改内部结构写 `refactor` |

### 3.4 定档

本入口**不审核**：`Metadata.Audit` 写 `none`，`Audit Trigger` 写 `none`（理由放「决策记录」，不要写进这个字段——它的取值域是 `none` 或具体命中条目）。

若 3.1 读下来发现命中 `spec/plans/plan-audit-guide.md` 0.2 的任一条（鉴权、金额、不可逆数据、破坏性迁移、并发、对外契约、安全边界、跨 ≥3 模块等），**不要自行改走审核**：在输出里明确建议改用 `feature-plan-audited.prompt.md` 并指出命中哪一条，然后仍按 `none` 落盘继续。

## 4. 落盘

```text
tasks/plans/<topic>/<plan-id>/
├── plan.md
├── STATUS.md
└── artifacts/        # 空目录也建
```

- `plan.md` 的 `Metadata` 十一项写全（`Issue: none`），模板照 `spec/plans/plan-writing-guide.md` 第 2 章，字段一个不少。
- 「步骤」每步带「文件 / 动作 / 验证 / 状态」，粒度到"能单独验证"，不许写"实现整个模块"。
- `STATUS.md` 三行，`Current Status: Planned`，`Next Action` 指向第 1 步。
- 写完执行 `python scripts/tasks-index.py`（索引是生成物，禁止手改）。
- **不要创建 `audits/`**（本入口不审核）。
- 写完 `plan.md` 做一次**覆盖核对**：需求/问题里的每条要求都能落到某条验收标准或某个 Step；落不上的补进「遗留问题」并在「决策记录」记一行。覆盖不上就不许开工。
- 「范围-改」出现新建路径时，先读 `spec/module/module-guide.md` 第 1 章或 `spec/frontend/frontend-guide.md` 第 1 章定目录，**列到文件级**，不要现编结构。

## 5. 审核（本入口不启用）

本入口以"计划即定稿"为前提：不创建 `audits/`、不另起会话、不写响应报告，`Metadata.Audit` 固定 `none`。

- 依据：`spec/plans/plan-audit-guide.md` 0.2 —— 未命中任何风险项的简单任务，第一版计划可直接执行。
- 若执行中发现当初判断错了（确实命中风险项），按 `spec/plans/plan-audit-guide.md` 0.3 **升档即补审**：对增量部分补至少一轮独立审核，`Audit` 与 `audits/` 同时更新；当前环境起不了独立会话则 `STATUS` 转 `Blocked`，移交 `feature-plan-audited.prompt.md`。
- **禁止**把 `Audit` 改成 `L2` 却没有 `audits/` 报告——字段声称已审、磁盘上零报告，比不写档位更糟。

<!-- common:wrapup -->
## 6. 实施与收口

### 6.1 执行

按 `plan.md` 的「步骤」顺序做，步与步不并行：

1. 开工前把 `STATUS.md` 改为 `In Progress`。
2. 每步做完：该 Step 的「状态」改「完成」，`STATUS.md` 的 `Next Action` 指向下一步。
3. 验证输出超过 20 行或含日志/JSON → 写入 `artifacts/<步号>-<名称>.log`，`plan.md` 只留一行结论 + 文件名。
4. 实际做法偏离计划 → **先改 `plan.md`**（「范围」「步骤」）再继续，「决策记录」写偏离原因。
5. 外部阻塞 → `STATUS` 转 `Blocked`，「遗留问题」写解除条件，输出说明后停。
6. 同一步的验证连续失败 2 次 → 停下回第 3 段复核计划与需求，**禁止第 3 次直接改**；`STATUS` 写 `Blocked`，把失败次数与现象写进「决策记录」。

### 6.2 测试

不单独设测试阶段：每步的「验证」就是测试。整单元完成后按改动性质补跑：

- 后端：相关模块单测 + 该模块回归（`spec/testing/backend-testing-guide.md`）
- 前端：组件测试 + 受影响页面（`spec/testing/frontend-testing-guide.md`）
- 跨栈或改核心流程：E2E 冒烟（`spec/testing/e2e-testing-guide.md`）

测试失败 → 回 6.1 修。**不新增状态**，也不在计划外顺手改别的。

- 仓库尚无测试框架时（首次落地）：把"建最小可运行骨架（`pyproject.toml` / `package.json` 与测试入口）"写成 Step 0 并进「范围-改」，**不要临时装包**。
- 骨架在本轮建不成 → `STATUS` 转 `Blocked`，`artifacts/unverified.md` 写清哪几条验收没法跑、卡在哪；**不许把"读代码确认"写成验证通过，也不许改 `Verified`**。

### 6.3 闭环五条

按 `spec/workflow/dev-workflow-guide.md` 4.3 逐条核，每条都要能指出磁盘上的证据文件：

| # | 闭合项 | 自检 |
| --- | --- | --- |
| 1 | 范围 | 「改」清单 = 实际 diff；多出的补进清单或还原 |
| 2 | 验收 | 每条验收标准对应一条命令与输出，在 `artifacts/` |
| 3 | 回归 | 相关测试与模块回归通过，输出在 `artifacts/`；缺陷/事故类还要有 `red.log`、`green.log`、`reverse-verify.log` 三份（`spec/workflow/bugfix-workflow-guide.md` 第 6 章） |
| 4 | 记录 | Step 全绿、`最终验证` 逐条对应、「遗留」「回滚」已写、`STATUS` 到 `Verified` |
| 5 | 依赖 | 新依赖进 `docs/deps/decisions.md`；新迁移跑过升降级 |

五条缺一条 → 不许把 `STATUS` 改 `Verified`。

### 6.4 停在待提交

1. `python scripts/tasks-index.py`。**退出码 1 时逐条读 stderr，只改被点名的 `plan.md` / `STATUS.md` 字段，重跑到 0**；两轮仍不为 0 → 原样贴出 stderr，`STATUS` 转 `Blocked`。**不要手改 `tasks/INDEX.md`**（它是生成物）。
2. 按 `spec/git/commit-guide.md` 第 2 章核四件事（范围、验收证据、测试真跑、无敏感文件与生成物）。
3. 按第 4 章用**显式路径**暂存，`git diff --cached` 完整看一遍。**`git rev-parse --show-toplevel` 失败（仓库未初始化）时停在这里报告，不要自行 `git init`。**
4. `STATUS.md` 改 `Verified`。
5. 按第 7 段输出收口报告，**不要自行提交**。
<!-- /common:wrapup -->

## 7. 输出收口报告

```text
plan-id：<...>
type：<feat|fix|refactor|...>
改动：<N> 个文件，+<增> −<删>
验收：<逐条：命令 → 结果摘要>
未执行项：<没有就写"无">
推定项：<第 0 段要求列出，没有就写"无">
待用提交信息：
<type>(<plan-id>): <祈使句结果>

Refs: design@<sha>#<需求标识>
Plan: tasks/plans/<topic>/<plan-id>/
Test: <命令> — <结果摘要>
```

**【硬停机】不要执行 `git commit`、`git push`、开 PR。** 等用户回"提交"再按 `spec/git/commit-guide.md` 第 4 章执行；`Completed` 只在合入后改。
