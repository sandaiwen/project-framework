---
version: 8.0.0
last_updated: 2026-11-15
---

# spec —— 项目执行规范

本目录存放项目**执行期**必须遵守的规范。每份文档约束一类具体动作：只规定"怎么做"，不描述"怎么设计""怎么论证设计"。

## 文档清单

| 文档 | 约束的动作 | 什么时候读 |
| --- | --- | --- |
| `workflow/dev-workflow-guide.md` | **主流程**：设计仓 → 项目仓 → 计划单元 → 闭环 → 提交；三层职责、三个接口（只读锁版本 / 任务卡 1:1 / 一单元一提交）、闭环五条、提交最后一环、状态进入条件、设计变更回流 | 接任何一个设计任务之前；不确定流程怎么走时 |
| `workflow/bugfix-workflow-guide.md` | **缺陷修复**：适用范围（bugfix/incident/design-gap）、编号与目录、七步流程、`analysis.md` 模板、根因三条判据、红→绿→反向验证、测试分层、回归登记、提交与重开 | 发现 bug、处理线上事故、判定"这是不是缺陷"时 |
| `git/commit-guide.md` | **提交**：提交信息格式与 `type`/`scope` 约定（唯一来源）、提交单元切分、提交前四件必须为真、暂存与复核命令、该拆还是该合、失败与返工、脏工作区例外 | 写提交信息、执行提交、推 PR 之前 |
| `python/python-code-style-guide.md` | 写、改 Python 代码：格式、命名、导入、类型注解、注释、异常、日志调用、测试 | 动手写任何代码之前 |
| `module/module-guide.md` | 实现一个模块：目录结构、用类还是用函数、依赖注入、分层与装配、对外接口 | 新建模块或调整模块结构时 |
| `frontend/frontend-guide.md` | 写前端代码：`src` 目录划分、页面与 feature 边界、Server/Client 组件边界、数据获取位置、类型与 API 契约、组件与状态、UI 组件与样式（shadcn/ui + Tailwind） | 新建页面、组件或 feature 时 |
| `testing/README.md` | 选层判据、目录总览、执行时机与 CI 分层、flaky 治理、跨层提交清单 | 开始写第一个测试之前 |
| `testing/backend-testing-guide.md` | 后端测试：pytest 配置、目录镜像、fixture、mock 与替身、接口与数据库测试、参数化、覆盖率 | 写后端测试、改 `conftest.py` 时 |
| `testing/frontend-testing-guide.md` | 前端测试：Vitest 配置、能测与不能测、组件四态、数据层、快照、契约类型 | 写前端测试、改 `vitest.config.mts` 时 |
| `testing/e2e-testing-guide.md` | 端到端：服务编排与探活、造数与清理、选择器与等待、断言、行为清单、失败产物 | 写 Playwright 用例、改 `playwright.config.ts` 时 |
| `testing/regression-testing-guide.md` | 回归：三条必要条件、反向验证、登记表、三档范围、契约与迁移基线、腐化退役、红灯放行 | 修缺陷、发布前、季度抽检时 |
| `testing/test-data-guide.md` | 测试数据：造数工厂、唯一性、隔离三档、时间与随机、外部依赖替身 | 第一次造数据、发现用例互相污染时 |
| `logging/logging-guidelines.md` | 打日志：级别、格式、字段、敏感信息、路由 | 第一次在该模块加日志时 |
| `alembic/alembic-guide.md` | 改数据库结构：迁移文件命名与内容、执行与回滚、封装脚本 | 有任何表、字段、索引变更时 |
| `dependency/dependency-guide.md` | 依赖管理：版本与锁文件、后端（uv）与前端（npm）依赖分组、第三方 SDK 封装、新依赖准入、升级与移除、供应链安全、工具链与系统包 | 引入/升级/移除任何依赖、接入第三方服务时 |
| `plans/plan-writing-guide.md` | 落盘执行计划：落盘门槛、目录三件套、`tasks/INDEX.md`（生成的任务索引）、`plan.md` 字段、验收标准、状态机与更新规则 | 启动任何满足落盘门槛的开发任务之前（判定见其第 0 章）；要不要审核见 `plans/plan-audit-guide.md` 0.2 |
| `plans/plan-audit-guide.md` | 计划审核：档位建议（`none` / `L1` / `L2`）与抽查、审核者独立性、八维度、严重度与结论、3 轮上限与"最后一轮"告知、末轮后转风险敞口、报告模板与 `audits/` 命名 | 决定要不要审、执行审核时 |
| `plans/plan-audit-response-guide.md` | 审核响应：逐条处置（accept/partial/reject/defer/risk）、改计划的位置对应、响应报告模板、末轮收口（`start` / `start-with-risk`） | 拿到审核报告、调整计划时 |
| `ci_cd/ci-cd-guide.md` | 建与改流水线、部署：分支与提交约定、流水线阶段与门禁、依赖与工具链锁定、镜像与产物、环境与密钥、迁移时序、部署与回滚、供应链安全、发布与度量 | 新增或修改 `.github/workflows/**`、`Dockerfile`、部署脚本时；准备第一次自动部署之前 |

## 一个功能从零落地时的顺序

开工前先读 `workflow/dev-workflow-guide.md`，确认这条任务走的是哪条路径、依据哪一版设计。

0. **选入口**：`.agents/prompts/` 下四份提示词二选一（需求 / 问题）×（不审 / 审），具体选择表见 `AGENTS.md` 第 0 节。选错档位的代价是漏审或白审，比选错顺序严重。
1. `plans/plan-writing-guide.md` —— 先把任务落成计划：定目标、验收标准、范围与步骤。
2. `module/module-guide.md` —— 后端：定模块边界、文件结构、类的划分。
3. `frontend/frontend-guide.md` —— 前端：定路由、feature、组件边界与取数位置。
4. `python/python-code-style-guide.md` —— 写代码时的通用约束。
5. `testing/README.md` —— 先看选层判据；然后按侧读 `backend-testing-guide.md` 或 `frontend-testing-guide.md`，跨栈流程读 `e2e-testing-guide.md`。每完成一步就补该层测试；修缺陷先写失败用例并读 `regression-testing-guide.md`。
6. `logging/logging-guidelines.md` —— 加日志。
7. `alembic/alembic-guide.md` —— 涉及数据结构时写迁移。
8. `ci_cd/ci-cd-guide.md` —— 代码要进流水线、要自动部署时：按第 13 章分阶段落地，先 CI 再发布再生产。

只做后端或只做前端时，跳过另一侧的第 2 或第 3 步。第 5 步不是最后一步：测试随代码走，不攒到最后补。

第 8 步与其它步不同：它不是每个功能都要读，而是**建/改流水线时**读一次，之后按它维护。

另有一份不在流程里的常备规范：`dependency/dependency-guide.md`。任何一步只要涉及"新增一个包 / 接入一个第三方服务 / 升级主版本"，先读它，并同步更新 `docs/deps/decisions.md`。

多数任务只涉及其中 1~2 份，按上表"什么时候读"取用，不必全读。

## 约束等级

`MUST` / `MUST NOT` / `SHOULD` / `SHOULD NOT` / `MAY` 的定义见 `python/python-code-style-guide.md` 第 0 章，本目录所有文档沿用同一套等级。

规则冲突时的优先级：

1. 正确性优先于代码风格。
2. 保持现有业务行为优先于改写。
3. 可读性优先于简洁性。
4. 项目现有约定优先于文档中的非强制建议。

## 文件与格式约定

- **目录**：一个主题一个子目录，目录名用 `lower_snake_case`。
- **命名**：`{主题}-guide.md` 或 `{主题}-guidelines.md`。
- **头部**：一律使用 YAML front matter，必须包含 `version` 与 `last_updated` 两个字段。
- **正文**：不在正文中重复写版本号，版本信息只出现在 front matter。
- **版本**：只用大版本，格式固定 `主版本号.0.0`（`1.0.0` → `2.0.0` → `3.0.0`）。每次内容更新只递增第一个版本号，**不使用 `1.1.0` / `1.0.1` 之类的次版本与修订号**；同步更新 `last_updated`。
