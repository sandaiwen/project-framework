---
version: 8.0.0
last_updated: 2026-11-15
---

# 开发流程规范（Dev Workflow Guide）

本文件规定**一个设计任务如何走到一次提交**：三层各自的职责、三个接口的契约、最小实施单元的闭环条件、状态流转与设计变更回流。

它是框架的**主流程**，其余规范是这条流程上的约束：`spec/plans/plan-writing-guide.md` 定计划文件怎么写，`spec/testing/` 定怎么验证，`spec/ci_cd/` 定怎么进流水线。本文只管"流转与边界"。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

---

## 0. 一句话

> **设计仓只回答"要什么"，`spec/` 只回答"必须怎么做"，计划单元回答"这一次具体怎么做、做完的证据在哪"。**

三层之间只有三个接口，把这三个接口写死，流程就不会乱。

```text
设计仓（独立 git 仓库）          项目仓
  PRD ──拆分──> 任务卡  ──只读克隆 + design.lock 锁 SHA──>  spec/ 约束
                                                             │
                                              任务卡 1:1 映射 ▼
                                        tasks/plans/<topic>/<plan-id>/
                                          plan.md · STATUS.md · artifacts/
                                                             │
                                                    一单元一提交 ▼
                                                     commit / PR
```

---

## 1. 三层与职责

| 层 | 在哪 | 只负责 | 不负责 | 权威来源 |
| --- | --- | --- | --- | --- |
| 意图层 | 设计仓（独立仓库） | 需求（PRD）、任务拆分、行为契约、验收标准 | 技术方案、文件路径、实现步骤 | 设计仓自身 |
| 约束层 | 项目仓 `spec/` | 技术选型、目录与写法、测试与迁移门槛、依赖与流水线 | 具体某个任务做什么 | `spec/README.md` |
| 执行层 | 项目仓 `tasks/plans/` | 一次实施的目标、步骤、验证、证据 | 需求定义、跨任务规划 | `spec/plans/plan-writing-guide.md` |

三条职责边界：

- MUST NOT 让设计仓写实现细节（文件路径、类名、SQL）。设计仓看不到代码现状，写出来的方案必然过期。
- MUST NOT 让计划单元重新定义需求。`plan.md` 的"目标/验收标准"必须与任务卡一致，措辞可以本地化，判定条件不能变。
- MUST NOT 让 `spec/` 记录具体任务。规范只写"这类事必须怎么做"，一旦出现"某功能要改动 A 文件"，说明放错了层。

### 1.4 两类入口：功能任务与缺陷修复

同一条流水线，两种进入方式。差别只在开工前那一段，**目录、状态机、审核、提交完全共用**：

| 入口 | `Metadata.Type` | `plan-id` 前缀 | 开工前额外产物 | 验收标准 |
| --- | --- | --- | --- | --- |
| 设计任务卡（功能、改造） | `feature` / `refactor` | 无 | 无 | 功能可用、验收标准逐条通过 |
| 缺陷 / 线上事故 | `bugfix` / `incident` | `fix-` / `hotfix-` | `analysis.md`（现象、根因、结论） | **复现用例由失败转通过** + 同模块回归 |

- MUST NOT 为缺陷另建 `tasks/bugs/`、`tasks/issues/` 目录，也不另立状态机：来源已经由 `Metadata.Type` / `Issue` 承载，目录再分一次等于同一件事存两遍。
- MUST 缺陷/事故类走 `spec/workflow/bugfix-workflow-guide.md` 的七步；功能类走本文第 2～5 章。
- 判据："预期"是设计定的还是代码没做到？前者走功能入口，后者走缺陷入口；设计本身错 → 结论 `design-gap`，计划转 `Blocked`，回流设计仓（解除条件：设计合入且 `design.lock` 更新）。

---

## 2. 三个接口（强制）

### 2.1 设计仓 → 项目仓：只读 + 版本锁定

- MUST 设计文档通过 `git clone` 拉到项目本地 `.design/`，并加入 `.gitignore`；**不提交进项目仓**。
- MUST 用仓库根的 `design.lock` 记录当前依据的设计版本：

```yaml
# design.lock
repo: git@example.com:team/design.git
commit: 9f2c1ab3d4e5f60718293a4b5c6d7e8f90123456
ref: main
updated_at: 2026-11-15 16:00
```

- MUST 计划开工前核对 `design.lock` 与 `.design` 的实际 HEAD 一致；不一致先同步再开工。
- MUST 项目仓对 `.design/` 只读，禁止修改、禁止提交。发现设计有问题 → 在设计仓提 issue/PR，本地计划转 `Blocked` 并写明阻塞原因。
- MUST NOT 让 CI 或构建依赖设计仓。`design.lock` 只服务人与计划，构建产物不得读取 `.design/`。
  理由：否则上游改个标点就会让无关 PR 变红。

同步命令（放 `scripts/design-sync.sh` 或等价封装，不要每次手敲）：

```bash
# 首次
git clone "$(sed -n 's/^repo: //p' design.lock)" .design

# 之后：切到 lock 记录的 commit
git -C .design fetch --all --tags
git -C .design checkout "$(sed -n 's/^commit: //p' design.lock)"

# 需要升级到最新时：改 commit 字段，再同步，并在计划里记录升级原因
```

### 2.2 任务卡 → 计划单元：严格 1:1

一张任务卡对应一个计划目录，不允许合并、不允许拆分。

| 任务卡字段 | 落到 plan 的哪里 | 规则 |
| --- | --- | --- |
| 卡 id（如 `TASK-01`） | `<plan-id>` 的后缀 + `Metadata.Source` | 用于反查；同一张卡不得对应两个计划 |
| 目标 | `plan.md` 的「目标」 | 一句话结果，不改写含义 |
| 验收标准 | `plan.md` 的「验收标准」 | 逐条照搬判定条件；可润色措辞，不得放宽 |
| 涉及模块 / 范围 | `plan.md` 的「范围」 | 补上"不改"的部分（卡里通常没有） |
| 依赖的其他卡 | `plan.md` 的「前置条件」 | 前置未完成则本计划停在 `Planned` |
| 设计 revision | `Metadata.Revision` | 设计变更回流时用来比对（见第 7 节） |

`plan.md` 的 `Metadata` 因此至少包含：

```md
- Plan ID: 20261115-user-login-01
- Source: design@9f2c1ab#TASK-01
- Revision: 3
```

- MUST 一张卡一个计划。要"顺手把下一张卡也做了"，就新开一个计划，用「前置条件」串起来。
- MUST `Source` 里的 SHA 与 `design.lock` 一致。
- MUST NOT 计划做完后回填 `Source`；开工时就写。

上游给的可能是**任务卡**，也可能只有 PRD 里一条需求（当前设计仓就是后者）。抽取按三级降级，落盘时在「决策记录」写明用了哪一级：

| 文档形态 | 抽取方式 | `Metadata.Source` |
| --- | --- | --- |
| 已成任务卡（有 id 与验收标准） | 直接引用，验收逐条照搬 | `design@<sha>#<卡 id>` |
| 有需求条目/章节，无卡 | 从正文抽目标、验收、范围、前置条件 | `design@<sha>#<需求标识>` |
| 只有散落描述 | 停下要求指定章节，不自行编需求 | — |

- MUST 抽不出可判定条件的验收条目时保留原文并标"待确认判定方式"，**不得自行编一个可判定的近似条件**——那会把需求变更伪装成实现任务。
- MUST 一段需求包含多件可独立交付的事时，只做第一件，其余进「遗留问题」并建议拆成多个需求；不要一张卡做多件事。

### 2.3 计划单元 → 交付：一单元一提交

- MUST 一个计划对应**一次提交**（或一个 PR）。多计划混在一次提交里，回滚就无法按单元进行。
- MUST 提交信息格式：

```text
<type>(<plan-id>): <祈使句结果>

Refs: design@<sha>#<task-id>
Plan: tasks/plans/<topic>/<plan-id>/
Test: <实际执行的命令> — <结果摘要>
```

`type` 取 `spec/ci_cd/ci-cd-guide.md` 1.2 的合法值（`feat` / `fix` / `refactor` / `test` / `docs` / `chore` …），`scope` 固定为 `plan-id`。不另造 `plan(...)` 类型——它不是合法 `type`，会让 commitlint 一类工具失效。完整格式与反例见 `spec/git/commit-guide.md` 第 3 章。

- MUST 提交前把 `STATUS.md` 改为 `Verified`；合入或交付后改为 `Completed`（`spec/plans/plan-writing-guide.md` 3.2）。
- SHOULD 计划目录与代码改动在同一个提交里，不分开两次提交（否则"计划说做了"和"代码做了没"会脱节）。
- 做过审核的计划，`audits/` 与计划同目录、随同一次提交入库。审核**不是流程阶段**，是写计划时的一个可选动作，见 `spec/plans/plan-audit-guide.md`。

---

## 3. 最小实施单元

一个计划目录就是最小实施单元，构成固定：

```text
tasks/plans/<topic>/<plan-id>/
  plan.md        # 唯一事实源：目标、验收、范围、步骤、决策、遗留、回滚
  STATUS.md      # 三行：当前状态、下一步动作、更新时间
  artifacts/     # 命令原始输出、覆盖率、E2E 报告、回归报告
```

- 落盘门槛（什么任务必须建计划）见 `spec/plans/plan-writing-guide.md` 第 0 章，本文不复述。
- 目录命名、模板字段、更新规则同上，本文只补充第 2、4 节的跨仓库契约与闭环条件。
- MUST NOT 在计划目录里新增碎片文档（`step1-summary.md` 之类）；例外情形见 `plan-writing-guide.md` 第 5 章。

---

## 4. 单元内部闭环

### 4.1 四步循环

```text
实施 → 记录 → 测试 ──失败──> 回改（回到实施）
                  └─通过──> 验收
```

- "回改"**不是状态**，是 `In Progress` 内部的循环。重试多少次都不产生新状态。
- 回改次数不单独记账，但每轮的关键决策（为什么失败、改了做法）写进 `plan.md` 的「决策记录」。

### 4.2 "记录"指什么

这里的记录是**执行记录**，不是应用运行日志，两者不能混：

| 类型 | 内容 | 落在哪 |
| --- | --- | --- |
| 执行记录 | 跑了什么命令、输出是什么、结论是什么 | `artifacts/`（原始输出）+ `plan.md` 的「最终验证」「决策记录」 |
| 应用日志 | 服务运行时的 log（级别、字段、脱敏） | 按 `spec/logging/logging-guidelines.md` 写进代码 |

- MUST NOT 把应用日志规范写进计划；也 MUST NOT 把执行输出贴进 `plan.md` 正文（放 `artifacts/`）。

### 4.3 闭环的五条判据

单元完成不以"代码写完"为准，以五条证据齐备为准：

| # | 闭合项 | 判定方式 |
| --- | --- | --- |
| 1 | 范围闭合 | `plan.md` 的「改」清单 = 实际 diff；有偏离已在「决策记录」说明 |
| 2 | 验收闭合 | 每条验收标准对应一条命令 + 实际输出，存 `artifacts/` |
| 3 | 回归闭合 | 改动相关测试 + 该模块回归通过；修缺陷有反向验证记录（`spec/testing/regression-testing-guide.md` 第 3 节） |
| 4 | 记录闭合 | 各 Step 状态为完成、`最终验证` 逐条对应、`遗留/回滚` 已写、STATUS 已到 `Verified` |
| 5 | 依赖闭合 | 新增依赖进 `docs/deps/decisions.md`；新增迁移已跑升降级；契约基线无未提交变化 |

- MUST 五条全部满足才能把 `STATUS.md` 改为 `Verified`。
- MUST NOT 用"测试跑过了"代替第 2 条；要说清"跑的是哪条验收标准"。
- MUST 缺陷/事故类的第 2 条改按"复现用例由失败转通过"判定：`artifacts/` 里要有 `red.log`、`green.log` 与反向验证记录（`spec/workflow/bugfix-workflow-guide.md` 第 6 章）。

---

## 5. 提交（最后一环）

闭环五条满足之后、状态转 `Completed` 之前，动作只有这一段。**细则全部在 `spec/git/commit-guide.md`，本节只规定顺序与出口条件。**

| 步 | 动作 | 出口条件 |
| --- | --- | --- |
| 1 | 自检四件事：范围=计划「改」清单、验收证据在 `artifacts/`、测试真跑过、无敏感文件与生成物 | 四项都能拿出证据 |
| 2 | 显式路径暂存，`git diff --cached` 完整看一遍 | 暂存内容与计划一致，没有意外文件 |
| 3 | 一次提交（一个计划一次；计划目录与代码同一提交）；提交前跑 `python scripts/tasks-index.py` 更新 `tasks/INDEX.md` | `git log -1 --stat` 与预期一致；索引随提交一起更新 |
| 4 | 推送、开 PR（描述三块：改了什么 / 怎么验证 / 怎么回滚） | CI 出结果 |
| 5 | CI 绿 + 合入，`STATUS.md` 转 `Completed` | 提交可独立 `git revert` |

- MUST 提交前把 `STATUS.md` 改为 `Verified`；**合入后**才改 `Completed`。先改 `Completed` 再提交，等于用计划冒充事实。
- MUST 一个计划一次提交；计划目录（`plan.md`、`STATUS.md`、`audits/`、`artifacts/`）与代码同一次提交。
- MUST 提交后立刻看 CI；红了立刻修，不等评审。
- MUST 这条提交能独立 `git revert`。做不到说明单元切错了，在「决策记录」记一笔。
- MUST NOT 用 `git add -A` / `git commit -a` 暂存——会把无关改动与生成物带进来，而 `git diff --cached` 往往看不出来。
- MUST NOT 走 `--no-verify`。hook 失败一律改根因（`spec/git/commit-guide.md` 第 6 章）。

---

## 6. 状态与流转

状态定义与合法转移表以 `spec/plans/plan-writing-guide.md` 3.2 / 3.3 为准。本文补充**进入条件**，避免状态变成自评：

| 状态 | 进入条件（可判定） |
| --- | --- |
| `Planned` | 目录三件套已建，`plan.md` 必填字段齐全，`Source` 已写 |
| `In Progress` | 已开工；`design.lock` 与 `.design` 的 HEAD 一致 |
| `Blocked` | 外部原因停滞；`plan.md` 写明阻塞原因与解除条件 |
| `Verified` | 第 4.3 节五条全部满足 |
| `Completed` | 提交已合入，或成果已交付 |
| `Archived` | 废弃或被其他计划替代；`plan.md` 写明原因与替代计划 id |

- MUST NOT 从 `Planned` 直接跳到 `Verified` / `Completed`。
- MUST `Blocked` 要么写清解除条件，要么在两周内转 `Archived`；长期挂着等于放弃。
- MUST `Verified` → `In Progress` 的回退（验证后发现缺陷）在「决策记录」留一行原因。

---

## 7. 设计变更回流

设计仓会继续演进，已完成的计划不能悄悄与新设计脱节。

- MUST 任务卡带 `revision`（或等效版本号），计划在 `Metadata.Revision` 记录开工时依据的值。
- MUST `design.lock` 升版时产出一份"受影响计划清单"：

```bash
# 找出引用了旧 revision 的活跃计划
grep -rl "Source: design@$(git -C .design rev-parse HEAD)" tasks/plans/*/*/plan.md
grep -rl "^Revision:" tasks/plans/*/*/plan.md | xargs grep -L "<新 revision>"
```

- MUST 按下面三档处理受影响计划：

| 情况 | 处理 |
| --- | --- |
| 验收标准未变，仅描述调整 | 更新计划的 `Revision` 与引用文字，不改代码 |
| 验收标准新增/收紧 | 新建一个计划承接增量；原计划不重开 |
| 行为契约变更（旧行为作废） | 新计划 + 一条回归条目（`source: behavior-change`） |

- MUST NOT 直接改已 `Completed` 计划的验收标准来"对齐新设计"。已完成的事实不允许被追溯修改；用新计划表达变化。

---

## 8. 并行与依赖

- MUST 计划之间只通过「前置条件」表达依赖，不通过时间顺序或口头约定。
- MUST 一张卡未完成时，不开始依赖它的卡；需要并行时先拆出不依赖的部分。
- SHOULD 同一主题（`<topic>`）下同时进行的计划不超过 2 个；超过说明拆分粒度太粗。
- MUST NOT 两个计划改同一批文件而不在「范围」里写明冲突面；出现冲突时先合并成一个计划。

---

## 9. 禁止事项

- MUST NOT 跳过计划直接改代码（门槛判定见 `plan-writing-guide.md` 第 0 章）。
- MUST NOT 在项目仓修改 `.design/` 下的设计文档。
- MUST NOT 提交设计文档到项目仓，或让构建/CI 读取设计仓。
- MUST NOT 一张卡拆成多个计划，或多个计划合并成一次提交。
- MUST NOT 事后补计划（计划要能指导执行，不是执行后的说明书）。
- MUST NOT 用 `STATUS.md` 写进展长文；它只有三行。
- MUST NOT 把应用日志规范与执行记录混为一谈。
- MUST NOT 完成一个单元时缺少第 4.3 节任一条证据。

---

## 10. 检查清单

**接任务时（开工前）**

- [ ] 已读任务卡，验收标准可判定（不是"功能正常"）。
- [ ] `design.lock` 与 `.design` 的 HEAD 一致，`Source` 的 SHA 已记录。
- [ ] 这张卡没有对应的进行中计划（1:1 未被破坏）。
- [ ] 落盘门槛判定过：该建计划已建，`plan.md` 必填字段齐全。
- [ ] `Metadata.Audit` 已写（`none` / `L1` / `L2`）；做过审核的，`audits/` 内报告与响应成对。

**执行中**

- [ ] 每完成一步就更新 Step 状态与 `Next Action`。
- [ ] 偏离计划的动作先写进「决策记录」。
- [ ] 测试失败的回改只在 `In Progress` 内循环，不新增状态。

**提交前**

- [ ] 第 4.3 节五条闭合全部满足。
- [ ] `STATUS.md` 为 `Verified`，三行且 `Next Action` 具体。
- [ ] 提交信息为 `<type>(<plan-id>): ...`，带 `Refs:` / `Plan:` / `Test:` 三个 trailer（`spec/git/commit-guide.md` 第 3 章）。
- [ ] 计划目录与代码改动在同一次提交里。
- [ ] `git diff --cached` 完整看过，无敏感文件、生成物、无关改动（`spec/git/commit-guide.md` 第 2 章）。
- [ ] `python scripts/tasks-index.py --check` 通过（`tasks/INDEX.md` 与计划目录一致）。
