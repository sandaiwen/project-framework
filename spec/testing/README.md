---
version: 1.0.0
last_updated: 2026-11-15
---

# 测试规范（Testing Specs）

本目录把测试规范拆成**一份索引 + 五份分层规范**。原因只有一个：不同层的测试，工具、运行前提、失败含义都不一样，混在一份文档里时，读的人只能整份读完再自行筛选。

| 文档 | 管什么 | 什么时候读 |
| --- | --- | --- |
| `backend-testing-guide.md` | pytest 配置、目录镜像、fixture 分层、mock 与替身、接口测试、数据库测试、参数化、断言、覆盖率 | 写后端测试、改 `conftest.py`、加接口或仓储逻辑时 |
| `frontend-testing-guide.md` | Vitest + RTL 配置、能测与不能测的边界、组件测试、快照、数据层测试、可访问性 | 写前端测试、改 `vitest.config.mts` 时 |
| `e2e-testing-guide.md` | Playwright 配置、服务编排与探活、造数与清理、选择器与等待、断言、失败产物、行为清单 | 写端到端用例、改 `playwright.config.ts` 时 |
| `regression-testing-guide.md` | 回归三条必要条件、反向验证、登记表、三档范围、基线与契约、腐化与退役、红灯放行 | 修缺陷、发布前、季度抽检时 |
| `test-data-guide.md` | 造数工厂、唯一性、隔离策略、时间与随机、外部依赖替身 | 第一次造测试数据、发现用例互相污染时 |
| 本文件 | 选层判据、目录总览、执行时机、flaky 治理、与计划衔接、跨层清单 | 开始写第一行测试之前 |

不涉及的内容：

- 代码格式、命名、导入、异常写法——见 `spec/python/python-code-style-guide.md`。
- 模块怎么分、类怎么拆——见 `spec/module/module-guide.md`。
- 前端目录、组件边界、取数位置——见 `spec/frontend/frontend-guide.md`。
- 迁移文件怎么写、`upgrade/downgrade` 怎么验证——见 `spec/alembic/alembic-guide.md` 第八章。
- 流水线文件怎么组织、门禁怎么挂——见 `spec/ci_cd/ci-cd-guide.md`；本目录只定义"跑什么、什么算通过"。

已安装的 `testing-py`、`webapp-testing` 技能提供写法与工具细节。**技能与本规范冲突时以本规范为准**：技能面向通用项目，本规范规定这个仓库的目录、命令、门槛与流程。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

---

## 0. 先决定写哪一层

**用最便宜、但仍能抓到该缺陷的那一层。**

按顺序回答，第一个"是"就是答案：

1. 不启动任何进程就能判断对错？→ **单元测试**（backend/frontend）。
2. 要真实 PostgreSQL 才能判断（约束、事务、并发、SQL）？→ **后端集成测试**。
3. 要真实 HTTP 请求才能判断（状态码、schema、鉴权、错误信封）？→ **后端接口测试**。
4. 要浏览器才能判断（路由、RSC 渲染、表单联动、可见性）？→ **E2E**。
5. 只有当某个已修缺陷会再次出现时才需要？→ **回归**（在原层写，另加登记）。

四条判断基准，冲突时取前面的：

1. **能抓到这个 bug 的最便宜那一层**。纯函数能测清的，不写接口测试；接口能测清的，不写 E2E。
2. **测行为，不测实现**。断言"调用方能观察到什么"，不断言"内部调了哪个函数几次"。
3. **测试必须能失败**。没有断言、断言永远为真、把实现重写一遍的用例，一律不算测试。
4. **失败必须指向缺陷位置**。一个用例断言 12 件事，第一个失败会掩盖其余问题。

### 0.1 被测对象 → 层 → 文档

| 被测对象 | 层 | 位置 | 读哪份 |
| --- | --- | --- | --- |
| 纯函数、数据转换、校验规则 | 单元 | `backend/tests/**/test_*.py` | backend |
| service 的协作逻辑（mock 外部边界） | 单元 | 同上 | backend |
| repository / SQL / 事务 | 集成 | `backend/tests/integration/` | backend + test-data |
| HTTP 路由（状态码、schema、鉴权） | 接口 | `backend/tests/**/test_router.py` | backend |
| 前端纯函数、格式化、校验 | 单元 | `frontend/src/**/*.test.ts` | frontend |
| 前端 hooks、同步组件 | 组件 | `frontend/src/**/*.test.tsx` | frontend |
| 跨页面用户流程、async Server Component | E2E | `frontend/e2e/*.spec.ts` | e2e |
| 已修缺陷、事故 | 回归 | 原层 + `regression` 标记 | regression |

### 0.2 三层运行前提

决定"能不能在本地跑"的不是 unit/integration 这种学术分类，而是**运行前提**。本仓库只有三种：

| 前提 | 覆盖范围 | 本地可跑 | 缺条件时 |
| --- | --- | --- | --- |
| 无需外部服务 | 前端单测/组件、后端纯单元 | 是，秒级 | — |
| 需真实 PostgreSQL | 后端集成、接口、迁移 | 是，需 `docker compose up -d db` | **skip 并写明缺什么** |
| 需真实前后端进程 | E2E | 是，需 `build && start` | **fail，不 skip** |

最后一行是刻意的方向差异：单元测试缺依赖可以 skip（跳过是诚实的），E2E 缺依赖必须 fail（跳过会让"什么都没测"看起来像绿）。细节见 e2e 规范第 2 节。

---

## 1. 目录总览

```text
backend/
├── app/
│   └── modules/
│       └── users/
│           ├── router.py
│           ├── service.py
│           └── repository.py
├── tests/
│   ├── conftest.py                    # 全局：engine、db_session、app、client
│   ├── factories.py                   # 造数函数，全项目共用
│   ├── modules/
│   │   └── users/                     # 镜像 app/modules/users/
│   │       ├── conftest.py            # 仅本模块需要的 fixture
│   │       ├── test_service.py
│   │       ├── test_repository.py
│   │       ├── test_router.py
│   │       └── test_regression.py     # 本模块的回归用例
│   ├── integration/                   # 跨模块、真实外部边界
│   └── regression/                     # 需要跨模块复现的回归用例
├── scripts/alembic/                   # 迁移封装脚本（见 alembic-guide）
└── pyproject.toml                      # pytest 与 coverage 配置唯一位置

frontend/
├── src/
│   └── features/
│       └── orders/
│           ├── utils.ts
│           ├── utils.test.ts          # 与被测文件同目录
│           └── components/
│               ├── order-table.tsx
│               └── order-table.test.tsx
├── e2e/
│   ├── fixtures.ts                    # 造数与清理
│   ├── behaviors.yaml                 # E2E 行为清单（分母，见 e2e 规范第 8 节）
│   ├── auth.spec.ts
│   └── orders.spec.ts
├── vitest.config.mts
├── vitest.setup.ts
└── playwright.config.ts

regression/
└── registry.yaml                      # 回归登记表：缺陷/事故 → 用例（跨前后端唯一一份）

scripts/
└── check_regression_registry.py       # 登记表与用例的双向一致性校验
```

要求：

- MUST 后端 `tests/` 镜像 `app/`，找测试时按被测文件路径反推，不做集中堆放。
- MUST 前端测试文件与被测文件同目录，命名 `<被测文件名>.test.ts(x)`。
- MUST E2E 用例只放 `frontend/e2e/`，不放 `src/`（Vitest 会误收集）。
- MUST `e2e/` 与 `src/` 的测试配置互相排除（见 frontend 3.1、e2e 3.1）。
- MUST NOT 为回归单开 `tests/regression_all/`、`e2e/regression/` 这类平行目录；回归是标记，不是层级。

---

## 2. 执行时机与 CI 分层

| 阶段 | 跑什么 | 目标时长 | 失败即阻断 |
| --- | --- | --- | --- |
| 保存 / 提交前 | 受影响模块单测 + lint + 类型检查 | < 60 s | 是 |
| PR | 后端全部单测 + 接口测试 + 前端单测 + 覆盖率门槛 | < 10 min | 是 |
| 合并主干 | 上一档 + 核心 E2E + 回归集 + 迁移升降级 | < 20 min | 是 |
| 夜间 | 全量 E2E + 慢测试（`-m slow`）+ 全量回归集 | 不限 | 否，次日修 |
| 发布前 | 全量冒烟 + 回归集 + 迁移演练 | < 30 min | 是 |

命令总表（uv + npm；用 poetry / pnpm 时按语义替换前半段）：

```bash
# ---------- 后端 ----------
uv run pytest -q                                    # 全部
uv run pytest -q -m "not slow"                      # 跳过慢测试
uv run pytest -q tests/modules/users                # 单模块
uv run pytest -q -m regression                      # 回归集
uv run pytest -q --cov=app --cov-branch --cov-report=term-missing --cov-fail-under=85

# ---------- 前端单测 ----------
npm run test:run
npm run test:coverage
npx vitest related --run src/features/orders/utils.ts   # 改动相关

# ---------- E2E ----------
npm run e2e
npm run e2e:smoke                                       # @smoke
npm run e2e:regression                                  # @regression
npx playwright test e2e/orders.spec.ts --repeat-each=5   # 排查 flaky

# ---------- 类型与静态检查（测试前必过） ----------
uv run mypy app
npx tsc --noEmit
```

规则：

- MUST CI 每一步单独成 job/step，失败能看出是"测试挂了"还是"类型检查挂了"。
- MUST 测试失败时上传 pytest 输出、覆盖率报告、`playwright-report/`、`test-results/`。
- MUST 依赖外部服务（PostgreSQL）的 job 显式声明服务容器与就绪等待，不在测试里重试连接。
- MUST NOT 让 CI 默认跑 `--last-failed`：缓存会让"本地通过、CI 没跑"长期共存。
- MUST NOT 只配了测试命令却不执行。**有配置无执行等于没有门禁**，且会让人误以为已覆盖。
- SHOULD 覆盖率单调不降：单容器全量跑时用 `--cov-fail-under`；一旦按域分片，改为"与基分支比 delta"（分片缺失会让项目级阈值误红）。

---

## 3. 稳定性与 flaky

判定顺序，不要跳步：

1. **是真缺陷吗**：偶发失败常对应竞态、超时、事务边界。先按缺陷处理。
2. **是环境吗**：端口占用、测试库残留、时钟与时区、并行冲突、缺浏览器依赖。
3. **才是测试本身**：等待方式不对、断言了不稳定中间态、依赖执行顺序。

处理规则：

- MUST NOT 用加大 `sleep`、放宽超时、提高重试次数来"修" flaky。
- MUST 等待改为"轮询条件 + 超时上限"，或用框架的自动重试断言。
- MUST 隔离重跑取证据：`pytest tests/x.py::test_y -x -vv`、`npx playwright test e2e/x.spec.ts --repeat-each=5`。
- MUST 修复后在 PR 说明根因，不允许只写"重跑就过了"。
- SHOULD 重跑次数按"外部依赖多少"分档，不设全局大值：纯单元 0~1 次，含外部服务 2 次，含第三方回调 3 次。

### 3.1 skip 与 xfail 的分工

| 场景 | 写法 | 为什么 |
| --- | --- | --- |
| 环境不具备（无 DB、无 key） | `pytest.mark.skipif` + 明确 reason | 诚实跳过；CI 里该 reason 必须出现在汇总中 |
| 已知缺陷、暂不修 | `pytest.mark.xfail(strict=True, reason=...)` | 修好那天会 XPASS → 变红，强制回来删标记 |
| 已修缺陷的防复发 | `regression` 标记 + 登记表 | 见 regression 规范 |
| 就是慢 | `slow` 标记 | 只在夜间跑，不是跳过 |

- MUST NOT 用 `skip` 表达"已知缺陷"。`skip` 会让用例从计数里消失，缺陷随之隐形；`xfail(strict=True)` 保留计数并在修复时报警。
- MUST `xfail` 必须带 `strict=True` 与 `reason`，`reason` 里写缺陷号与"何时可以删"。
- MUST NOT `xfail(strict=False)`：它会把 XPASS 变绿，等于永久豁免。

---

## 4. 与计划、验收标准的衔接

- MUST 计划里的每条验收标准对应一条可执行命令或可观察结果，不写"功能正常"（见 `spec/plans/plan-writing-guide.md`）。
- MUST 计划步骤的"验证"列写具体命令，例如 `uv run pytest tests/modules/users -q`，不写"跑测试"。
- MUST 测试输出、覆盖率报告、E2E 报告、回归报告存入该计划的 `artifacts/`，不在 `plan.md` 里贴大段日志。
- MUST 未执行的测试在 `plan.md` 的执行结果中逐条列出原因（缺环境、缺数据、不在本轮范围）。
- MUST 计划中"回归范围"一栏写清档位（改动相关 / 模块级 / 全量）与触发理由，不写"跑一下相关测试"。
- SHOULD 验收标准优先用测试命令表达；无法自动化的（视觉、体验）写明人工检查方式与判定依据。

---

## 5. 提交前检查清单（跨层）

各层的细项见对应文档末尾；这里是**每次提交都要过一遍**的十条：

- [ ] 新增/修改的行为有对应测试，且放在最便宜的那一层。
- [ ] 新增的测试在改动前会失败（缺陷修复必须反向验证过）。
- [ ] 没有用 E2E 覆盖单测能覆盖的逻辑，也没有用 mock 掩盖真实边界。
- [ ] 断言的是可观察结果，不是内部调用次数、CSS 类名、日志文案。
- [ ] 测试数据唯一且自清理，跑两遍、换顺序都能过。
- [ ] 失败的用例没有用 `skip` / 重试 / 放宽断言处理；已知缺陷用 `xfail(strict=True)`。
- [ ] 覆盖率达标且未用排除项凑数。
- [ ] 回归用例已登记，`check_regression_registry.py` 通过（修缺陷时必查）。
- [ ] 契约基线（`docs/openapi.json`、`src/types/api.d.ts`）没有未提交的变化。
- [ ] 未执行的测试已在报告中如实说明原因。

---

## 6. 底线

1. **能抓到这个 bug 的最便宜一层**：纯函数不写接口测试，接口能测清的不写 E2E。
2. **断言可观察结果**：不断言实现细节、mock 内部调用、CSS 类名。
3. **缺陷修复先写失败的测试**，再改代码；顺序反了等于没有回归保护。
4. **测试库是 PostgreSQL**，每测试一事务、结束回滚；不用 SQLite 假装。
5. **不为了让流水线变绿而改测试**：删用例、加 skip、放宽断言、批量更新快照或契约基线都不算修复。
6. **flaky 必须查根因**：加大 sleep、提高重试次数只是把问题推到下次。
7. **回归红灯不放行**：P0 失败就是不能发；例外只有"功能开关已关闭"，且要留 issue 与恢复日期。
8. **有配置必须有执行**：写进 CI 的测试命令才算门禁，本地跑过不算。

---

## 附录：采纳自 LiteLLM 的实践与取舍

参考实现：`D:\workspace\codex\litellm\_src_litellm`（2221 个测试文件 / 28178 个测试函数 / 44 个分目录 conftest / 56 个 workflow）。下表只列**改变了本规范写法**的条目。

| 实践 | 参考位置 | 采纳 | 本仓库的落地 |
| --- | --- | --- | --- |
| mock-only 目录禁止真实出站 | `tests/README.MD:7-9`、`CONTRIBUTING.md:91-95` | 是 | backend 规范 2.2：单元测试目录不得访问网络 |
| mock 打在 transport 层而非方法级 | `test_mistral_completion.py:57-75`、`test_llm_http_handler.py:1660-1671` | 是 | backend 规范 6.2：`respx` / `MockTransport` 优先 |
| 单测缺依赖 skip、E2E 缺依赖 fail | `tests/e2e/conftest.py:66-74`、`_live_test_helpers.py:6-10` | 是 | 本文件 0.2；e2e 规范 2.3 |
| 服务由编排层起，测试只探活一次并缓存 | `tests/e2e/conftest.py:42-63` | 是 | e2e 规范 2.2 |
| 轮询到 deadline，never sleep-once | `tests/e2e/e2e_config.py:36-39` | 是 | e2e 规范 5.2 |
| 拒绝类用例双断言（状态码 + 无副作用） | `test_key_generate.py:58-70` | 是 | backend 规范 5.4 |
| 资源登记 + LIFO best-effort 清理 | `tests/e2e/lifecycle.py:97-120` | 是 | e2e 规范 4.2 |
| 清理全局数据前先确认"真跑过" | `tests/e2e/conftest.py:77-108` | 是 | e2e 规范 4.3 |
| 参数化矩阵规模守卫（cell count 断言） | `test_reasoning_effort_grid.py:203-207` | 是 | backend 规范 7.3 |
| 行为清单作分母 + 用例声明 + 静态 diff | `tests/e2e/coverage_registry/README.md:3-38` | 是（轻量版） | e2e 规范 8 |
| 契约用"重生成 + git diff --exit-code" | `check-ui-api-types.yml:67-83` | 是 | regression 规范 7.1 |
| 迁移一致性用工具自带的 diff 判定 | `proxy_migration_tests/test_db_schema_migration.py:40-68` | 是（`alembic check`） | regression 规范 7.3 |
| `xfail(strict=True)` 表达"已知缺陷待修" | `batches_endpoints/test_endpoints.py:1419-1432` | 是 | 本文件 3.1 |
| 重跑次数按域分档 | `_test-unit-base.yml:15-19` + 各 caller | 是 | 本文件 3 |
| 变异测试限定范围、手动触发、不阻断 | `mutation-test.yml:3-14`、`pyproject.toml:311-343` | 是 | backend 规范 9.4 |
| VCR 录制回放 + 基线自动过期（24h TTL） | `_vcr_redis_persister.py:11,176-183` | 有条件 | test-data 规范 5.4：仅当接入第三方 HTTP 时 |
| 按域拆 12 片 matrix + 孤儿文件守卫 | `test-unit-proxy-db.yml:37-104` | 否 | 规模不够：单次全量 < 30 min 时，分片维护成本高于收益 |
| 350 分钟变异 job + LLM 报告流水线 | `mutation-test.yml:29,101-131` | 否 | 本地/每周 cron 跑 `mutmut` 即可 |
| 覆盖率不设 `fail_under`，交给 Codecov delta | `codecov.yaml:71-79` | 部分 | 单容器时保留 `fail_under`；分片后改 delta |

一个反面教材也值得记住：LiteLLM 仓库里有 487 个前端 Vitest 文件、`package.json` 里配了 `test: vitest`，但 56 个 workflow 里**没有任何一个执行它**。测试写完不进门禁，等于没写——这就是本文件第 6 节第 8 条的由来。
