---
description: 接一个设计文档中的需求，写实施计划后由独立 agent 审核最多 3 轮；第 3 轮后按未关闭项转风险敞口再执行到"待提交"
version: 2.0.0
last_updated: 2026-11-26
kind: feature / audited
inputs:
  - "需求：.design/docs/<module>/<file>.md#<需求标识>"
  - "补充（可选）：限制条件"
---

# 功能任务 · 写实施计划 + 审核后执行

输入是**设计文档里的一个需求**。产出是一个**经过最多 3 轮独立审核、未关闭项已转风险敞口**的计划目录、按计划改完的代码、以及停在"待提交"的一次提交候选。

与 `feature-plan.prompt.md` 的差别不止多一段，共五处：§2 多"审核能力"检查、§3.4 改按 0.2 定档、§4 多建 `audits/` 且 `Next Action` 写"等待第 1 轮审核"、§5 审核循环、§7 多一行 `audit`。审核是强制的，且**不许自审**。

<!-- 公共段：§0 与 §6 与本目录另三份逐字一致（common:exec / common:wrapup）；§5 与 issue-plan-audited.prompt.md 逐字一致（common:audit）。改一处必须同组同改，版本一起升。 -->

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
| 5 | 落盘门槛 | 按 `spec/plans/plan-writing-guide.md` 0.1 与 0.2 共同判定（0.1 命中即建，否则按 0.2 免建） | **【硬停机】**命中 0.2 的免建情形 → 不建目录，给改动说明后结束 |
| 6 | 审核能力 | 当前环境能否起独立会话或子 agent | 不能 → 计划写完后按第 5 段**硬停机**移交，不要自审 |

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
- 验收标准必须可判定（命令 + 期望输出 / 接口返回 / 页面行为）。抽不出判定条件的条目**不要编**：写成 `- [ ] <原文> —— 待确认判定方式`，并在最终输出列出待确认项。**这类条目是审核的主要靶子，先自己标出来比被审出来好。**
- **【硬停机】**只要 `plan.md` 里还存在任一"待确认判定方式"条目，本计划最高只能到 `Planned`：`Next Action` 写"等待确认第 N 条验收判定方式"，输出后停。带着未确认的验收标准去审核，审核者只能判 `reject`。
- 一张需求对应一个计划。需求里明显包含多件可独立交付的事 → 只做第一件，其余写「遗留问题」，并在输出里建议拆成多个需求。

### 3.3 定标识

| 项 | 规则 |
| --- | --- |
| `topic` | 受影响的模块或领域，`kebab-case`（`orders`、`user-center`）。从「范围-改」的路径前缀取；无代码时从文档模块名转 kebab。**不用** `feature`、`task` 这类词 |
| `plan-id` | `YYYYMMDD-<slug>-NN`。`slug` 是需求的短英文动作短语；`NN` = 扫描 `tasks/plans/<topic>/` 下同日同 slug 的已有目录数 + 1，两位补零，从 `01` 起 |
| `Type` | 新增能力写 `feature`；不改外部行为、只改内部结构写 `refactor` |

### 3.4 定档（按 0.2 命中即定，`L2` 优先）

完整判定表见 `spec/plans/plan-audit-guide.md` 0.2，本段只列必须写进 `Metadata` 的两行：

```md
- Audit: <L1|L2>
- Audit Trigger: <命中的具体条目，不写"风险较高">
```

- 命中 `L2` 任一条 → `L2`，审核者必须**不同 agent 或不同模型**（轮次上限同为 3，见第 5 段）。
- 否则命中 `L1` 任一条 → `L1`，换会话即可（轮次上限同为 3）。
- 两条都不命中 → 说明这份需求其实是简单任务：**不要为了走流程而审**，改为输出"建议改用 `feature-plan.prompt.md`（`Audit: none`）"并结束，让用户决定。
- 计划范围扩大后重新判定，**只升不降**。

## 4. 落盘

```text
tasks/plans/<topic>/<plan-id>/
├── plan.md
├── STATUS.md
├── audits/           # 本入口要建（第 5 段写入）
└── artifacts/        # 空目录也建
```

- `plan.md` 的 `Metadata` 十一项写全（`Issue: none`），模板照 `spec/plans/plan-writing-guide.md` 第 2 章，字段一个不少。
- 「步骤」每步带「文件 / 动作 / 验证 / 状态」，粒度到"能单独验证"，不许写"实现整个模块"。
- `STATUS.md` 三行，`Current Status: Planned`，`Next Action` 写 `等待第 1 轮审核`。
- 写完执行 `python scripts/tasks-index.py`。
- 写完 `plan.md` 做一次**覆盖核对**：需求/问题里的每条要求都能落到某条验收标准或某个 Step；落不上的补进「遗留问题」并在「决策记录」记一行。覆盖不上就不许开工。
- 「范围-改」出现新建路径时，先读 `spec/module/module-guide.md` 第 1 章或 `spec/frontend/frontend-guide.md` 第 1 章定目录，**列到文件级**，不要现编结构。
- **此时不要开工**，进入第 5 段。

<!-- common:audit -->
## 5. 审核（写完计划、开工之前）

审核规则唯一来源：`spec/plans/plan-audit-guide.md`（怎么审、八维度、报告模板）；响应规则：`spec/plans/plan-audit-response-guide.md`（逐条处置、改计划哪一节）。本段只规定循环与停机。

### 5.1 循环（N 从 1 起，最多 3 轮）

1. **起独立审核**：另开会话或子 agent，只给三样东西——计划目录 `tasks/plans/<topic>/<plan-id>/`（`analysis.md` 也在里面，缺陷类必须读）、规范路径 `spec/plans/plan-audit-guide.md`、轮次号 `N / 3`。**第 3 轮必须写明"这是最后一轮审核"**。**不得传你的草稿、推理过程、倾向性结论。**
2. **收报告**：产出 `audits/NN-audit.md`，结论必须是 `pass` / `pass-with-changes` / `reject` 三者之一，`blocker` / `major` / `minor` 分级齐全。
3. **判走向**：
   - `pass` → 审核闭合，进入第 6 段。
   - `pass-with-changes` → 必须出响应（下一步），响应闭环后进入第 6 段，不必复审。
   - `reject` 且 `N < 3` → 必须出响应 + 复审，`N + 1` 回到第 1 步。
   - `reject` 且 `N == 3` → **不得起第 4 轮**，出响应后按 5.2 收口并开工。
4. **出响应**：按响应规范逐条处置（`accept` / `partial` / `reject` 需给证据 / `defer` 不得用于 `blocker` / `risk` 只在第 3 轮可用），产出 `audits/NN-response.md`，并把改动落到 `plan.md` 的对应章节。**本阶段禁止改代码。**
5. **复审只核**上一轮的 `blocker`、`major` 与新增项，不重新全审——每轮全审等于每轮推翻自己，轮次收不住。
6. **留痕**：每轮在「决策记录」写一行 `审核第 N 轮：audits/NN-audit.md 结论 <...>（YYYY-MM-DD）`。

### 5.2 三轮之后：最终调整 → 开工

第 3 轮结束即审核关闭，**不再追求 `blocker` 清零**（规则见 `spec/plans/plan-audit-guide.md` 第 5 节）。不论第 3 轮结论是什么：

1. 写 `audits/03-response.md` 逐条处置；未关闭的 `blocker` / `major` 一律用 `risk` 处置。
2. 每个 `risk` 项落到 `plan.md` 的「风险」章节，三要素齐全：**后果 / 检测（挂在哪个 Step 的验证）/ 回退**。
3. `STATUS.md` 改 `In Progress`，进入第 6 段实施。**不许写 `Blocked`，不许"再问一轮"。**
4. 缺「检测」或「回退」的项不许开工，就地补齐。

唯一例外：验收无法判定 / 需求自相矛盾 / 关键前置不存在 → 一次性输出裁定请求（待定项 + 2–3 个候选 + 各自后果），状态留 `Blocked` 并停。

### 5.3 【硬停机】无独立审核能力时

**不许自审**：同一会话里"顺手再审一遍"等于没审，它只会确认自己已有的推理。

此时把 `STATUS.md` 改为 `Next Action: 等待第 1 轮审核`，状态留在 `Planned`，输出下面的移交块并**结束本次执行**：

```text
移交审核
计划：tasks/plans/<topic>/<plan-id>/
规则：spec/plans/plan-audit-guide.md
轮次：<N> / 3（第 3 轮写"最后一轮"）
要求：结论只能是 pass / pass-with-changes / reject；按规范第 6 章模板写 audits/NN-audit.md
完成后：回到 <本文件名> 继续第 5 段（响应 → 收口 → 开工）
```

### 5.4 审核期间的禁止事项

- 不改代码、不建迁移、不动依赖——审核只改计划文档。
- 不改审核报告本身；对某条意见有异议走 `reject` 并给证据，不删条目。
- 不为了让结论变 `pass` 而放宽验收标准；验收标准被改松了，审核就白做了。

<!-- /common:audit -->

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
audit：<L1|L2> · <N> 轮 · 最终结论 <pass|pass-with-changes>
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
