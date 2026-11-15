---
version: 11.0.0
last_updated: 2026-11-15
applies_to:
  - tasks/plans/
change_note: 目录增加 audits/（审核与响应报告）；Metadata 增加 Audit 与 Audit Trigger（取值为 none / L1 / L2）；额外文档例外扩为三类
---

# 计划落盘规范（Plan Writing Guide）

本规范规定**一次开发任务的执行计划怎么落盘、写到什么程度、按什么规则更新**。

计划的作用不是事后总结，而是**执行前定清边界、执行中可中断续做、执行后能复核**。因此本规范的重心是：目标是否清楚、验收是否可判定、步骤是否带验证、状态是否真实。

---

## 0. 落盘门槛（强制）

### 0.1 必须建计划

满足以下**任一条**，即必须先建计划目录再动手：

1. 改动涉及 **2 个及以上文件**。
2. 涉及数据库结构或数据变更（任何迁移）。
3. 涉及新增模块、新增对外接口（HTTP、CLI、任务）。
4. 需要多轮验证才能确认完成（含先失败、再修、再跑）。
5. 探索性任务，结论可能与预期相反（先做的目的就是搞清楚该不该做）。
6. 用户明确要求"先出计划"。

### 0.2 不建计划

以下情况不建目录，直接做并在交付说明中写清改了什么：

1. 单文件内的错别字、注释、文案、日志措辞修正。
2. 纯查询、纯调查、只读分析，不修改仓库文件。结论直接在交付说明里写清，不落盘归档。
3. 依赖版本补丁号升级等无行为变化的机械改动。

### 0.3 已建计划的任务范围扩大

不新建计划，更新原计划的 `范围` 与 `步骤`，并在 `决策记录` 写清扩大原因。

**判定标准：拿不准是否该建时建。** 多建一个目录的成本远低于一次无记录的重构。

入口：不要手工按本章建目录，走 `.agents/prompts/` 的四份提示词之一（选择表见 `AGENTS.md` 第 0 节）。提示词负责建目录、写 `plan.md`/`STATUS.md`、跑索引；本章规定它写出来的东西必须长什么样。

---

## 1. 目录与文件（强制）

```text
tasks/plans/<topic>/
  <plan-id>/
    analysis.md      # 仅缺陷/事故类（Type: bugfix|incident）；功能任务不建
    STATUS.md
    plan.md
    audits/          # 审核与响应报告，按轮次编号；仅触发审核时创建
    artifacts/
```

- `<topic>`：主题域，`kebab-case`，例如 `auth`、`alembic`、`catinfo-dashboard`。用**受影响的模块或领域**，不用 `bug`、`fix`、`issues` 这类来源词。
- `<plan-id>`：`YYYYMMDD-<short-slug>-NN`。`NN` 为同一 slug 内的两位递增序号，不同 slug 独立编号。缺陷类前缀 `fix-`、事故 `hotfix-`（`spec/workflow/bugfix-workflow-guide.md` 1.2）。
- `artifacts/`：只放自动生成或体积大的产物（`pytest.log`、`build.log`、`coverage.html`、`explain.json`）。没有产物时保留空目录。

示例：

```text
tasks/plans/auth/20261115-user-login-01/
  STATUS.md
  plan.md
  artifacts/
```

### 1.1 三个文件的职责边界（强制）

| 文件 | 只写什么 | 不写什么 |
| --- | --- | --- |
| `plan.md` | 目标、验收标准、范围、步骤、决策、遗留、回滚 | 当前状态的一行摘要（那属于 STATUS.md） |
| `STATUS.md` | 当前状态、下一步动作、更新时间，共 3 行 | 进展叙述、结论、分析过程 |
| `audits/` | 审核报告 `NN-audit.md` 与响应报告 `NN-response.md`，按轮次成对 | 代码、验证结论、命令输出（那些在 `artifacts/`） |
| `analysis.md` | 缺陷/事故类的问题分析：现象、复现、影响面、根因、结论（模板见 `spec/workflow/bugfix-workflow-guide.md` 第 3 章） | 修复方案、步骤、验收标准（那些在 `plan.md`） |
| `artifacts/` | 命令原始输出与生成物 | 手写总结 |

`plan.md` 是唯一事实源：任何结论、决策、进展都写在这里。`STATUS.md` 只做"一眼看到进度"，不承载信息。

**禁止横向分类目录**：不得用 `tasks/plans/changelog/`、`verification/`、`reports/`、`summary/` 作为组织方式，必须按"一个计划一个目录"组织。

### 1.2 `tasks/INDEX.md`（生成物，禁止手改）

`tasks/INDEX.md` 是**执行任务索引**：一眼看到哪些计划在进行、哪些已收口、哪些卡住了。

它是**派生视图**，不是事实源。每个字段都从计划目录里取，脚本不产生任何新信息：

| 列 | 取自 |
| --- | --- |
| 日期 | 目录名前缀 `YYYYMMDD`（必须与 `Metadata.Created` 一致，不一致直接报错） |
| plan-id | 目录名（必须与 `Metadata.Plan ID` 一致） |
| Type | `Metadata.Type` |
| 模块 | 父目录名 `<topic>` |
| 目标 | `plan.md`「目标」段第一段，压成一行 |
| 状态 | `STATUS.md` 第一行 `Current Status:` |
| 最后更新 | `STATUS.md` 的 `Updated` 日期 |

分段：`## 进行中`（`Planned` / `In Progress` / `Blocked`）、`## 已收口`（`Verified` / `Completed` / `Archived`）、`## 未成立的问题`（只有 `analysis.md` 的缺陷目录，显示结论）。

```bash
python scripts/tasks-index.py            # 重写 tasks/INDEX.md
python scripts/tasks-index.py --check    # 只校验，不一致退出码 1 并打印 diff
python scripts/tasks-index.py --stdout   # 打印到终端，额外带「停留 N 天」列
```

- MUST 在计划状态变化后、提交之前跑一次 `tasks-index.py`；它与 `STATUS.md` 的修改在同一次提交里。
- MUST NOT 手改 `tasks/INDEX.md`。要改状态改 `STATUS.md`，要改目标改 `plan.md`，然后重新生成。
- MUST 任何数据问题（缺 `STATUS.md`、`Metadata.Created` 与目录名不一致、状态值非法）都**报错退出，不猜、不跳过**——索引宁可不出，也不能出错的。
- 索引文件里**不写生成时间**，也不写「停留天数」：它们每天都变，会让 `--check` 永远失败、让每次提交都产生无意义的 diff。「停留」只在 `--stdout` 里给。
- 校验放在 CI 阶段 1（`spec/ci_cd/ci-cd-guide.md` 2.2），与目录不一致即阻断。

---

## 2. plan.md 模板（强制遵循）

```md
## Metadata

- Plan ID:
- Topic:
- Owner:
- Created:
- Last Updated:
- Source: design@<commit>#<task-id>
- Revision: <设计任务卡版本>
- Type: <feature|bugfix|incident|refactor>
- Issue: <BUG-YYYYMMDD-NN|none>
- Audit: <none|L1|L2>
- Audit Trigger: <none|选审核的理由>

## 目标

一句话：做完之后什么变了。不写手段，只写结果。

## 验收标准

- [ ] 可判定的条件：跑什么命令、期望输出是什么；或哪个接口返回什么；或页面出现什么行为
- [ ] 可判定的条件

每条都必须能被第三个人独立判定真假。"功能正常""体验良好"不算验收标准。

## 范围

改：
- backend/app/modules/auth/（新建）
- backend/alembic/versions/（新增一个迁移）

不改：
- 前端登录页
- 鉴权中间件

## 前置条件

- 依赖的任务、环境、数据、权限；没有则写"无"。

## 风险

只写会改变做法的风险，以及对应的应对。没有则写"无"。

## 步骤

### Step 1 <动作名>

- 文件：路径（新建 / 修改）
- 动作：具体改什么
- 验证：验证方式（命令、期望结果、或可观察行为）
- 状态：待做 / 进行中 / 完成

### Step 2 <动作名>

...

## 最终验证

- 逐条对照"验收标准"，写明实际执行的方式与结果。

## 决策记录

- 决策内容 —— 原因 —— 被否掉的替代方案。只记会被人反复问起的决策。

## 遗留问题

- 本次不做、但已确认存在的问题，写清影响与建议的后续任务。

## 回滚

- 回滚步骤，或"无需回滚（只增不改）"。
```

模板使用要求：

1. `Metadata`、`目标`、`验收标准`、`范围`、`步骤` 必填，其余按需，无内容写"无"。
2. `Source` 与 `Revision` 在任务来自设计仓时必填，格式与比对规则见 `spec/workflow/dev-workflow-guide.md` 2.2 与第 7 节；不来自设计仓的任务写"无"。
3. `步骤` 的粒度以"能单独验证"为准：一步对应一次可验证的改动。不得把"实现整个模块"作为一步。
4. 单步内不写代码实现细节，只写文件、动作、验证方式。
5. 步骤顺序必须与实际执行顺序一致；实际偏离时更新计划，不要事后倒着补。

---

## 3. STATUS.md 格式与状态机（强制）

### 3.1 格式

```md
Current Status: In Progress
Next Action: 实现 AuthService.login 并补 pytest
Updated: 2026-11-15 05:10
```

三行，不得增加段落。`Next Action` 必须是**下一个具体动作**，不是"继续开发"。

### 3.2 状态定义

| 状态 | 含义 |
| --- | --- |
| `Planned` | 计划已落盘，未开工 |
| `In Progress` | 正在执行 |
| `Blocked` | 因外部原因停滞；`plan.md` 必须写阻塞原因与解除条件 |
| `Verified` | 验收标准逐条通过，但尚未合并或交付 |
| `Completed` | 已合并或已交付 |
| `Archived` | 不再活跃（已完成归档，或已废弃） |

`Verified` 与 `Completed` 的区别只在"是否已合入/交付"，不得混用。

审核**不新增状态**：审核与响应都发生在 `Planned` 阶段，`STATUS.md` 的 `Next Action` 写"等待第 N 轮审核"或"按 audits/N-response.md 调整计划"即可。

### 3.3 允许的状态转移

| 从 | 到 |
| --- | --- |
| `Planned` | `In Progress`、`Archived` |
| `In Progress` | `Blocked`、`Verified`、`Archived` |
| `Blocked` | `In Progress`、`Archived` |
| `Verified` | `Completed`、`In Progress`（验证后发现缺陷） |
| `Completed` | `Archived` |
| `Archived` | 终态，不再变更 |

未经上表的转移（如 `Planned` 直接到 `Completed`）视为违规。

---

## 4. 更新规则（强制）

1. **开工即改**：开始执行前把 `STATUS.md` 从 `Planned` 改为 `In Progress`。
2. **每完成一步就更新**：把该 Step 的 `状态` 改为"完成"，并更新 `STATUS.md` 的 `Next Action`。
3. **双处同步**：状态变更时，`plan.md` 的步骤状态与 `STATUS.md` 必须同一轮改完，不允许只改一处。
4. **时间只写真实的**：`Last Updated` / `Updated` 写实际操作时间（日期 + 时分即可）。未记录就留空，**禁止编造时间戳**。
5. **决策与偏离必须落字**：与计划不一致的做法，先写进 `决策记录` 再执行。
6. **收口**：
   - 补齐 `最终验证`，逐条对应验收标准；
   - 补齐 `遗留问题` 与 `回滚`；
   - `STATUS.md` 改为 `Verified`，合入或交付后改为 `Completed`。
7. **废弃**：`STATUS.md` 改为 `Archived`，`plan.md` 写明废弃原因、已完成部分、后续建议。目录保留，不删除历史。

---

## 5. 允许新增的额外文档（仅例外）

只有四类：

1. 自动生成的大产物 → `artifacts/`。
2. 超大型任务（架构迁移、多仓库改造、对外接口重设计）→ 可在计划目录内新增 `design.md`、`migration.md`、`rollback.md`。
3. 审核与响应报告 → `audits/NN-audit.md` / `audits/NN-response.md`，规则见 `spec/plans/plan-audit-guide.md` 与 `spec/plans/plan-audit-response-guide.md`。
4. 缺陷/事故类的问题分析 → `analysis.md`，规则见 `spec/workflow/bugfix-workflow-guide.md`。它先于 `plan.md` 存在，因为"确认问题是否存在"可能得出不修代码的结论（那时只留 `analysis.md` + `STATUS.md`：`not-a-bug` 转 `Archived`，`design-gap` 转 `Blocked` 等设计仓改完）。

除以上四类，不得新增 `step1-summary.md`、`verification.md`、`report.md` 等碎片文档。碎片文档会与 `plan.md` 形成两份事实源。

---

## 6. 中断与交接

1. 中断时不做长篇交代：更新 `STATUS.md` 的 `Next Action` 与 `plan.md` 的当前步骤状态即可。
2. 接手者按顺序读三处：`STATUS.md`（现在到哪一步）→ `plan.md` 的 `目标`/`验收标准`/`范围`（要做什么）→ `决策记录`（为什么这么做）。
3. 阻塞超过预期时改 `Blocked` 并写解除条件，不要长期停留在 `In Progress`。

---

## 7. 禁止事项

1. 用 `STATUS.md` 写进展长文，而 `plan.md` 不更新。
2. 验收标准写成主观描述（"功能正常""基本可用"）。
3. 步骤写成无法验证的大块（"完成后端开发"）。
4. 事后补写计划，用于交差（计划应能指导执行，不是执行后的说明书）。
5. 编造时间戳、验证结果或命令输出。
6. 同一任务并存两份计划，或新建计划替代原计划而不在原计划里记录关联。
7. 在 `artifacts/` 之外散放日志与生成物。

---

## 8. 提交前检查清单

对本次任务的计划目录逐项确认：

- [ ] 目录为 `tasks/plans/<topic>/<plan-id>/`，含 `STATUS.md`、`plan.md`、`artifacts/`。
- [ ] `plan.md` 的 `目标` 是一句话结果，不含手段。
- [ ] `验收标准` 每条都能被独立判定真假。
- [ ] `范围` 同时写了"改"与"不改"，并列出具体文件或目录。
- [ ] 每个 Step 都有 `文件` 与 `验证`，状态与实际一致。
- [ ] `Metadata.Audit` 已写（`none` / `L1` / `L2`）；做过审核的，`audits/` 下报告与响应成对且轮次一致（`pass` 轮次无需 response）。
- [ ] `STATUS.md` 只有三行，`Next Action` 是具体动作。
- [ ] `plan.md` 与 `STATUS.md` 的状态一致，且转移合法。
- [ ] 完成时 `最终验证` 已逐条对应验收标准。
- [ ] 时间戳真实，未编造。

---

## 9. 核心信条

**一个计划目录 + 一份 plan.md = 一个可执行、可中断、可复核的状态机。**

计划的成本应当花在"想清楚要做什么、怎么算做完"，而不是花在记账格式上。
