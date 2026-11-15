---
version: 5.0.0
last_updated: 2026-11-15
---

# 回归测试规范（Regression Testing）

> 本章的"回归"指**可追溯、可单独选出、能证明抓得住原缺陷**的用例体系，不是"全部测试再跑一遍"。全量重跑见 `spec/testing/README.md` 第 2 节。

---

## 1. 定义与三个必要条件

回归用例 = 一条**带来源标识、能独立选出、且在修复前会失败**的用例。三个条件缺一不可：

| 条件 | 判定方式 | 不满足的后果 |
| --- | --- | --- |
| 可选出 | `pytest -m regression` / `vitest -t regression` / `playwright --grep @regression` 能精确命中 | 发布前无法单独跑回归集，等于没有 |
| 可追溯 | `docs/regression/registry.yaml` 有对应条目，能从用例反查到缺陷/事故编号 | 半年后没人知道它在防什么，会被当冗余删掉 |
| 能失败 | 在修复前的代码上跑过一次，确认失败原因就是该缺陷（第 3 节） | 可能永远为真，提供零保护 |

与"全量测试"的区别：

| | 回归集 | 全量测试 |
| --- | --- | --- |
| 性质 | 存量资产，随时间累积 | 代码快照，随重构变化 |
| 来源 | 具体缺陷、事故、契约变更 | 需求与现有实现 |
| 能否删除 | 只能走第 8 节的退役流程 | 被测代码消失即随之消失 |
| 跑法 | 发布前必跑，且按条目可点名 | 按 README 第 2 节分层跑 |

---

## 2. 四类来源

回归集只从下面四类事件新增。**"我觉得这里容易错"不是来源**——那写普通测试。

| 来源 | 触发物 | 用例落点 | 登记时要写清楚 |
| --- | --- | --- | --- |
| 缺陷修复 | 缺陷单 / issue | 能复现该缺陷的**最低层** | `root_cause` + 反向验证日期 |
| 线上事故 | 事故单 / 回滚记录 | 事故暴露的接口 + 对应监控项的断言 | `id` 用事故单号、`source: incident`，`note` 记回滚与恢复时长 |
| 行为变更 | 推翻旧行为的需求单 | 旧行为所在位置的新断言 | `source: behavior-change`，`note` 写旧行为为何被推翻 |
| 契约 / 数据变更 | 接口或表结构变更 | 契约快照 + 迁移升降级（第 7 节） | `source: contract`，`note` 写基线文件与变更点 |

规则：

- MUST 一条缺陷至少一条回归用例；跨栈缺陷（后端返回错 + 前端展示错）两侧各一条，登记在同一条记录下。
- MUST 线上事故即使已有 E2E，也要补一条**最低层**用例。E2E 只在夜间和发布前跑，不能当第一道防线。
- MUST NOT 把"环境导致的偶发失败"当缺陷入库；按 README 第 3 节 flaky 处理。
- SHOULD 同类缺陷累计 3 次以上时，增加一条"类别条目"，并把防线前移到设计层（如统一在 base schema 加校验），用一条参数化用例覆盖整类输入。

### 2.1 兼容性回归要写明"谁在依赖它"

保留旧行为的用例，最容易在半年后被当成"过时的测试"删掉。防这个的办法是**在 docstring 里点名受益方**：

```python
async def test_list_keys_without_member_team_ids_keeps_old_behavior():
    """未传 member_team_ids 时保持旧的不过滤行为。

    受益方：内部监控（直接调用 _list_key_helper）与 v1 客户端。
    何时可删：v1 客户端下线且监控改造完成后。
    """
```

- MUST 兼容性用例写明"谁依赖它"与"何时可以删"。
- MUST NOT 只写"兼容旧版本"这种无法判断时效的说明。

---

## 3. 缺陷修复的强制时序

修任何缺陷都按这个顺序，不允许跳步：

1. **写用例**：放在能复现该缺陷的最低层。
2. **反向验证**：在**修复前**的代码上跑，确认失败，且失败信息对得上缺陷现象。
3. **改代码**：让用例转绿。不改断言。
4. **跑同模块全部测试**：确认没有引入新失败。
5. **登记**：写 registry 条目、打 `regression` 标记、名称带缺陷号（第 4 节）。

反向验证的做法（任选其一，命令改路径即可用）：

```bash
# 方式一：改动还没提交，暂存后重跑
git stash push -- app/modules/orders/service.py
uv run pytest tests/modules/orders/test_regression.py -q   # 此时必须失败
git stash pop

# 方式二：已在分支提交，检出父提交里的被改文件
git checkout HEAD~1 -- app/modules/orders/service.py
uv run pytest tests/modules/orders/test_regression.py -q   # 此时必须失败
git checkout HEAD -- app/modules/orders/service.py

# 方式三：缺陷来自依赖，锁回旧版本跑一次
uv run --with 'some-lib==1.2.3' pytest tests/modules/orders/test_regression.py -q
```

- MUST 把反向验证的**日期**写进 registry 的 `reverse_verified_at`，不写"已验证"三个字。
- MUST 无法反向验证时（只在生产数据上出现、依赖无法降级），登记 `reverse_verified: false` 并在 `note` 写原因，该条目按第 9 节的"弱回归"处理。
- MUST NOT 先改代码再补测试。补出来的测试只证明"当前实现自洽"，不证明它抓得住该缺陷。

### 3.1 用例里保留原始复现条件

最有价值的回归用例保留的是**当时的输入形状**，不是编号：

```python
@pytest.mark.regression
async def test_regression_issue_1234_zero_quantity_order_rejected(client):
    """缺陷 #1234：数量为 0 的订单被接受并生成 0 元支付单。

    原始复现：前端把空输入序列化成 0 而非 null，走的是 qty=0 分支。
    """
    resp = await client.post("/api/v1/orders", json={"sku": "A-1", "qty": 0})
    assert resp.status_code == 422, f"期望 422，实际 {resp.status_code}"
```

- MUST 保留触发缺陷的关键输入（边界值、异常组合、真实 payload 结构），不"简化成更好写的形状"。
- MUST NOT 因为"输入太怪"而删掉原缺陷的边界值；那正是它要防的东西。

---

## 4. 标记与命名

| 层 | 标记 | 位置 | 命名 |
| --- | --- | --- | --- |
| 后端 | `@pytest.mark.regression` | 单模块：`tests/modules/<m>/test_regression.py`；跨模块：`tests/regression/` | `test_regression_issue_1234_<触发条件>_<期望>` |
| 前端单测 | `describe('[regression] #1234 <行为>')` | 与被测文件同目录 | `it('<条件> 时 <期望>')` |
| E2E | `@regression` tag | `frontend/e2e/*.spec.ts` | `test('@regression #1234 <行为>')` |

规则：

- MUST `regression` 标记已在 `pyproject.toml` 注册；`--strict-markers` 会让漏注册的标记直接报错。
- MUST 同一缺陷多条用例时用**触发条件**区分（`..._zero_quantity_...`、`..._negative_quantity_...`），禁止 `_2`、`_3`。
- MUST 用例名里的编号去分隔符（`INC-2026-03-11` → `inc_20260311`），docstring 里写**完整单号**。第 12 节的校验按"完整单号 / 去前缀编号 / 纯数字"三者之一在文件中命中即通过。
- MUST E2E 的 tag 以 `@` 开头且完整可 grep：`--grep @regression` 命中全部，`--grep "@regression #1234"` 命中单条。
- MUST NOT 一条用例同时断言两个不同缺陷：失败时无法定位是哪条防线破了。
- MUST NOT 为回归单开 `tests/regression_all/`、`e2e/regression/` 这类平行目录；回归是标记，不是目录层级。

---

## 5. 回归登记表

用例代码之外，必须有一份**人能读、机器可校验**的登记表：`docs/regression/registry.yaml`（`docs/regression/`，跨前后端唯一一份）。

为什么放根目录而不分前后端：一条缺陷常跨栈。分两份会出现两个 id 指向同一缺陷，追溯时对不上。

字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | 缺陷单号原样（本项目为 `BUG-YYYYMMDD-NN`，规则见 `spec/workflow/bugfix-workflow-guide.md` 1.1；外部单号 `#1234` / `INC-2026-03-11` 亦可），与用例里的标识一致 |
| `title` | 是 | 一句话现象：什么条件下错了。不写修复方案 |
| `severity` | 是 | `critical` / `high` / `medium` / `low`，决定第 10 节的阻断级别 |
| `source` | 是 | `defect` / `incident` / `behavior-change` / `contract` |
| `found_at` | 是 | 发现日期 `YYYY-MM-DD` |
| `fixed_in` | 否 | 首次修复所在 tag 或 commit；未发布可留空 |
| `root_cause` | 是 | 一句话根因，供第 8 节判断能否合并或退役 |
| `cases` | 是 | 用例清单，每项 `layer` + `path`（`文件::节点`） |
| `reverse_verified` | 是 | `true` / `false`；`false` 必须在 `note` 写原因 |
| `reverse_verified_at` | 条件 | `reverse_verified: true` 时必填，`YYYY-MM-DD` |
| `status` | 是 | `active` / `pending` / `retired` |
| `note` | 条件 | 弱回归原因、数据来源、退役理由与替代条目 |

完整示例：

```yaml
# docs/regression/registry.yaml
# 一条记录 = 一个缺陷/事故，可挂多条用例（前后端各一条）。
- id: BUG-1234
  title: 数量为 0 的订单被接受并生成 0 元支付单
  severity: high
  source: defect
  found_at: 2026-03-11
  fixed_in: v1.4.2
  root_cause: 校验只在 Pydantic schema 做，service 内部直接调用时绕过
  cases:
    - layer: backend
      path: backend/tests/modules/orders/test_regression.py::test_regression_issue_1234_zero_quantity_order_rejected
    - layer: e2e
      path: frontend/e2e/orders.spec.ts::@regression #1234
  reverse_verified: true
  reverse_verified_at: 2026-03-12
  status: active

- id: INC-2026-03-11
  title: 发布后登录接口 500，JWT 密钥轮换未重启
  severity: critical
  source: incident
  found_at: 2026-03-11
  fixed_in: v1.4.3
  root_cause: 密钥从环境变量读取后缓存在模块级单例，轮换后不失效
  cases:
    - layer: backend
      path: backend/tests/integration/test_regression.py::test_regression_inc_20260311_key_rotation_takes_effect
  reverse_verified: true
  reverse_verified_at: 2026-03-13
  status: active
  note: 事故期间人工回滚一次，恢复时间 11 分钟
```

规则：

- MUST 新增回归用例与 registry 条目在**同一个 PR** 里，不拆开提交。
- MUST 一条记录可挂多条用例；禁止一个用例一条记录（否则同一缺陷出现多个 id）。
- MUST `status: pending` 只用于"用例已写、反向验证未做"，**两周内**必须转 `active` 或删除。
- MUST NOT 修改已发布的 `id`（会切断追溯）；需要重新编号时新增条目并在 `note` 引用旧 id。
- MUST NOT 在 registry 里贴大段日志或 diff；它是指引，不是证据仓库。证据放计划的 `artifacts/`。
- SHOULD 单条记录不超过 12 行，`title` 与 `root_cause` 都写成一句人话。

---

## 6. 回归范围：三档与全量触发

| 档位 | 触发时机 | 范围 | 命令 |
| --- | --- | --- | --- |
| 改动相关 | 保存 / 提交前 | 被改动模块的单测 + 接口测试 | `pytest tests/modules/<m>` / `npx vitest related --run <文件>` |
| 模块级 | PR | 该模块全部测试 + 依赖它的上层测试 + 该模块的回归条目 | `pytest tests/modules/<m> tests/integration -m "not slow"` |
| 全量冒烟 | 合并主干 / 发布前 | 全部单测 + **全部回归集** + 核心 E2E + 迁移升降级 | README 第 2 节命令表 |

升级判定：改动波及 import 关系、公共工具、配置默认值 → 升一档；只改文案与样式 → 停在改动相关。拿不准时按高的一档跑，代价是几分钟。

以下变更**不允许**用"改动相关"档位放行：

1. **数据库迁移**：`upgrade → downgrade → upgrade` + 受影响模块的 repository 测试。
2. **依赖升级**（框架、ORM、UI 库大版本）：全部单测 + 全部 E2E。
3. **鉴权与权限模型**：登录、越权、会话过期全部用例 + 权限边界 E2E。
4. **路由与接口契约变更**：全部接口测试 + 前端类型检查 + 涉及该接口的 E2E + 契约快照比对。
5. **环境变量与配置默认值变更**：启动冒烟 + 受影响功能主路径。
6. **公共组件 / 工具函数改动**：引用该文件的全部测试（后端按模块目录跑，前端 `vitest related <文件>`）。
7. **回归集自身被修改**（新增/改断言/改基线）：本档位无效，必须跑全量回归集，否则改了防线却不知道其它防线还在不在。

---

## 7. 回归基线：契约、快照、迁移、数据

有一类回归不靠"写用例"，靠**比对基线**。基线入库、入库即受版本控制，改动必须显式出现在 diff 里。

### 7.1 接口契约基线

```bash
# 生成并入库（PR 中契约变化必须可见）
uv run python -c "import json,sys; from app.main import app; \
  json.dump(app.openapi(), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)" \
  > docs/openapi.json

# 回归判据：生成结果与入库版本一致
git diff --exit-code docs/openapi.json

# 前端类型跟随契约，防止两边漂移
npx openapi-typescript docs/openapi.json -o src/types/api.d.ts
git diff --exit-code src/types/api.d.ts
```

- MUST `docs/openapi.json` 与前端 `api.d.ts` 纳入版本控制，且由上面两条命令生成，禁止手改。
- MUST 生成器必须**可重现**：键排序、缩进固定、描述文本归一化；否则 diff 会随机红，人就会开始无视它。
- SHOULD 用 `oasdiff breaking` 在 PR 上单独判"是否破坏性变更"，把结果贴进 PR 描述。

### 7.2 前端快照基线

只在组件结构稳定后启用（规则见 frontend 规范第 4 节）。判据是"`git diff` 里没有快照文件的意外变化"，不是"测试是绿的"。

### 7.3 迁移基线

空库升降级已在 `spec/alembic/alembic-guide.md` 第八章规定。回归再加两条：

```bash
# (a) 模型与迁移是否同步（有模型改动但没生成迁移 → 失败）
uv run alembic upgrade head
uv run alembic check

# (b) 有数据演练：升级后关键表行数与校验和不变；降级再升级不丢列、不丢索引
uv run alembic upgrade head
psql "$APP_TEST_DATABASE_URL" -f backend/tests/fixtures/seed-baseline.sql
uv run alembic downgrade -1 && uv run alembic upgrade head
uv run pytest tests/modules/<受影响模块> -q
```

- MUST NOT 用"删掉迁移目录让检查变绿"处理失败；空迁移目录本身要判红。

### 7.4 数据回放

适用于报表、金额、税费、聚合、结算这类"算错了但界面正常"的逻辑。

- MUST 用脱敏样本 `backend/tests/fixtures/golden/<场景>.jsonl` 作为输入，输出与 `golden/<场景>.expected.json` 全字段比对。
- MUST 样本来自真实结构（字段类型、空值、边界值齐全），不是手工编的 3 条。
- MUST 比对失败时先判定是逻辑错还是预期变更（第 11 节），不直接重生成 `.expected.json`。
- SHOULD 样本每季度从真实数据重新采样一次。**基线不会自己过期，就会变成"永远正确"的化石**——上游数据分布变了、样本还停在两年前，测试会一直绿。

### 7.5 golden 文件只能用于纯函数

- MUST 只对"输入 → 输出确定"的对象用 golden 文件（格式化器、报表 builder、代码生成器、序列化）。
- MUST NOT 把整个 HTTP 响应冻成 golden 文件；HTTP 层用字段级断言，必要时用少量"特征化测试"（characterization）锁住重构前行为，并在注释里写明"这是当前行为，不是我认为正确的行为"。

---

## 8. 用例腐化与退役

回归用例会**在保持绿色的同时失去保护力**，这是回归体系最常见的失效方式。

| 腐化表现 | 发现手段 |
| --- | --- |
| 重构后不再走原路径，断言照样通过 | 季度抽检：对 `critical` 条目做一次反向验证（第 3 节方式二） |
| 关键边界被 mock 掉 | review 时看 mock 位置；该行在覆盖率报告里显示未执行 |
| 上游行为变了，断言变成"描述错误现状" | 断言失败但业务确实变了 → 走第 10 节判定，不是直接改绿 |
| 一直绿但没人知道防什么 | registry 条目缺失或 `title` 空泛（第 12 节校验会拦） |

节奏：

- MUST 每季度对 `severity: critical` 的 `active` 条目做**反向验证抽检**，抽 20%（不少于 3 条），结果记入季度回归报告；不通过的条目降级为 `pending` 并限期修。
- SHOULD 金额、权限、迁移等核心模块引入变异测试：`uv run --with mutmut mutmut run --paths-to-mutate app/modules/orders`。存活的变异体说明测试抓不住。
- SHOULD 跟踪"回归缺陷重开率"：同一现象修复后 90 天内被再次报出 / 同期修复缺陷数。> 5% 说明回归用例只修了表面（通常只断言了状态码，没断言数据状态）。

退役条件（满足任一即可提出）：

1. 功能已下线（路由、页面删除）。
2. 缺陷类别被结构性消除（如统一校验器替代逐点校验），且有覆盖该类的通用用例。
3. 与另一条用例完全重复（保留覆盖更深的那条）。

流程：

- MUST registry 改 `status: retired`，`note` 写退役理由与替代条目，**同一个 PR 内**删除用例代码。
- MUST NOT 只删用例代码而留下 registry 条目（第 12 节校验会报"节点未收集到"）。
- MUST NOT 未经 review 退役 `critical` 条目，至少一人确认。

---

## 9. 手工回归

有些回归无法自动化，必须承认并管理，而不是假装它不存在。

| 场景 | 为什么不能自动 |
| --- | --- |
| 布局、视觉、字体截断 | 断言成本高于人工目检 |
| 第三方回调（支付、短信、邮件） | 真实回调不可在 CI 造 |
| 运维操作（备份恢复、证书轮换、磁盘扩容） | 涉及环境与权限 |
| 真实支付 / 真实资金流 | 不能用测试账号替代 |

清单写法（放计划目录 `tasks/plans/<topic>/<plan-id>/artifacts/`，随该次修复一起提交）：

```markdown
### MR-01 订单导出 Excel 表头顺序
- 前置：账号有导出权限，存在 ≥ 2 条订单
- 步骤：订单列表 → 导出 → 打开文件
- 期望：列顺序为 订单号 / 客户 / 金额 / 状态；金额两位小数
- 证据：`artifacts/MR-01-export.xlsx`
```

- MUST 每条含前置、步骤、期望、证据四段，缺一段则不可执行。
- MUST 记录执行人、日期、环境（分支 + digest），否则下次无法判断结果是否适用。
- MUST NOT 用"看起来正常""功能可用"作为结论。
- MUST `reverse_verified: false` 的弱回归条目，在每次发布检查中由人手工执行一次并留证。

---

## 10. 红灯处置与放行

| 级别 | 判定 | 处置 |
| --- | --- | --- |
| P0 | `critical` 条目失败、核心 E2E 失败、迁移升降级失败 | 阻断合并与发布，当场修 |
| P1 | `high` / `medium` 条目失败 | 阻断发布；允许继续合并其它 PR，但 24 小时内修完 |
| P2 | `low` 条目失败，或已确认的基线预期变更 | 记录 issue，可放行，发布说明里列出 |

- MUST 发布前产出 `artifacts/regression-<version>.md`，含：registry 校验结果、执行命令与耗时、条目数（active / critical）、失败项与定级、手工项执行记录、弱回归条目结果。
- MUST 放行例外只有一种情形：相关功能开关已关闭或路径不可达。即便如此也要开 issue、写恢复日期、在发布说明标注、两周内复核；批准人写入发布记录。
- MUST NOT 通过下调级别来放行（P0 改成 P2 不是修复）。

---

## 11. 回归中的禁止行为

- MUST NOT 修改断言使其通过。先判"实现错了"还是"期望过时了"：前者改代码，后者改测试并在 PR 说明原因。
- MUST NOT 删除、`skip`、`xfail` 一条失败的回归用例来让流水线变绿。
- MUST NOT 用 `xfail(strict=False)` 让回归用例永久豁免；确需暂缓就 `skip` + 缺陷单 + 到期日。
- MUST NOT 放宽断言范围（`==` 改 `in`、精确值改 `is not None`）当作修复。
- MUST NOT 重新生成快照或契约基线来"修复"回归失败，除非已确认输出变化是预期的，且 diff 被人看过。
- MUST NOT 新增带 `regression` 标记的用例却不加 registry 条目（第 12 节校验会阻断）。
- MUST NOT 让 `retired` 条目继续留在 CI 执行集合里。

---

## 12. 命令与产物

```bash
# 1) 登记表一致性（CI 必跑，PR 与发布前各一次）
uv run pytest -m regression --collect-only -q | grep '::' > /tmp/regression-collected.txt
uv run python scripts/check_regression_registry.py --collected /tmp/regression-collected.txt

# 2) 执行回归集
uv run pytest -m regression -q
npx vitest run -t regression
npx playwright test --grep @regression

# 3) 契约回归
git diff --exit-code docs/openapi.json
git diff --exit-code src/types/api.d.ts

# 4) 迁移回归
uv run alembic check

# 5) 抽查单条（定位失败原因）
uv run pytest "tests/modules/orders/test_regression.py::test_regression_issue_1234_zero_quantity_order_rejected" -vv
```

产物：

| 产物 | 位置 | 何时产生 |
| --- | --- | --- |
| 登记表 | `docs/regression/registry.yaml` | 常驻版本控制 |
| 回归报告 | `artifacts/regression-<version>.md` | 每次发布前 |
| 失败证据 | JUnit XML、`playwright-report/`、`artifacts/` | 失败时 |
| 季度抽检记录 | 回归报告的 `## 抽检` 段 | 每季度 |

校验脚本（放 `scripts/check_regression_registry.py`，需要 `pyyaml`；未装则 `uv add --dev pyyaml`）：

脚本在同目录：`scripts/check_regression_registry.py`（依赖 `pyyaml`；未装则 `uv add --dev pyyaml`）。

```bash
# 1) 收集回归用例节点（后端）
uv run pytest -m regression --collect-only -q | grep '::' > /tmp/collected.txt

# 2) 校验（仓库根执行）
uv run python scripts/check_regression_registry.py --collected /tmp/collected.txt
```

它校验四项，任一项不过即退出码 1（CI 阶段 1 与 `tasks-index.py --check` 并列阻断）：

| # | 校验 | 失败意味着 |
| --- | --- | --- |
| 1 | 结构完整、枚举合法、`id` 不重复 | 登记表本身写坏了 |
| 2 | 每条 `cases.path` 的文件存在 | 用例被删或路径写错 |
| 3 | 缺陷编号出现在对应用例文件里 | 改了用例忘了改表，或反过来 |
| 4 | 后端用例的 pytest 节点确实被收集到 | 用例漏打 `@pytest.mark.regression`，等于没进回归集 |

脚本读的是 `docs/regression/registry.yaml`（与本文同一条路径约定）。字段规则见本章表格，不要照脚本的 `REQUIRED` 集合反推——`reverse_verified_at` 是条件必填，脚本单独校验。

