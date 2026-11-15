---
version: 3.0.0
last_updated: 2026-11-15
---

# 提交规范（Commit Guide）

本规范规定两件事：**提交信息写什么**（版本控制层的约定），以及**工作区里的改动怎么变成一个正确的提交**（切多大、怎么暂存、怎么复核、失败怎么重来）。

它是 `spec/workflow/dev-workflow-guide.md` 的最后一环：闭环五条满足之后、状态转 `Completed` 之前，走这里。放在 `spec/git/` 而不是 `spec/workflow/`，因为提交首先是版本控制操作，不是流程阶段。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

---

## 0. 分工：本文管什么，不管什么

| 事项 | 归哪 | 本文的位置 |
| --- | --- | --- |
| **提交信息格式、`type` 取值、`scope`、破坏性变更标记** | **本文第 3 章** | **唯一来源**，`ci_cd` 不再重复定义 |
| 分支模型、`main` 保护、squash 合并、PR 描述三块 | `spec/ci_cd/ci-cd-guide.md` 1.1 / 1.3 / 1.4 / 1.5 | 遵守，不另立一套 |
| 某类 `type` 在流水线上触发什么额外动作 | `spec/ci_cd/ci-cd-guide.md` 1.2 | 只管本地怎么写，不管流水线怎么反应 |
| 计划目录里放什么、状态机怎么转 | `spec/plans/plan-writing-guide.md` | 提交前以它为准 |
| 提交里的代码该长什么样 | `spec/python/`、`spec/frontend/`、`spec/module/` | 与本规范无关 |

一句话：**版本控制的约定与本地动作在本文，流水线与协作流程在 `ci_cd`。**

旧的「小任务提交」提示词按文件类型分批（文档 / 代码 / 配置分三次），与本文第 1、5 章冲突——**冲突以本文为准**。分批的唯一依据是「能否独立回滚且独立成立」。

---

## 1. 提交单元：一个计划一次提交

| 规则 | 判定方式 |
| --- | --- |
| MUST 一个计划对应一次提交 | 提交的 `scope` 就是 `plan-id`；一次提交里不得出现第二个 `plan-id` |
| MUST 一次提交只做一件逻辑上完整的事 | 用一句话能说清"改了什么行为"；说不清就是混了 |
| MUST 不建计划的改动独立成一次提交 | 错别字、注释、配置微调各归各的提交，不夹带进计划提交 |
| MUST 跨两个计划的改动拆成两次提交 | 两个计划分别收口；不允许"反正一起改的" |
| SHOULD 单次提交不超过 25 个文件或 800 行净增 | `git diff --stat` 一眼可数；超了说明单元太粗，回头拆计划 |
| MUST NOT 把顺手修的问题混进来 | 另开一次提交，消息里写清是顺手修的 |

**为什么不是"按文件类型分批"。** 早期做法是按代码 / 文档 / 配置分三次提交，看着整齐，实际把一次改动切成三段：单看任一段都跑不过、回滚任一段都不成立、`git blame` 找不到"为什么"。**切分的唯一依据是"能否独立回滚且独立成立"，不是文件后缀。**

计划目录里的东西（`plan.md`、`STATUS.md`、`audits/`、`artifacts/`）与代码**必须同一次提交**：计划说做了、代码没做，是最难查的一类不一致。

---

## 2. 提交前必须为真的四件事

缺任何一件都不要提交。每件都有可执行判定：

| # | 判定项 | 命令 / 证据 | 不满足的后果 |
| --- | --- | --- | --- |
| 1 | 改动范围 = 计划「改」清单 | `git status --short` + `git diff --stat`，逐条对照 `plan.md` 的 `范围-改` | 计划与代码脱节，闭环第 1 条不成立 |
| 2 | 每条验收标准都有证据 | `artifacts/` 下能对上号的输出；`plan.md` 的 `最终验证` 逐条对应 | 没人能判断这次到底算不算做完 |
| 3 | 测试是真跑过的 | 命令 + 摘要进 `artifacts/`（`spec/testing/README.md` 第 2 节） | "跑过了"无法复核，等于没跑 |
| 4 | 没有禁止入库的内容 | 见下方扫描 | 密钥进历史，只能轮换 + 重写历史 |

```bash
# (1) 看全貌：改了什么、多了什么
git status --short
git diff --stat

# (2) 抓敏感与生成物（有输出就必须逐个解释）
git status --short | grep -Ei '\.env|secret|credential|\.pem|\.key|id_rsa'
git status --short | grep -Ei 'node_modules|\.venv|dist/|build/|__pycache__|\.pyc|coverage\.xml|\.log$'

# (3) 未跟踪目录必须展开成文件清单，不能整体 add
git ls-files -o --exclude-standard

# (4) 锁文件变了要能解释
git diff --stat -- '*uv.lock' '*package-lock.json' '*poetry.lock'
```

- MUST (2) 有输出时逐个说明为什么该进仓库；说不清就移出暂存。
- MUST 锁文件变更与 `pyproject.toml` / `package.json` 的变更同时出现；只变锁文件说明是本地乱跑命令，回退它（`spec/dependency/dependency-guide.md` 1）。
- MUST 新增迁移时，同一次提交里要有 `alembic upgrade head` 与 `downgrade -1` 的执行输出（`spec/alembic/alembic-guide.md`）。

---

## 3. 消息格式

沿用 `spec/ci_cd/ci-cd-guide.md` 1.2 的 Conventional Commits，本项目的落地形态：

```text
<type>(<plan-id>): <祈使句结果>

<为什么这么改，1～3 行，可选>

Refs: design@<sha>#<task-id>
Plan: tasks/plans/<topic>/<plan-id>/
Test: <实际执行的命令> — <结果摘要>
```

| 字段 | 本项目取值 |
| --- | --- |
| `type` | 计划驱动：`feat` `fix` `refactor` `perf` `test` `docs` `chore` `ci` `build` `style` `revert` 之一 |
| `scope` | **计划驱动固定写 `plan-id`**；无计划的小改用模块名（`auth`、`orders`）或 `deps`、`ci`、`db` |
| `subject` | 祈使句、≤72 字符、结尾不加句号、不加前缀 `[xxx]` |
| `body` | 只写**为什么**；不写"改了哪些文件"（diff 里有） |
| 三个 trailer | 计划驱动必填；无计划时 `Plan:` 写 `none` |

**为什么 `scope` 放 `plan-id` 而不是再发明一个 `plan(...)` 类型。** `plan` 不是合法 `type`，会让 commitlint、semantic-release 之类的工具直接失效；放到 `scope` 既保住 Conventional 兼容，又保住"从提交反查计划"这条链路。

### 3.1 类型怎么选

| 场景 | type | 说明 |
| --- | --- | --- |
| 新增用户可感知的行为 | `feat` | 新接口、新页面、新命令 |
| 修缺陷 | `fix` | 必须带回归用例、`registry.yaml` 条目、`Issue:` trailer；`body` 写一句根因，`Test:` 写红→绿（`spec/workflow/bugfix-workflow-guide.md` 第 9 章） |
| 不改行为、只调结构 | `refactor` | 判据：对外行为与测试断言都没变 |
| 只加/改测试 | `test` | 不夹带生产代码改动 |
| 只改文档、注释、规范 | `docs` | 计划目录里的 `plan.md` 单独提交时用这个 |
| 依赖、工具链、配置 | `chore` / `deps` / `build` / `ci` | 独立提交，便于整体回滚 |
| 纯格式化（无逻辑变化） | `style` | 必须单独一次，否则 review 无法看 |
| 回滚某次提交 | `revert` | body 写被回滚的 SHA 与原因 |
| 破坏性变更（接口不兼容、行为作废） | 上述任一 `type` 加 `!` | `feat!:` 或 footer 写 `BREAKING CHANGE:`；它决定版本号递增与是否要分阶段迁移（`spec/ci_cd/ci-cd-guide.md` 1.2） |

### 3.2 反例

| 反例 | 问题 |
| --- | --- |
| `update code` | 没有行为信息，`git log --oneline` 里等于噪音 |
| `fix bug` | 哪个 bug？没有回归用例无法判断 |
| `feat: 新增订单导出功能，同时调整了鉴权中间件和依赖版本` | 三件事一个提交，无法单独回滚 |
| `plan(20261115-order-export): 完成` | `plan` 不是合法 type；"完成"不是结果 |
| subject 里写文件清单 | 与 diff 重复，且改名后失真 |

---

## 4. 暂存与提交：固定动作

按顺序执行，不要跳步：

```bash
# 1) 只暂存本次要提交的文件，逐个写出来
git add -- backend/app/modules/orders/export.py
git add -- backend/tests/modules/orders/test_export.py
git add -- tasks/plans/orders/20261115-order-export/

# 2) 复核暂存内容（这一步最容易发现问题）
git diff --cached --stat
git diff --cached

# 3) 提交（多行 trailer 用 heredoc，避免被 shell 吃掉）
git commit -F - <<'MSG'
feat(20261115-order-export): 支持按时间范围导出订单 CSV

导出走流式写出，避免大结果集占满内存。

Refs: design@9f3c1ab#TASK-07
Plan: tasks/plans/orders/20261115-order-export/
Test: uv run pytest -q tests/modules/orders — 42 passed
MSG

# 4) 核对结果
git log -1 --stat
git status --short
```

- MUST 显式列出暂存路径。**`git add -A` / `git add .` / `git commit -a` 一律禁止**：它们会把无关改动、生成物、别人的半成品一起带进来，而 `git diff --cached` 通常看不出来。
- MUST 提交前看一遍 `git diff --cached` 的完整内容，特别是迁移文件、配置、`.env.example`。
- MUST 提交后再跑一次 `git status --short`，确认剩下的改动都是有意留下的。
- SHOULD 用 `git add -p` 处理同一文件里混着无关改动的情况；拆不开时说明这次改动本身不干净。

---

## 5. 该拆还是该合

| 情形 | 处理 | 理由 |
| --- | --- | --- |
| 代码 + 迁移 + 计划文档 | **合成一次** | 拆开后任一单独都不成立：没有迁移代码跑不起来 |
| 修复 + 它引入的回归用例 | **合成一次** | 用例是修复的一部分，分开会让"修复"本身不可验证 |
| 纯格式化 / 重排 import | **必须单独一次** | 混进功能提交会让 review 与 blame 失效 |
| 依赖升级（`uv.lock` / `package-lock.json`） | **单独一次** | 回滚依赖与回滚业务是两件事 |
| 跨两个计划 | **拆成两次** | 否则 `plan-id` 与提交不再一一对应 |
| 顺手修的小问题（拼写、日志措辞） | **单独一次** | 计划提交里出现无关 hunk 就无法用计划解释 |
| 一次改动 >25 文件 | **回头拆计划** | 不是拆提交，是计划粒度错了 |

---

## 6. 失败与返工

| 情形 | 正确做法 | 禁止 |
| --- | --- | --- |
| pre-commit / hook 失败 | 读报错、改根因、重新提交 | `--no-verify`（跳过门禁等于把问题推给 CI） |
| 漏了文件 | 补一次新提交，subject 写清补了什么；squash 合并时自然并进去 | `git commit --amend` 已推送的提交 |
| 提交信息写错 | 仅当**未推送**时可 `git commit --amend`；已推送就留着，历史不改 | 在已推送分支上改写历史、强推 `main` |
| 提交后才发现测试红 | 新提交修复，并在 `plan.md` 的「决策记录」写一行 | revert 掉红提交假装没发生（缺陷会被埋） |
| 提交里混进了不该有的文件 | 未推送：`git reset --soft HEAD~1` 重新切；已推送：新提交删除，并说明原因 | `git reset --hard`、`checkout --` 抹掉工作区 |
| 需要改历史（合错单元、密钥误入） | 停下，单独开一个计划处理；密钥误入必须**先轮换密钥** | 直接 `filter-repo` / `rebase -i` 式重写已共享的历史 |

- MUST hook 失败一律改根因。门禁被绕过一次，之后每次都会有人绕过。
- MUST 已推送的历史不改写。改历史的代价（所有人的本地仓库都要重置）远大于一条难看的提交信息。

---

## 7. 脏工作区与例外

工作区里常有别人的、别的任务的、自己忘了的改动。规则：

| 情况 | 做法 |
| --- | --- |
| 有与本任务无关的改动 | 显式路径暂存，**不清理、不回滚、不顺手提交** |
| 有未跟踪目录 | 先 `git ls-files -o --exclude-standard` 展开成文件清单，确认无生成物再逐个 add |
| 需要临时切分支 | 用 `git stash push -- <path>` 只暂存自己的文件；不要把整个工作区 stash，那会把别人的改动一起卷走 |
| 文件被 `.gitignore` 命中但确实要入库 | 先改 `.gitignore` 的排除规则（说明原因），必要时 `git add -f`；**不得**只 `-f` 不改规则，否则下一个人会再踩 |
| 仓库里已有大文件 / 生成物被跟踪 | 另开计划处理（涉及历史清理），不在业务提交里顺手删 |

- MUST NOT 为了让 `git status` 干净而提交无关文件。
- MUST NOT 用 `git clean -fd` 清工作区；它删掉的是别人正在做的活。

---

## 8. 提交之后

1. **推送并开 PR**；PR 标题用同一个 subject，描述按 `spec/ci_cd/ci-cd-guide.md` 1.5 的三块写（改了什么 / 怎么验证 / 怎么回滚）。
2. **马上看 CI**。红了立刻修，不要等评审——评审看到红 PR 只会多花一轮。
3. **合入后**才把 `STATUS.md` 转 `Completed`（`spec/plans/plan-writing-guide.md` 3.2）。
4. **验证可回滚**：这条提交必须能独立 `git revert`。做不到说明单元切错了，在计划里记一笔，下次别这么切。

---

## 9. 禁止事项

- MUST NOT 用 `git add -A` / `git add .` / `git commit -a`。
- MUST NOT `git commit --no-verify`，也不得临时改 hook 脚本绕过检查。
- MUST NOT 提交 `.env`、凭据、私钥、token、本地数据库文件。
- MUST NOT 提交 `node_modules/`、`.venv/`、`dist/`、`build/`、`__pycache__/`、日志与覆盖率产物。
- MUST NOT 把两个计划的改动放进同一次提交。
- MUST NOT 用 `reset --hard`、`checkout --`、`clean -fd` 处理"工作区不干净"。
- MUST NOT 在已推送的分支上改写历史或强推 `main`。
- MUST NOT 提交未经运行的测试、未执行的迁移演练。
- MUST NOT 提交信息写"update"、"fix bug"、"完成"这类没有行为信息的描述。
- MUST NOT 在没有计划的情况下提交业务代码改动（门槛见 `spec/plans/plan-writing-guide.md` 第 0 章）。

---

## 10. 检查清单

**提交前**

- [ ] 改动范围 = `plan.md` 的「改」清单，偏离已在「决策记录」写明。
- [ ] `artifacts/` 里每条验收标准都有对应输出。
- [ ] 测试真跑过，命令与摘要已记录。
- [ ] 敏感文件、生成物、大文件扫描无输出（或已逐个解释）。
- [ ] 迁移有升降级输出，锁文件变更能解释。
- [ ] `git diff --cached` 完整看过一遍。
- [ ] `scope` 是 `plan-id`，三个 trailer 齐全。

**提交后**

- [ ] `git log -1 --stat` 的内容与预期一致。
- [ ] `git status --short` 只剩有意留下的改动。
- [ ] PR 描述三块齐全，CI 结果已看。
- [ ] 这条提交可独立 `git revert`。
