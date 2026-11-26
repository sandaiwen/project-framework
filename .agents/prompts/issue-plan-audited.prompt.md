---
description: 接一个问题描述，确认与定位根因后写修复计划，由独立 agent 审核最多 3 轮；第 3 轮后按未关闭项转风险敞口再执行到"待提交"
version: 2.0.0
last_updated: 2026-11-26
kind: issue / audited
inputs:
  - "问题：<一句话现象>"
  - "预期依据（可选）：.design/docs/<module>/<file>.md#<需求标识>"
  - "环境（可选）：本地|staging|production / commit"
---

# 问题修复 · 分析根因 + 写计划 + 审核后执行

输入是**一个问题**，可以是 bug、功能缺陷或线上事故。产出是一份 `analysis.md`、一份**经最多 3 轮审核且未关闭项已转风险敞口**的修复计划、按计划改完的代码（含红→绿证据与回归登记）、以及停在"待提交"的提交候选。

与 `issue-plan.prompt.md` 的差别不止多一段，共四处：§2 多"审核能力"检查、§4.2 定档改为按 0.2 判（普通缺陷默认 `L1`、事故 `L2`）、§4.3 多建 `audits/` 且 `Next Action` 写"等待第 1 轮审核"、§5 审核循环。**事故（`incident`）只能走本入口**，因为它按规范属于 `L2`，不审入口在 §2 就会拒收。

<!-- 公共段：§0 与 §6 与本目录另三份逐字一致（标记 common:exec / common:wrapup）；§5 与 feature-plan-audited 逐字一致（标记 common:audit）。改一处必须同组同改，版本一起升。 -->

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
问题：<一句话现象>
预期依据（可选）：<设计文档路径>#<需求标识>
环境（可选）：<本地|staging|production> / <commit 或版本号>
```

- **只有「问题」一项也能跑。** 缺预期依据时，按以下顺序推定"预期是什么"：
  1. 同类接口的现有契约（OpenAPI、请求/响应类型定义、既有测试断言）；
  2. 相邻功能的实现一致性（同模块其它接口怎么处理同类输入）；
  3. `.design/` 里同名模块的章节。
- 推定结果必须写进 `analysis.md` 的「结论 - 判定依据」，并在最终输出单列"预期来源：xxx"。找不到任何依据 → 只能是 `needs-info`。
- 现象要能被"期望 vs 实际"两句话说清。说不清 → **【硬停机】** 只问一句："期望是什么、实际是什么"。

## 2. 前置检查（任一不过即停）

| # | 检查 | 方法 | 不过时 |
| --- | --- | --- | --- |
| 1 | 设计仓状态（有预期依据时才需要） | `.design/` 存在，`git -C .design rev-parse HEAD` 等于 `design.lock` 的 `commit` | **【硬停机】**报告两个 SHA；**不要自行升级** |
| 2 | 无重复记录 | 扫 `tasks/plans/*/*/analysis.md` 与 `docs/regression/registry.yaml`，同现象或同编号没有已存在的条目 | **【硬停机】**报告目录与结论，等确认续做还是新开（`not-a-bug` 的不要重开） |
| 3 | 落盘门槛 | 缺陷修复一律建目录并走完整流程；本入口**不保留"直接改"旁路** | **【硬停机】**命中文案例外 → 改走 `issue-plan.prompt.md` 并说明；在此直接改会跳过 `analysis.md`、计划与审核 |
| 4 | 可复现前提 | 有没有能跑起来的运行环境 | 不能起服务 → 允许静态定位（读代码 + 日志 + 数据），`analysis.md` 标「未运行验证」，验收标准写"环境就绪后首次执行必须红→绿"并进「风险」；**静态证据凑不齐第 3 章三条判据就只能是 `needs-info`** |
| 5 | 审核能力 | 当前环境能否起独立会话或子 agent | 不能 → 计划写完后按第 5 段**硬停机**移交，不要自审 |

- 仓库当前可能只有规范、没有应用代码。此时若问题指向尚不存在的实现，结论应为 `design-gap` 或 `not-a-bug`，不是 `confirmed`。

## 3. 确认与根因（`spec/workflow/bugfix-workflow-guide.md` 第 2 章第 0～2 步）

### 3.1 登记

| 项 | 规则 |
| --- | --- |
| `Issue` | `BUG-YYYYMMDD-NN`。`NN` = 扫 `tasks/plans/*/*/analysis.md` 与 `docs/regression/registry.yaml` 中**当日**最大序号 + 1（两位补零），扫描不到从 `01` 起。编号一旦写入不再改 |
| `topic` | 受影响的模块（`orders`、`auth`、`billing`），**不用** `bug`、`fix`、`issues` |
| `plan-id` | `YYYYMMDD-fix-<slug>-NN`；线上事故用 `hotfix-` |
| 目录 | `tasks/plans/<topic>/<plan-id>/`，先只建 `analysis.md`、`STATUS.md`、`artifacts/` |

### 3.2 写 `analysis.md`

模板照 `spec/workflow/bugfix-workflow-guide.md` 第 3 章，**一节不许省**。至少做到：

- 「现象」：期望 / 实际 / 复现步骤 / 复现率 / 证据（日志片段、trace id、请求响应、截图路径）。
- 「影响面」：用户影响、**是否已产生错误数据**（要不要单独修数据）、范围（单租户/全量、单接口/全链路）。
- 「根因」：直接原因 → 根本原因，**每条都带证据**（`文件:行号`、SQL、提交 SHA、日志行）。
- 「为何现有测试没抓到」：必填。写"没覆盖到"不算答案，要说清哪一层本该覆盖、为什么漏了。

### 3.3 根因的三条判据（缺一条不许往下走）

1. 能指到具体文件与行号（或具体配置项、具体数据行）。
2. 能解释复现条件：为什么这个条件下必现、那个条件下不出现。
3. 能解释为何现有测试没抓到。

缺任何一条 → `STATUS` 停在 `Planned`，`Next Action` 写还缺哪条证据，输出说明后停。**禁止带着猜测写修复计划**：猜出来的修复会同时引入新缺陷。

### 3.4 结论四选一

| 结论 | 之后做什么 |
| --- | --- |
| `confirmed` | 进入第 4 段 |
| `not-a-bug` | **不建 `plan.md`**。`STATUS` 转 `Archived`，`analysis.md` 写清"为什么不是缺陷 + 若要改应走哪个入口"，输出后结束 |
| `design-gap` | **不建 `plan.md`**。`STATUS` 转 `Blocked`（在等设计仓改，不是归档），写清设计哪一条错了、建议在设计仓提什么 issue；解除条件是设计仓合入且 `design.lock` 更新。输出后结束（**不在项目仓打补丁**） |
| `needs-info` | `STATUS` 转 `Blocked`，列出缺什么信息、找谁要，输出后结束 |

- 偶发问题（复现率 < 100%）且无日志证据 → 只能 `needs-info`，不许猜根因。
- 性能问题：判定"当前实现没达到既定指标"→ `bugfix`；判定"指标本身要改"→ 输出建议走 `feature` 入口，不在本入口改需求。

## 4. 修复计划与落盘

### 4.1 与功能计划的四处差异

模板同 `spec/plans/plan-writing-guide.md` 第 2 章，但四项必须不同：

| 项 | 要求 |
| --- | --- |
| 验收标准 | 写成"复现用例由失败转通过" + "同模块回归通过"。不接受"问题不再出现"这类无法判定的表述 |
| 范围-改 | **必须包含**复现用例文件与 `docs/regression/registry.yaml` |
| 回滚 | 若已产生错误数据，写清数据怎么处理（脚本、判定条件、执行顺序） |
| Metadata | `Type: bugfix`（事故 `incident`）、`Issue: BUG-...`、`Source` 指预期依据所在章节（无依据写 `none`） |

### 4.2 定档（事故一律 `L2`）

完整判定表见 `spec/plans/plan-audit-guide.md` 0.2。本入口必须写出档位：

```md
- Audit: <L1|L2>
- Audit Trigger: <命中的具体条目，不写"风险较高">
```

- `Type: incident`（线上事故、回滚后的补修）→ **`L2`**，审核者必须不同 agent 或不同模型（轮次上限同为 3）。
- 命中 0.2 任一 `L2` 项 → `L2`。
- 其余情况按 `spec/workflow/bugfix-workflow-guide.md` 第 5 章：**普通缺陷默认 `L1`**，至少换一个会话（轮次上限同为 3）。不要因为"看起来简单"降到 `none`——降档只有不审入口才允许，且要满足它的低风险条件。
- 范围扩大后重新判定，**只升不降**；升档按 `plan-audit-guide.md` 0.3 对增量补审。

### 4.3 落盘

```text
tasks/plans/<topic>/<plan-id>/
├── analysis.md       # 第 3 段已写
├── plan.md
├── STATUS.md
├── audits/           # 本入口要建（第 5 段写入）
└── artifacts/        # red.log / green.log / reverse-verify.log 放这里
```

- `plan.md` 的 `Metadata` 十一项写全，模板照 `spec/plans/plan-writing-guide.md` 第 2 章。
- 「步骤」第 1 步固定是"写失败用例并留红"，最后一步固定是"反向验证 + 回归登记"，中间步骤按修复动作拆。
- `STATUS.md` 三行，`Current Status: Planned`，`Next Action` 写 `等待第 1 轮审核`。
- 写完执行 `python scripts/tasks-index.py`。
- 写完 `plan.md` 做一次**覆盖核对**：需求/问题里的每条要求都能落到某条验收标准或某个 Step；落不上的补进「遗留问题」并在「决策记录」记一行。覆盖不上就不许开工。
- 「范围-改」出现新建路径时，先读 `spec/module/module-guide.md` 第 1 章或 `spec/frontend/frontend-guide.md` 第 1 章定目录，**列到文件级**，不要现编结构。
- **此时不要开工**，进入第 5 段。

### 4.4 实施顺序（审核通过后照此执行，不许调换）

1. **红**：写复现用例，跑到失败，输出存 `artifacts/red.log`。用例**没失败**说明它抓不住这个缺陷 → 重写用例。重写 2 次仍不红 → 结论降为 `needs-info`（这条"缺陷"可能并不成立），停止实施。
2. **绿**：改代码到用例通过，输出存 `artifacts/green.log`。
3. **反向验证**：`git stash push -u -- <本次新增或修改的源码与用例文件>`（`-u` 才能带走未跟踪的新文件；漏了它，新建用例会留在原地导致"验证通过"是假的）→ 重跑用例**必须重新失败** → `git stash pop`，输出存 `artifacts/reverse-verify.log`，并把结论写入「决策记录」：`反向验证：stash 修复后用例重新失败（YYYY-MM-DD）`。
4. **分层**：按影响面选层（公共层 / 权限 / 金额 → 相关单测 + 接口测试 + E2E + 拒绝路径断言），输出全部进 `artifacts/`。
5. **登记**：`docs/regression/registry.yaml` 加一条，按文件顶部注释逐字段填：`id`（与 `Issue` 完全一致）、`title`、`severity`、`source`、`found_at`、`root_cause`（与 `analysis.md` 的「根本原因」一字对齐）、`cases`、`reverse_verified: true`、`reverse_verified_at`、`status`。**首次登记是把文件末尾的 `[]` 整体替换成这条记录**（保留顶部注释），不是往 `[]` 后面追加。

- 一次没修好：扩范围要在「决策记录」写原因。
- **同一缺陷第二次仍未修好** → 第三次动手前必须找人复核 `analysis.md`（按 `spec/plans/plan-audit-guide.md` 审一遍）；连续失败通常说明根因错了，不是修得不够。
- `incident` 的提交与发布走 `spec/ci_cd/ci-cd-guide.md` 的热修链路，测试与回归登记不因紧急而降。
- 审核期间**不改代码**：本节 1～5 步全部发生在第 5 段审核闭合之后，之前只允许改计划文档。

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
issue：BUG-<...> · severity：<critical|high|medium|low>
audit：<L1|L2> · <N> 轮 · 最终结论 <pass|pass-with-changes>
根因：<一句话，带 文件:行号>
红→绿：red.log 失败 <N> 条 → green.log 通过 <N> 条 · 反向验证 reverse-verify.log 已确认重新失败
回归登记：docs/regression/registry.yaml 已加 <id>，reverse_verified: true · reverse_verified_at: <日期>
改动：<N> 个文件，+<增> −<删>
未执行项：<没有就写"无">
推定项：<第 0 段要求列出，没有就写"无">
待用提交信息：
fix(<plan-id>): <现象消失的祈使句>

<一句话根因，与 analysis.md 的「根本原因」一致>

Refs: design@<sha>#<需求标识>（无则写 none）
Plan: tasks/plans/<topic>/<plan-id>/
Issue: BUG-<...>
Test: <命令> — red.log 失败 → green.log 通过
```

**【硬停机】不要执行 `git commit`、`git push`、开 PR。** 等用户回"提交"再按 `spec/git/commit-guide.md` 第 4 章执行；`Completed` 只在合入后改。
