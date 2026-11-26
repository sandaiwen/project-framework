# AGENTS.md

本文件是本仓库的**代理工作约定**。在本仓库执行任务的任何编码代理（Codex、Claude Code、Cursor 及其他 AGENTS.md 兼容工具），在开始工作前必须读完本文件。

本仓库不单独维护 `CLAUDE.md`：Claude Code 自 v2.1.277 起直接读取 `AGENTS.md`，且仓库内一旦存在 `CLAUDE.md` 就会反过来遮蔽它。

---

## 0. 核心开发流程（最高优先级，先读这一节）

**完整规范：`spec/workflow/dev-workflow-guide.md`。本节是它的强制摘要，冲突时以该文件为准。**

一条任务只走这一条路，不允许绕：

```text
设计仓（PRD → 任务卡）── 只读克隆 + design.lock 锁 SHA ──> spec/ 约束
                                        │
                          任务卡 1:1 映射 ▼
                    tasks/plans/<topic>/<plan-id>/（plan.md · STATUS.md · artifacts）
                                        │
                              一单元一提交 ▼
                                  commit / PR
```

三条铁律：

- **MUST 一卡一计划**：一张任务卡对应一个计划目录；不允许合并、不允许拆分。计划开工时在 `Metadata.Source` 写 `design@<sha>#<task-id>`，与 `design.lock` 一致。
- **MUST 设计文档只读**：设计仓克隆到 `.design/` 且不入库；禁止在项目仓修改它，禁止让构建或 CI 读取它。设计有问题 → 在设计仓提 issue，本地计划转 `Blocked`。
- **MUST 一单元一提交**：提交信息 `<type>(<plan-id>): <祈使句结果>`（`type` 取 `ci_cd` 1.2 的合法值），带 `Refs: design@<sha>#<task-id>`、`Plan:` 路径、`Test:` 结果三个 trailer。

任务入口是四份提示词，**选一份用，不混**：

| 入口文件 | 输入 | 审核 | `Metadata.Audit` |
| --- | --- | --- | --- |
| `.agents/prompts/feature-plan.prompt.md` | 设计文档中的一个**需求** | 不审，写完即定稿 | `none` |
| `.agents/prompts/feature-plan-audited.prompt.md` | 同上 | 独立会话/agent 审最多 3 轮 | `L1` / `L2` |
| `.agents/prompts/issue-plan.prompt.md` | 一个**问题**（bug / 缺陷 / 事故） | 不审 | `none` |
| `.agents/prompts/issue-plan-audited.prompt.md` | 同上 | 审最多 3 轮 | `L1` / `L2` |

- 四份是**唯一任务入口**：接任务先选一份，按文件里的入参格式贴一行输入即可跑完（除文件标注的硬停机点外不需要再喂）。
- 选哪份看风险：命中 `spec/plans/plan-audit-guide.md` 0.2 任一条（鉴权、金额、不可逆数据、破坏性迁移、并发、对外契约、安全边界）或线上事故 → 用 audited 两份；否则用不审的两份。轮次上限**统一 3 轮**，第 3 轮起审时必须告知"这是最后一轮"，之后不再加轮；未关闭项转风险敞口（后果 / 检测 / 回退）带险开工。
- 审核报告与响应报告放**同一个计划目录**下 `audits/NN-audit.md`、`audits/NN-response.md`，与 `plan.md` 同级，随计划一起提交。
- 审核**不是流程阶段**：不设开工门禁、不新增状态、不改提交粒度。它只在"写计划"这一段里发生。
- 独立性必须真实：同一会话"顺手再审一遍"等于没审。工具不支持子 agent 时，用提示词里的移交块换会话审。
- 规则：`spec/plans/plan-audit-guide.md`、`spec/plans/plan-audit-response-guide.md`。

闭环五条（缺一条不算完成，判定见规范 4.3）：

1. 范围闭合：计划的「改」清单 = 实际 diff，偏离已记录。
2. 验收闭合：每条验收标准有对应命令与输出，存 `artifacts/`。
3. 回归闭合：改动相关测试与模块回归通过。
4. 记录闭合：Step 全绿、`最终验证` 逐条对应、`遗留/回滚` 已写、STATUS 到 `Verified`。
5. 依赖闭合：新依赖已登记、新迁移已跑升降级、契约基线无未提交变化。

**缺陷修复是同一个流程的另一个入口**：`Metadata.Type` 写 `bugfix` / `incident`，`plan-id` 前缀 `fix-` / `hotfix-`，`Metadata.Issue` 写 `BUG-YYYYMMDD-NN`。目录、状态机、审核、提交全不变，只多一份 `analysis.md`（现象 / 复现 / 影响面 / 根因 / 结论四选一），验收标准换成"复现用例由失败转通过 + 同模块回归"。**不为缺陷另建 `tasks/bugs/` 或 `tasks/issues/` 目录。**规则见 `spec/workflow/bugfix-workflow-guide.md`。

**任务索引是生成的**：`tasks/INDEX.md` 由 `scripts/tasks-index.py` 从各计划目录产出，**禁止手改**；状态变化后跑一次，提交时随计划一起更新。

**最后一环是提交**：闭环五条满足后走 `spec/git/commit-guide.md`——一个计划一次提交，提交前四项自检（范围=计划「改」清单、验收证据在 `artifacts/`、测试真跑过、无敏感文件与生成物），`git diff --cached` 看过一遍，禁用 `git add -A` 与 `--no-verify`；PR 描述写「改了什么 / 怎么验证 / 怎么回滚」。

状态与回改：外部只有 `Planned → In Progress → Verified → Completed`（另有 `Blocked`、`Archived`）；"实施 → 记录 → 测试 → 回改"是 `In Progress` **内部的循环**，不产生新状态。状态定义见 `spec/plans/plan-writing-guide.md` 3.2 / 3.3。

> 违反本节的任一条（跳计划、改设计文档、合并提交、缺证据就标 `Verified`）视为流程违规，不得以"任务紧急"为由豁免。

---

## 1. 仓库定位

本仓库是**项目基础框架仓库**，当前只包含：执行规范、AI 指令、协作产物存档。

当前**不含应用代码**，没有 `backend/`、`frontend/`、`pyproject.toml`、`package.json`。

目标技术栈（应用落地时使用，仓库现状不等于已落地）：

| 层 | 技术 |
| --- | --- |
| 后端 | Python + FastAPI |
| 前端 | Next.js |
| 数据库 | PostgreSQL |

> MUST NOT 假设仓库中已存在后端或前端源码、依赖清单、可执行脚本。需要时先向用户确认，或先看目录实际情况。

---

## 2. 目录结构

```text
.
├── AGENTS.md              # 本文件，代理工作约定（各工具共用这一份）
├── spec/                  # 执行规范，入口是 spec/README.md
│   ├── README.md          #   规范索引：什么场景读哪份
│   ├── workflow/          #   流程：dev-workflow-guide.md（主流程）+ bugfix-workflow-guide.md（缺陷）
│   ├── git/               #   commit-guide.md（提交信息格式 + 本地提交动作）
│   ├── python/            #   python-code-style-guide.md
│   ├── module/            #   module-guide.md
│   ├── frontend/          #   frontend-guide.md
│   ├── testing/           #   README + backend/frontend/e2e/regression/test-data 五份
│   ├── logging/           #   logging-guidelines.md
│   ├── alembic/           #   alembic-guide.md
│   ├── dependency/        #   dependency-guide.md
│   ├── ci_cd/             #   ci-cd-guide.md
│   └── plans/             #   plan-writing-guide.md + plan-audit-guide.md + plan-audit-response-guide.md
├── tasks/                 # 执行记录：INDEX.md（生成的任务索引）+ plans/<topic>/<plan-id>/
├── scripts/               # 工具脚本：tasks-index.py（索引生成与校验）
├── .agents/               # 代理资产
│   ├── prompts/       #   任务入口提示词（4 份，选择表见第 0 节）
│   └── skills/        #   已安装技能包，管理规则见 6.1
├── skills-lock.json       # 技能来源与内容哈希，add / update 的唯一依据
└── docs/                  # 协作文档与项目记录
    ├── deps/              #   依赖决策表、第三方服务登记
    └── regression/        #   回归登记表 registry.yaml（跨前后端唯一一份）
```

---

## 3. 规范入口（动手前必读）

写代码、改数据库、写计划之前，先读 `spec/README.md`，按其中"什么时候读"取用对应文档。

| 要做的事 | 必读 | 路径 |
| --- | --- | --- |
| 接一个需求或问题（**所有任务的入口**） | 入口提示词（四份） | `.agents/prompts/`（选择表见第 0 节） |
| 不确定流程怎么走 | **开发流程规范（主流程）** | `spec/workflow/dev-workflow-guide.md` |
| 写或改 Python 代码 | 编码风格指南 | `spec/python/python-code-style-guide.md` |
| 新建 / 重构一个模块 | 模块编写指南 | `spec/module/module-guide.md` |
| 加日志 | 日志规范 | `spec/logging/logging-guidelines.md` |
| 改表结构、字段、索引 | 迁移规范 | `spec/alembic/alembic-guide.md` |
| 引入/升级/移除依赖、接入第三方服务 | 依赖管理规范 | `spec/dependency/dependency-guide.md` |
| 拆解多步骤任务 | 计划文档规范 | `spec/plans/plan-writing-guide.md` |
| 写实施计划（含要不要审核） | 计划文档规范 + 审核规范 | `spec/plans/plan-writing-guide.md` · `spec/plans/plan-audit-guide.md`（要不要审看其 0.2） |
| 修 bug、处理线上事故 | 缺陷修复规范 | `spec/workflow/bugfix-workflow-guide.md` |
| 提交代码、写提交信息、推 PR | 提交规范（主流程最后一环） | `spec/git/commit-guide.md` |
| 审别人的计划 / 按审核意见调整计划 | 计划审核与响应规范 | `spec/plans/plan-audit-guide.md` · `spec/plans/plan-audit-response-guide.md` |
| 写或改 Next.js 前端代码 | 前端编写指南 | `spec/frontend/frontend-guide.md` |
| 写测试、修缺陷、处理回归 | 测试规范（入口 + 分层索引） | `spec/testing/README.md`（后端 / 前端 / E2E / 回归 / 数据各一份） |
| 建/改流水线、Dockerfile、部署脚本 | CI/CD 规范 | `spec/ci_cd/ci-cd-guide.md` |

规范中的 `MUST` / `MUST NOT` / `SHOULD` / `MAY` 定义见 `spec/python/python-code-style-guide.md` 第 0 章。

规则冲突时按此优先级：正确性 > 保持现有行为 > 可读性 > 简洁性 > 项目现有约定。

---

## 4. 工作流程

1. **先读规范，再动手**。任务涉及的规范没读，不要开始写。
2. **按主流程走**。接口契约、闭环判据、状态进入条件以 `spec/workflow/dev-workflow-guide.md` 为准；多步骤任务再按 `spec/plans/plan-writing-guide.md` 落盘计划，一个计划一个目录，`plan.md` 是唯一核心文档。需要文件化跟踪时，使用 `.agents/skills/planning-with-files`。
3. **实现阶段小步推进**。一次一件事，改完即验证，不要把无关改动夹带进来。
4. **验证要真实**。没有执行的测试不得声称通过；无法执行时明确说明原因和未覆盖内容。
5. **产出归档**。计划审核与响应报告放**该计划目录下的 `audits/`**：`audits/NN-audit.md`、`audits/NN-response.md`，与 `plan.md` 同级，随计划一起提交。

报告必须跟着计划走：报告与计划分离，下次接手的人就找不到"当时为什么这么改"。本项目不设非计划类报告的归档目录——针对 `spec/` 的审查结论直接在对话里给，需要留档时写进对应规范的正文。

---

## 5. 硬性约定

- **语言**：面向用户的说明、代码注释、提交信息、计划文档、报告，一律使用中文。
- **版本信息**：修改任何带 YAML front matter 的规范文档时，同步更新 `version` 与 `last_updated`，正文不重复写版本号。
- **版本只走大版本**：格式固定 `主版本号.0.0`，每次内容变更只递增第一个版本号（`1.0.0` → `2.0.0` → `3.0.0`）。**禁止** `1.1.0`、`1.0.1` 这类次版本与修订号。
- **最小改动**：只改完成当前任务必需的代码或文档，不顺手重构、不顺手格式化无关文件。
- **不编造**：不得假设不存在的函数、接口、配置项、依赖、命令。无法确认时说明不确定性。
- **不擅自扩范围**：新增规范文档、调整目录结构、新增 CI 配置文件（`.github/workflows/`）前，先与用户确认。
- **遵守既有约定**：同一目录内已有文件命名、结构、写法优先于个人偏好。

---

## 6. 常用命令

当前仓库没有应用代码，**没有可用的构建、测试、启动命令**。只有一个工具脚本：

| 命令 | 作用 |
| --- | --- |
| `python scripts/tasks-index.py` | 重写 `tasks/INDEX.md`（计划状态变化后、提交前跑） |
| `python scripts/tasks-index.py --check` | 校验索引与计划目录一致，不一致退出码 1（CI 阶段 1 用） |
| `python scripts/tasks-index.py --stdout` | 打印索引，额外带「停留 N 天」列 |

- MUST NOT 凭经验执行 `npm` / `pnpm` / `pytest` / `uvicorn` 等命令并假定其结果。
- 应用落地后，本节应补充：后端启动与测试命令、前端开发与构建命令、数据库迁移命令（参照 `spec/alembic/alembic-guide.md` 第八章封装脚本）。
- **流水线命令不在本节**：`.github/workflows/` 里的命令一律以 `spec/ci_cd/ci-cd-guide.md` 附录 A 为准；该目录尚未创建，落地时先建再从附录抄进去，不要各自发挥。

### 6.1 技能（skills）管理

技能位于 `.agents/skills/`，来源与内容哈希记录在 `skills-lock.json`。当前 18 个，全部已纳管。

- **只有记录进 `skills-lock.json` 的技能受保护**。不在该文件中的技能目录会被 `npx skills add` 当作无主目录清理 —— 本项目已发生过两次，每次都要从备份逐个恢复。
- 新增技能的唯一方式：`npx skills add <owner>/<repo> --skill <name> -a amp --copy -y`。装完必须核对 `.agents/skills` 的目录数与 `skills-lock.json` 的条目数是否相等。
- **执行 `add` 之前先备份** `.agents/skills`（复制到仓库外的 `_skills-backup/<日期>/`）。
- 手工纳入已有技能时，条目需含 `source` / `sourceType` / `skillPath` / `computedHash` / `installMode`；`computedHash` 是对整个技能目录（排除 `.git`、`__pycache__`、`metadata.json`，路径按正斜杠排序，逐文件 `path\0长度\0内容` 拼接后取 sha256，CRLF 归一为 LF）算的，不能拿 `SKILL.md` 单文件哈希代替。
- 改动任何 `SKILL.md` 后，该技能的哈希即与 lock 不符，会被判为 modified。本地化改动必须在文件内显式标注「本仓库本地化说明」，并同步重算 `computedHash`。
- **技能与本仓库 `spec/` 冲突时，以 `spec/` 为准**：技能提供通用最佳实践，`spec/` 定义本项目允许的做法。

---

## 7. 关于本文件的维护

- 修改 `AGENTS.md` 前说明原因，改动限于"约定"层面，不写具体实现细节（细节归 `spec/`）。
- 不要新增 `CLAUDE.md`：它会让 Claude Code 停止读取本文件。确需 Claude 专属指令时，才建 `CLAUDE.md` 并在首行写 `@AGENTS.md` 导入。
- 其他工具的专用文件（如 Copilot 的 `.github/copilot-instructions.md`、Cursor 规则）如需新增，应先确认。本仓库的提示词统一放 `.agents/prompts/`，**不要另建 `.github/prompts/` 或 `.claude/commands/`**；那个目录不是任何工具的自动加载路径，调用方式是"读某份提示词并执行 + 给入参"。
