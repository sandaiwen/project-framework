---
version: 5.0.0
last_updated: 2026-11-15
---

# 缺陷修复流程（Bugfix Workflow Guide）

本流程规定**发现一个缺陷或问题之后，怎么确认、定位、修、验证、登记、提交**。

它与 `dev-workflow-guide.md` 是**同一条流水线的两个入口**，不是两套体系：目录、计划单元、状态机、审核、提交全部复用主流程；多出来的只有两件事——开工前一份 `analysis.md`，验收标准从"功能可用"换成"**复现用例由失败转通过**"。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

---

## 0. 适用范围：什么进这里，什么不进

| 情形 | 去哪 | 判据 |
| --- | --- | --- |
| 实现与预期不符（代码写错了） | **本文**，`Type: bugfix` | 预期行为本来是明确的，是代码没做到 |
| 线上已经出问题（有用户/数据受影响） | **本文**，`Type: incident` | 走 `spec/ci_cd/ci-cd-guide.md` 的热修链路 |
| 设计本身错了（原设计就不该这样） | 设计仓改设计，项目仓计划转 `Blocked` | `analysis.md` 结论写 `design-gap`，**不在项目仓打补丁** |
| 不是缺陷，是理解偏差 | 结论写 `not-a-bug`，目录 `Archived` | 写清"为什么这是预期行为" |
| 只是慢、不报错 | `Type: feature`（性能优化） | 没有"错"，只有"不够好" |
| 依赖升级导致的破坏 | `Type: bugfix` + 依赖回归 | 根因写清是版本行为变化还是用法错 |

分界原则：**"预期"是谁定的？** 设计/需求定的 → 代码错，本文修；设计本身没定或定错了 → 回设计仓。

---

## 1. 编号与目录

### 1.1 编号

| 字段 | 格式 | 说明 |
| --- | --- | --- |
| `Issue` | `BUG-YYYYMMDD-NN` | 仓库内自建，`NN` 为当日递增两位序号；与回归登记表的 `id` **完全一致** |
| `External` | 外部单号或链接，无则 `none` | Jira / 禅道 / GitHub Issue |

- MUST 一个缺陷一个编号，编号一旦写进 `analysis.md` 与 `registry.yaml` 就不再改。
- MUST 同一现象由不同人报两次时合并为一个编号，在 `analysis.md` 的「现象-证据」里记另一个来源。
- MUST NOT 用计划 id 当缺陷编号（两者生命周期不同，混用后无法按缺陷查历史）。

### 1.2 目录

复用主流程的计划目录，**不新建 `tasks/bugs/`、`tasks/issues/`**：

```text
tasks/plans/<topic>/<YYYYMMDD>-fix-<slug>-NN/
├── analysis.md     # 本文第 3 章模板；缺陷/事故类必填
├── plan.md
├── STATUS.md
├── audits/
└── artifacts/
```

- MUST `<topic>` 用**受影响的模块或领域**（`orders`、`auth`、`billing`），不用 `bug`、`fix`、`issues` 这类来源词。理由：按模块翻历史才能看到"这个模块反复出什么问题"；按来源分目录等于把同一模块的问题散到各处。
- MUST `plan-id` 前缀为 `fix-`；事故为 `hotfix-`。
- MUST NOT 为缺陷单独维护一套状态机或提交规则。

---

## 2. 七步流程

| 步 | 动作 | 产物 | 出口条件 |
| --- | --- | --- | --- |
| 0 登记 | 建目录、写 `STATUS.md`、`analysis.md` 骨架 | 一句话现象 + 来源 + 环境 | 现象能用一句话说清 |
| 1 确认 | 复现：环境、步骤、期望 vs 实际、日志、影响面 | `analysis.md` 的「现象」「影响面」 | 结论四选一已写 |
| 2 根因 | 现象 → 直接原因 → 根本原因，全部带证据 | `analysis.md` 的「根因」 | 满足第 4 章三条判据 |
| 3 计划 | 修复计划：范围含用例文件，验收含红→绿 | `plan.md` | 验收标准可判定；`Audit` 档位已定 |
| 4 实施 | 先写失败用例 → 留红证据 → 改代码 → 跑绿 | `artifacts/red.log`、`green.log` | 两份输出都在 |
| 5 测试 | 按影响面选层跑；失败回第 4 步 | 各层输出进 `artifacts/` | 该影响面要求的层全绿 |
| 6 登记 | `docs/regression/registry.yaml` 加条目 | 一条记录，`reverse_verified: true` | 反向验证已做 |
| 7 提交 | `fix(<plan-id>)`，body 写根因 | 一次提交（`spec/git/commit-guide.md`） | CI 绿、可独立 revert |

`Issue` 的 `NN` 不靠记忆：扫 `tasks/plans/*/*/analysis.md` 与 `docs/regression/registry.yaml`，取**当日**已用最大序号 + 1（两位补零）；扫不到从 `01` 起。编号写入后不再改，与实际发现时间不一致也保持原编号。

第 0～2 步发生在 `Planned` 状态内（`STATUS.md` 的 `Next Action` 写"确认是否存在""定位根因"），第 4～5 步的循环留在 `In Progress` 内。**全程不新增状态。**

---

## 3. `analysis.md` 模板（强制）

```md
# 问题分析：<一句话现象>

## Metadata

- Issue: BUG-20261115-01
- External: none
- Type: bugfix
- Severity: <critical|high|medium|low>
- Found At: 2026-11-15
- Reporter: <谁发现的>
- Affected: <模块 / 接口 / 页面>
- Env: <版本或 commit> / <环境：本地|staging|production>

## 现象

- 期望：
- 实际：
- 复现步骤：
  1.
  2.
- 复现率：必现 / 偶发（N/10）
- 证据：<日志片段、trace id、请求响应、截图路径>

## 影响面

- 用户影响：
- 数据影响：<是否已产生错误数据；要不要单独修数据>
- 范围：<单租户 / 全量；单接口 / 全链路>

## 根因

- 直接原因：
- 根本原因：
- 证据：<文件:行号、SQL、提交 SHA、日志>
- 为何现有测试没抓到：

## 结论

- 结论：`confirmed` | `not-a-bug` | `needs-info` | `design-gap`
- 判定依据：
```

- MUST 结论只选一个，不写"疑似""应该是"。
- MUST `confirmed` 才能进第 3 步；`needs-info` 只写"缺什么信息、找谁要"，不得开始猜测。
- MUST `not-a-bug` 时：目录保留，`STATUS.md` 转 `Archived`，**不建 `plan.md`**，在 `analysis.md` 结论里写清"为什么这是预期行为"。半年后再有人提，直接看这份文件。
- MUST `design-gap` 时：目录保留，`STATUS.md` 转 `Blocked`（不是 `Archived`——它在等设计仓改完），**不建 `plan.md`**，`analysis.md` 写清设计哪一条错了、要提什么 issue；解除条件是"设计仓合入且 `design.lock` 更新"，解除后重新走第 1 步确认。
- MUST 「为何现有测试没抓到」必填。它决定第 5 步要补哪一层用例；写"测试没覆盖到"不算答案，要说清"哪一层本该覆盖、为什么漏了"。

---

## 4. 根因的三条判据

三条全部满足才算根因确认，缺一条就不许进第 3 步：

1. **能指到具体位置**：文件与行号、配置项、SQL、或具体的数据记录。写"某处逻辑有问题"不算。
2. **能解释复现条件**：为什么只在特定输入 / 并发 / 特定数据下出错。解释不了，说明根因还差一层。
3. **能解释为什么测试没抓到**：是没写、写错了断言、还是测试环境与真实环境有差异。

- MUST NOT 用"可能是并发问题""可能是缓存"这类表述进入修复计划。要么给出证据升级为确认，要么留在第 2 步继续调查。
- MAY 在第 2 步做一个一次性验证实验（打日志、复现脚本、SQL 查询）；实验代码**不进提交**，结论写进 `analysis.md`。

---

## 5. 修复计划：与功能计划的四处差异

计划模板本身不变（`spec/plans/plan-writing-guide.md` 第 2 章），四处内容必须不一样：

| 项 | 缺陷修复的要求 |
| --- | --- |
| `Metadata.Type` / `Issue` | `bugfix` 或 `incident`；`Issue: BUG-…` |
| `验收标准` | 必须写成"复现用例从失败变通过"+"同模块回归通过"，不能写"功能恢复正常" |
| `范围-改` | 必须包含用例文件与 `docs/regression/registry.yaml`；漏了这两项就是范围不全 |
| `回滚` | 除代码回滚外，写清**已产生的错误数据**怎么处理（修复 / 保留 / 单独脚本） |

- MUST `验收标准` 里点名那条用例的路径与节点名，让第三人能直接跑。
- MUST `Audit` 档位按 `spec/plans/plan-audit-guide.md` 0.2 判：线上事故、鉴权、金额、不可逆数据一律 `L2`；普通缺陷默认 `L1`。
- 唯一例外：**单模块、已有测试覆盖、且不命中 0.2 任何 `L2` 项**的缺陷，若走不审入口，可写 `none`，但必须在「决策记录」写一句"按本文默认应为 L1，因 <具体理由> 未审"。其余情形降档一律视为违规。

---

## 6. 实施：先红，再绿，再反向验证

顺序不能变。反了就等于没有回归保护——你先改代码，永远能写出一个"刚好通过"的用例。

```bash
# 1) 先写用例（可以只写一个，先让它失败）
#    用例名带缺陷号，见 spec/testing/regression-testing-guide.md 第 4 章

# 2) 跑一次，必须看到失败；把输出原样存下来
uv run pytest -q tests/modules/orders/test_regression.py -k 20261115 \
  > tasks/plans/orders/20261115-fix-xxx-01/artifacts/red.log 2>&1 || true

# 3) 改代码

# 4) 跑到绿，存一份
uv run pytest -q tests/modules/orders/test_regression.py -k 20261115 \
  > tasks/plans/orders/20261115-fix-xxx-01/artifacts/green.log 2>&1

# 5) 反向验证：把修复暂存起来，只留用例，确认它又变红
git stash push -- backend/app/modules/orders/service.py
uv run pytest -q tests/modules/orders/test_regression.py -k 20261115 \
  > tasks/plans/orders/20261115-fix-xxx-01/artifacts/reverse-verify.log 2>&1 || true
git stash pop
```

- MUST 红、绿、反向验证三份输出都进 `artifacts/`。没有 `red.log` 就无法证明"这个用例真的能抓到这个缺陷"。
- MUST 反向验证后把结论写进 `plan.md` 的「决策记录」：`反向验证：stash 修复后用例重新失败（YYYY-MM-DD）`。
- MUST NOT 先改代码再补用例；MUST NOT 改已有用例的断言让缺陷"消失"。
- MUST 偶发缺陷写清复现率与触发条件。用例要么能稳定构造条件，要么循环跑 N 次（N 写进用例注释）；**不许**用 `sleep` 或提高重试次数来"稳定"。

---

## 7. 测试循环：按影响面定要跑哪几层

| 改动影响面 | 最低要求 |
| --- | --- |
| 单个函数 / 单个接口 | 该模块单测 + 该接口的契约断言 |
| 跨模块，或改了公共层、中间件、鉴权 | 全部单测 + 涉及模块的接口测试 |
| 表结构 / 数据修复 | `alembic upgrade head` + `downgrade -1` + **有数据**的迁移演练 |
| 前端行为 | 该组件测试 + 该页面的 E2E |
| 权限、金额、不可逆操作 | 上面各项 + E2E + 拒绝路径的副作用断言（`spec/testing/backend-testing-guide.md` 5.4） |

- MUST 失败就回第 6 步改，不许通过放宽断言、加 `skip`、删用例来收口。
- MUST 循环只在 `In Progress` 内进行，不新增状态、不新建计划目录。
- MUST 同一缺陷连续两次修不好时，停手回到第 2 步重做根因分析——连续失败通常说明根因是错的，不是修得不够。

---

## 8. 回归登记（必须）

在 `docs/regression/registry.yaml` 加一条，字段定义见 `spec/testing/regression-testing-guide.md` 第 5 章，本文只补三条：

- MUST `id` 与 `analysis.md` 的 `Issue` **完全一致**，包括前缀与日期。
- MUST `root_cause` 与 `analysis.md` 的「根本原因」一致（一句话）。两处不一致说明分析或计划有一个是临时编的。
- MUST `reverse_verified: true` 且写 `reverse_verified_at`。做不到就写 `false` 并在 `note` 说明，同时该条目 `status: pending`，下次发布前必须补。

---

## 9. 提交

```text
fix(20261115-fix-cart-total-rounding-01): 购物车金额不再出现 0.01 误差

根因：金额先四舍五入再累加，导致分位误差累积。

Issue: BUG-20261115-01
Refs: design@none
Plan: tasks/plans/orders/20261115-fix-cart-total-rounding-01/
Test: pytest tests/modules/orders/test_regression.py -k 20261115 — red → green，反向验证通过
```

- MUST `subject` 写**现象消失**（"不再出现 0.01 误差"），不写"修改 rounding 逻辑"。
- MUST `body` 一行写根因；根因超过一行说明还没定位清楚。
- MUST `Issue:` trailer 带缺陷号，让提交能反查到 `analysis.md` 与 registry。
- MUST `incident` 走 `spec/ci_cd/ci-cd-guide.md` 的热修链路，但测试与登记要求不降。

---

## 10. 一次没修好怎么办

| 情形 | 处理 |
| --- | --- |
| 修完发现还有关联缺陷（同一根因的另一处） | 在**同一计划**里扩范围，更新「范围」与「决策记录」；不新建计划 |
| 换个思路重做（原方案行不通） | 新开计划 `<同日>-fix-<slug>-02`，`前置条件` 写 `Requires: <旧 plan-id>`；旧计划转 `Archived` 并写明"被 X 取代、失败原因是 Y" |
| 根因判断错了 | 回第 2 步重写 `analysis.md` 的根因，**保留**原判断并标注"已推翻，原因…"；不要删掉错误结论 |

- MUST NOT 在原计划里删掉失败的步骤与决策。失败路径是下一次判断的依据。
- MUST FOR 两次未修好 → 第三次动手前先找人复核 `analysis.md`（相当于对分析做一次审核，规则见 `spec/plans/plan-audit-guide.md`）。

---

## 11. 禁止事项

- MUST NOT 不写 `analysis.md` 直接改代码。
- MUST NOT 用"可能是""疑似"当根因进入修复。
- MUST NOT 跳过失败用例（`red.log` 缺失即为跳过）。
- MUST NOT 改测试断言、加 `skip`、删用例来让缺陷"消失"。
- MUST NOT 用 `try/except: pass`、吞异常、加默认值掩盖缺陷。
- MUST NOT 把 `design-gap` 当普通缺陷在项目仓打补丁——那会让设计与实现的分歧永久留在代码里。
- MUST NOT 漏登记 registry，或把 `reverse_verified` 写成没做过的 `true`。
- MUST NOT 事故修复绕过热修链路，或以"紧急"为由跳过测试与登记。
- MUST NOT 为缺陷新建 `tasks/bugs/`、`tasks/issues/` 这类按来源分的目录。

---

## 12. 检查清单

**登记与确认（第 0～2 步）**

- [ ] 编号 `BUG-YYYYMMDD-NN` 已定，`analysis.md` 的 `Metadata` 填全。
- [ ] 复现步骤能被第三个人照着走通，期望与实际写具体。
- [ ] 影响面写了用户影响与**数据影响**。
- [ ] 根因满足三条判据；「为何现有测试没抓到」已写。
- [ ] 结论四选一已写；`needs-info` 写清缺什么、找谁。

**计划（第 3 步）**

- [ ] 验收标准是"用例由失败转通过 + 同模块回归"，点了名到具体用例路径。
- [ ] 范围包含用例文件与 `registry.yaml`。
- [ ] 回滚写了错误数据怎么处理。
- [ ] `Metadata.Type` / `Issue` / `Audit` 已写。

**实施与测试（第 4～5 步）**

- [ ] `artifacts/` 有 `red.log`、`green.log`、`reverse-verify.log`。
- [ ] 反向验证结论已写进「决策记录」。
- [ ] 影响面要求的层全绿。

**提交（第 6～7 步）**

- [ ] `registry.yaml` 条目 id 与 `analysis.md` 一致，`root_cause` 一致。
- [ ] 提交信息 `fix(<plan-id>)`，带 `Issue:` / `Plan:` / `Test:`。
- [ ] 计划目录与代码同一次提交，可独立 `git revert`。
