---
description: 接一个问题描述，先确认与定位根因，再写修复计划并执行到"待提交"（不审核）
version: 1.0.0
last_updated: 2026-11-15
kind: issue / no-audit
inputs:
  - "问题：<一句话现象>"
  - "预期依据（可选）：.design/docs/<module>/<file>.md#<需求标识>"
  - "环境（可选）：本地|staging|production / commit"
---

# 问题修复 · 分析根因 + 写计划并直接执行

输入是**一个问题**，可以是 bug、功能缺陷或线上事故。产出是一份 `analysis.md`、一份修复计划、按计划改完的代码（含红→绿证据与回归登记）、以及停在"待提交"的提交候选。

与 `feature-plan.prompt.md` 的差别：**先证明问题存在并找到根因，才允许写计划**；验收标准是"复现用例由失败转通过"。

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
| 3 | 落盘门槛 | 缺陷修复一律建目录；唯一例外是纯文案/注释且无行为变化 | **【硬停机】**命中文案例外 → 直接改并在输出写清现象与根因；其余不满足即停 |
| 4 | 可复现前提 | 有没有能跑起来的运行环境 | 不能起服务 → 允许静态定位（读代码 + 日志 + 数据），`analysis.md` 标「未运行验证」，验收标准写"环境就绪后首次执行必须红→绿"并进「风险」；**静态证据凑不齐第 3 章三条判据就只能是 `needs-info`** |
| 5 | 风险筛 | 按 `spec/plans/plan-audit-guide.md` 0.2 判；`Type: incident` 或命中任一 `L2` 项 | **【硬停机】**本入口只接低风险缺陷：列出命中的条目，要求改用 `issue-plan-audited.prompt.md`，不要在此降档 |

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
| 验收标准 | 写成"复现用例由失败转通过" + "同模块回归通过"，并点名用例路径与节点名。不接受"问题不再出现"这类无法判定的表述 |
| 范围-改 | **必须包含**复现用例文件与 `docs/regression/registry.yaml`；漏这两项就是范围不全 |
| 回滚 | 若已产生错误数据，写清数据怎么处理（脚本、判定条件、执行顺序） |
| Metadata | `Type: bugfix`、`Issue: BUG-...`、`Source` 指预期依据所在章节（无依据写 `none`） |

- 「步骤」第 1 步固定是"写失败用例并留红"，最后一步固定是"反向验证 + 回归登记"。

### 4.2 定档（本入口的例外边界）

`Audit` 与 `Audit Trigger` 都写 `none`。这是对 `spec/workflow/bugfix-workflow-guide.md` 第 5 章"普通缺陷默认 `L1`"的**有意例外**，前提是 §2 第 5 行风险筛已通过（单模块、已有测试覆盖、不命中任何 `L2` 项）。

- MUST 在「决策记录」写一句「按规范默认应为 `L1`，因 <单模块 / 已有测试覆盖 / 无 L2 项> 未审」。不写这句等于违规降档。
- MUST NOT 把 `incident` 放进本入口：事故一律 `L2`，走 `issue-plan-audited.prompt.md`。
- MUST NOT 在 `Audit Trigger` 写中文说明——它的取值域是 `none` 或具体命中条目。

### 4.3 落盘

```text
tasks/plans/<topic>/<plan-id>/
├── analysis.md       # 第 3 段已写
├── plan.md           # 本节写
├── STATUS.md         # 三行，Current Status: Planned
└── artifacts/        # red.log / green.log / reverse-verify.log 放这里
```

- `plan.md` 的 `Metadata` 十一项写全（`Issue: BUG-...`），模板照 `spec/plans/plan-writing-guide.md` 第 2 章。
- `STATUS.md` 三行，`Next Action` 指向第 1 步（写失败用例）；第 3 段已建过就先改内容，不要重建。
- 写完执行 `python scripts/tasks-index.py`。
- **不要创建 `audits/`**（本入口不审核）。
- 落盘完成后才进入 4.4；顺序颠倒会出现"代码改了但计划不存在"。
- 写完 `plan.md` 做一次**覆盖核对**：需求/问题里的每条要求都能落到某条验收标准或某个 Step；落不上的补进「遗留问题」并在「决策记录」记一行。覆盖不上就不许开工。
- 「范围-改」出现新建路径时，先读 `spec/module/module-guide.md` 第 1 章或 `spec/frontend/frontend-guide.md` 第 1 章定目录，**列到文件级**，不要现编结构。

### 4.4 实施顺序（写进「步骤」，不许调换）

1. **红**：写复现用例，跑到失败，输出存 `artifacts/red.log`。用例**没失败**说明它抓不住这个缺陷 → 重写用例。重写 2 次仍不红 → 结论降为 `needs-info`（这条"缺陷"可能并不成立），停止实施。
2. **绿**：改代码到用例通过，输出存 `artifacts/green.log`。
3. **反向验证**：`git stash push -u -- <本次新增或修改的源码与用例文件>`（`-u` 才能带走未跟踪的新文件；漏了它，新建用例会留在原地导致"验证通过"是假的）→ 重跑用例**必须重新失败** → `git stash pop`，输出存 `artifacts/reverse-verify.log`，并把结论写入「决策记录」：`反向验证：stash 修复后用例重新失败（YYYY-MM-DD）`。
4. **分层**：按影响面选层（公共层 / 权限 / 金额 → 相关单测 + 接口测试 + E2E + 拒绝路径断言），输出全部进 `artifacts/`。
5. **登记**：`docs/regression/registry.yaml` 加一条，按文件顶部注释逐字段填：`id`（与 `Issue` 完全一致）、`title`、`severity`、`source`、`found_at`、`root_cause`（与 `analysis.md` 的「根本原因」一字对齐）、`cases`、`reverse_verified: true`、`reverse_verified_at`、`status`。**首次登记是把文件末尾的 `[]` 整体替换成这条记录**（保留顶部注释），不是往 `[]` 后面追加。

- 一次没修好：扩范围要在「决策记录」写原因。
- **同一缺陷第二次仍未修好** → 第三次动手前必须找人复核 `analysis.md`（按 `spec/plans/plan-audit-guide.md` 审一遍）；连续失败通常说明根因错了，不是修得不够。
- `incident` 的提交与发布走 `spec/ci_cd/ci-cd-guide.md` 的热修链路，测试与回归登记不因紧急而降。

## 5. 审核（本入口不启用）

本入口以"低风险、根因清楚、改法唯一"为前提（§2 第 5 行风险筛已通过）：不创建 `audits/`、不另起会话，`Metadata.Audit` 与 `Audit Trigger` 都写 `none`。

- 依据：`spec/workflow/bugfix-workflow-guide.md` 第 5 章的例外条款 + `spec/plans/plan-audit-guide.md` 0.2 档位表。`incident` 与任何 `L2` 命中项在 §2 就被拒收，走不到这里。
- 若执行中发现根因被推翻、或范围扩到跨模块（命中 `L2`），按 `plan-audit-guide.md` 0.3 **升档即补审**：对增量补至少一轮独立审核，`Audit` 与 `audits/` 同时更新；起不了独立会话则 `STATUS` 转 `Blocked`，移交 `issue-plan-audited.prompt.md`。
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
issue：BUG-<...> · severity：<critical|high|medium|low>
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
