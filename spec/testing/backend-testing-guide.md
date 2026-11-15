---
version: 2.0.0
last_updated: 2026-11-15
---

# 后端测试规范（Backend Testing）

适用：`backend/` 下的 pytest 测试。技术栈 Python 3.12+ / FastAPI / Pydantic v2 / SQLAlchemy 2.0 async / PostgreSQL。

总纲与选层判据见 `spec/testing/README.md`；造数与隔离细节见 `spec/testing/test-data-guide.md`；已修缺陷的登记与反向验证见 `spec/testing/regression-testing-guide.md`。

---

## 1. 配置

唯一配置写在 `backend/pyproject.toml`，不另放 `pytest.ini` / `setup.cfg`（多份配置并存必然出现"改了这份、跑的是那份"）。

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
addopts = "-q --strict-markers --strict-config"
markers = [
  "slow: 单条超过 2 秒或依赖外部服务",
  "integration: 依赖真实外部边界（真实 PostgreSQL、真实 HTTP）",
  "regression: 已修缺陷的回归用例，须登记于 docs/regression/registry.yaml 并完成反向验证",
]

[tool.coverage.run]
branch = true
source = ["app"]

[tool.coverage.report]
show_missing = true
fail_under = 85
exclude_lines = [
  "if TYPE_CHECKING:",
  "raise NotImplementedError",
  "def __repr__",
  "pragma: no cover",
]
```

规则：

- MUST `asyncio_mode = "auto"`：异步测试与异步 fixture 都不写 `@pytest.mark.asyncio` / `@pytest_asyncio.fixture`。
- MUST `asyncio_default_fixture_loop_scope` 与 `asyncio_default_test_loop_scope` 设为**同一值**。不一致时 session 级 engine 在 A 循环创建、测试在 B 循环使用，报 `Event loop is closed` 或 `attached to a different loop`。
- MUST 只用一个异步插件。本仓库统一 `pytest-asyncio`，**不装、不用 `pytest-anyio`**（含 `@pytest.mark.anyio`），两个插件同时启用会争抢同一批 `async def`。
- MUST NOT 在 `addopts` 挂 `--cov`：单跑一个用例也会采集全量覆盖率，本地变慢且噪声大。覆盖率由第 9 节命令显式开启。
- MUST `--strict-markers` 与 `--strict-config` 常开：marker 拼错、配置键写错要当场报错，而不是静默失效。
- MUST NOT 用 `filterwarnings = ["ignore"]` 压制告警；新增 `DeprecationWarning` 按缺陷处理。

### 1.1 一次只装一套插件

同时安装 `pytest-rerunfailures` 与 `pytest-retry` 会让两者争抢同一个 `--reruns` 选项，且其中一个在 in-process 调用（如 `mutmut`）下会 `INTERNALERROR`。本项目只装 `pytest-rerunfailures`，本地不默认开启重跑（重跑只在 CI 按域启用，见 README 第 3 节）。

---

## 2. 目录与分层

### 2.1 镜像规则

- MUST `tests/` 镜像 `app/`：`app/modules/users/service.py` ↔ `tests/modules/users/test_service.py`。找测试时按被测文件路径反推。
- MUST 跨模块、需要真实外部边界的测试放 `tests/integration/`；需要跨模块复现的缺陷放 `tests/regression/`。
- MUST NOT 把测试集中堆在 `tests/` 根目录，除非被测对象本身就是 `app/` 根下的单文件。
- SHOULD 一个被测文件对应一个 `test_<文件名>.py`；文件超过 500 行时按行为拆分，不按函数拆分。

### 2.2 单元测试目录禁止真实出站

`tests/modules/**` 与 `tests/integration/**` 的分工不是"能不能联网"，而是**"要不要真实边界"**：

| 目录 | 允许真实 PostgreSQL | 允许真实 HTTP | 说明 |
| --- | --- | --- | --- |
| `tests/modules/**`（除 `test_repository.py`） | 否 | 否 | 全部外部边界必须替身 |
| `tests/modules/**/test_repository.py` | 是 | 否 | 验证 SQL、约束、事务 |
| `tests/integration/**` | 是 | 是（指向本机或 compose 内的服务） | 跨模块协作 |
| `tests/regression/**` | 视需要 | 视需要 | 按原缺陷的复现条件 |

- MUST NOT 在单元测试里请求公网。需要真实第三方时，走 `tests/integration/` 并显式打 `integration` 标记。
- SHOULD 在 CI 上用网络策略兜底：单元测试 job 不需要外网，跑通即可反证"没有偷偷出站"。

---

## 3. 命名

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| 文件 | `test_<被测模块>.py` | `test_user_service.py` |
| 函数 | `test_<行为>_<条件>_<期望>` | `test_login_with_wrong_password_returns_401` |
| 类（仅聚合同族用例时） | `Test<被测对象>` | `TestUserService` |
| fixture | 名词，不用动词短语 | `db_session`、`auth_client` |

- MUST 测试名能读出"什么条件下发生什么"，禁止 `test_1`、`test_service`、`test_ok`。
- MUST 回归用例命名带编号（见 regression 规范第 4 节）。
- SHOULD 断言失败信息写中文并带实际值：`assert resp.status_code == 401, f"期望 401，实际 {resp.status_code}"`。

---

## 4. fixture

- MUST 放在**最近**的 `conftest.py`：只被一个模块用的写在该模块的 `conftest.py`，不是根目录。
- MUST scope 默认 `function`；扩大到 `session` / `module` 只允许用于**只读且昂贵**的对象（engine、已解析配置、迁移后的库）。
- MUST 用 `yield` fixture 做清理，清理代码写在 `yield` 之后（测试失败时同样执行）。
- MUST NOT 用 `autouse=True` 做"每个测试都重置数据库/清缓存"这类隐式全局动作。需要隔离就在 fixture 里给每个测试独立事务（第 8 节）。
- MUST NOT 在 fixture 里 `time.sleep` 等异步资源就绪；改为轮询条件 + 超时上限。
- MUST 全局状态（模块级单例、缓存、注册表、`os.environ`）在 fixture 里显式保存与还原，并在 docstring 写明**哪些状态不保证被还原**。

```python
# 推荐：就近、显式、可清理
@pytest.fixture
async def db_session(engine):
    """每个测试一个独立事务，结束后整体回滚。"""
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()
```

### 4.1 全局状态隔离要写"不保证"

autouse 的重置 fixture 永远不可能还原所有东西（类实例内部状态、注册过的路由、logger handler、第三方库单例）。照抄下面这段注释结构，把边界写清楚，比追求"万能重置"更可靠：

```python
@pytest.fixture(autouse=True)
def reset_app_state():
    """每个测试前重置可安全复制的模块级可变状态。

    会被重置：settings 缓存、限流计数器、内存缓存 dict。
    不会重置：已构造的 service 单例、已注册的路由、logger handler。
    需要改这些时用 monkeypatch.setattr 并依赖它自动还原，不要指望本 fixture。
    """
```

- MUST NOT 用 `importlib.reload(模块)` 做隔离。它会重新执行整条 import 链，单测从毫秒级退化到秒级，且在 xdist 下行为不稳定。
- SHOULD 需要"干净单例"时，把构造逻辑收进 `create_xxx()` 工厂，测试直接调工厂，而不是改全局。

---

## 5. 接口测试

用 `httpx.AsyncClient` + `ASGITransport`，不用 `TestClient`。

理由：`TestClient` 在自己的线程与事件循环里跑应用，无法与异步 engine / session 共用同一循环；异步测试函数内也不能使用它。

```python
# tests/conftest.py
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db
from app.main import create_app


@pytest.fixture
def app(db_session) -> FastAPI:
    application = create_app()

    async def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

### 5.1 规则

- MUST `base_url` 给绝对地址（`http://test`），httpx 要求请求 URL 为绝对地址。
- MUST `dependency_overrides` 在 fixture 结束时 `clear()`，否则污染后续测试。
- MUST 覆盖数据库依赖时，override 返回本测试的 `db_session`，这样测试内直接查库能看到 handler 写入的数据（回滚前）。
- MUST app 由 `create_app()` 构造，不在模块导入时创建全局实例，否则每个测试无法独立注册 override。
- MUST 应用依赖 `lifespan`（连接池、缓存、定时任务）时用 `asgi-lifespan` 的 `LifespanManager` 包住 client，否则启动逻辑不执行：

```python
from asgi_lifespan import LifespanManager

@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    app.dependency_overrides.clear()
```

- MUST 断言至少包含：状态码 + 响应体关键字段（或 `response.json() == {...}` 全等）。只断状态码不算。
- MUST 断言失败时把响应体带出来：`assert resp.status_code == 422, resp.text`。

### 5.2 鉴权

- MUST 鉴权接口至少各有一条：无 token、过期 token、权限不足。
- MUST 这类用例用 `dependency_overrides[get_current_user]` 注入固定用户，不重复验证 JWT 解码；JWT 解码本身单独写单元测试。
- MUST NOT 用 `patch("app.api.deps.get_current_user")` 绕过鉴权——那样连"鉴权依赖是否真的挂在路由上"都测不到。

```python
async def test_create_order_without_token_returns_401(client):
    resp = await client.post("/api/v1/orders", json={"sku": "A-1", "qty": 1})
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["title"], "错误响应必须带可读标题"  # 字段以项目 API 契约为准
```

### 5.3 错误信封

- MUST 对每一类错误码各有一条用例，断言**信封结构**而不只是状态码：`title` / `detail` / 业务 `code` 至少各断一个字段。
- MUST NOT 断言完整错误文案（改文案会红）；断言"包含关键片段"或"code 等于常量"。
- SHOULD 用一条参数化用例覆盖全部错误码，而不是复制十次。

### 5.4 拒绝类用例必须双断言

只断 403 是不够的：**必须同时证明"拒绝之后什么都没写"**。这类"以为拦住了、其实已经落库"的缺陷，只靠状态码永远抓不到。

```python
async def test_insufficient_permission_does_not_write(client, db_session):
    resp = await client.delete(f"/api/v1/orders/{order_id}", headers=user_headers)
    assert resp.status_code == 403, resp.text
    # 第二断言：副作用没有发生
    still_there = await db_session.get(Order, order_id)
    assert still_there is not None, "拒绝后订单被删除了"
```

- MUST 所有"删除 / 修改 / 越权 / 超限"类拒绝用例都补第二条断言：数据库状态、外部调用次数、或消息是否入队。
- SHOULD 把"副作用检查"写成小工具函数（如 `assert_order_exists(db, id)`），避免每个用例重复写查询。

---

## 6. mock 与替身

### 6.1 原则

- MUST 只 mock **自己拥有的边界之外**的东西：第三方 HTTP、支付、邮件、对象存储、时钟。自己写的 service 之间不 mock，直接构造真实对象。
- MUST 在**使用处**打补丁，不是定义处。`service.py` 里 `from httpx import get` 之后要 patch `app.modules.x.service.get`，patch `httpx.get` 不生效。
- MUST `autospec=True`（或 `create_autospec`）。否则方法名写错、参数个数不对依然通过，属于假绿。
- MUST NOT 断言 mock 的内部调用细节（`mock_calls` 的顺序）来验证业务逻辑；要验证"发出了什么请求"时，断言参数中的关键字段。
- SHOULD 优先 `monkeypatch`（env、属性、`chdir`），需要断言调用时用 `mocker`。

### 6.2 出站 HTTP：优先在 transport 层拦截

按"能验证多少真实语义"排序，选最靠上的一种：

| 方式 | 能验证什么 | 什么时候用 |
| --- | --- | --- |
| `respx` | URL、方法、请求体、查询参数、调用次数 | **默认选择**，验证"我们发出了什么请求" |
| `httpx.MockTransport` | 真实 client 的编码、header、form vs JSON | 需要验证线格式（编码、content-type、multipart）时 |
| 本地假服务（进程内 ASGI 或 `127.0.0.1` 上的 stub） | 真实 HTTP 往返、超时、重试、连接复用 | 需要验证 client 的超时/重试/连接池行为时 |
| `patch("...HTTPHandler.post")` | 几乎没有 | **存量兼容**，新代码不用 |

```python
# 推荐：respx 断言请求
async def test_sync_order_posts_expected_body(respx_mock):
    route = respx_mock.post("https://erp.example.com/api/orders").respond(201, json={"id": "E-1"})
    await svc.push_order(order)
    assert route.called
    assert route.calls[0].request.content  # 关键字段逐个断言，不做全文比对
```

- MUST NOT 用 `patch` 掉自己封装的 client 方法后再断言"它被调用了"——这只证明函数被调用，不证明请求正确。
- SHOULD 一个外部依赖只保留**一种**替身方式，避免同一模块里 respx 与 patch 混用导致行为不可预测。

### 6.3 其余边界

| 依赖 | 做法 | 禁止 |
| --- | --- | --- |
| 时间 | 注入 `now()` / `clock`，测试传固定值 | `freezegun` 全局冻结后忘记原因 |
| 随机 | 注入生成器，或断言集合而非顺序 | 断言具体随机值 |
| 文件 | `tmp_path` | 写死 `/tmp/xxx` 或仓库内路径 |
| 队列 / 任务 | 同步执行或 mock 投递函数，断言投递参数 | 测试里起真实 broker |
| 对象存储 | `moto` 或注入 storage client | 用真实 bucket |

- MUST NOT 冻结时间后不还原；`freezegun` 必须限定在 `with` 块或 fixture 内。
- MUST 需要"等某状态出现"时轮询条件（带超时上限），不用固定 `sleep`。

---

## 7. 参数化与矩阵

### 7.1 基本用法

- MUST 正例与反例都参数化，不靠注释声明"支持 X、拒绝 Y"。
- MUST 用 `ids=` 或 `pytest.param(..., id=...)` 让 nodeid 可读：`api_key-httpx-timeout` 比 `test_thing[3-9]` 有用得多。
- MUST 一个参数化用例只验证一件事；把"状态码"和"响应体结构"拆成两条，不要塞进同一格。

### 7.2 多维权衡：矩阵放数据里，不放分支里

维度（角色 × 目标 × 期望）会相乘。正确形状是：**期望写在数据表里，测试体只有断言**：

```python
_SCENARIOS = [
    # (id, actor, body_extras, expected_status)
    ("self-admin", Actor.ADMIN, {}, 200),
    ("other-user", Actor.USER, {"team_id": TEAM_B}, 403),
    ("no-token", Actor.ANON, {}, 401),
]

@pytest.mark.parametrize("actor,body_extras,expected_status", [...], ids=[s[0] for s in _SCENARIOS])
async def test_create_key_permission_matrix(actor, body_extras, expected_status, client):
    resp = await client.post("/api/v1/keys", json={"name": "k", **body_extras}, headers=auth(actor))
    assert resp.status_code == expected_status, f"{actor}: {resp.text}"
```

- MUST NOT 在测试体里写 `if actor == ADMIN: ... elif ...` 的分支树；分支树会让"漏了一个角色"变成不报错。
- SHOULD 期望值放模块级常量或 YAML/JSON 数据文件，测试体只做"取数据 → 请求 → 断言"。

### 7.3 矩阵规模守卫

参数化矩阵会被"悄悄删掉一行"稀释，而这种删减不会让任何用例变红。**为矩阵条目数写一条断言**：

```python
def test_scenario_count():
    assert len(_SCENARIOS) == 12, f"权限矩阵应有 12 格，实际 {len(_SCENARIOS)}"
```

- MUST 每个参数化矩阵（≥6 格）配一条规模守卫，并在断言消息里写清"预期几格、由什么组成"。
- SHOULD 矩阵由代码生成（`for role in ROLES for target in TARGETS`）时，守卫断言总数等于两个集合大小的乘积。

### 7.4 不要用参数化代替抽象

同一套断言跑 N 个实现（多个 provider、多个存储后端、多个通道）时，用**基类 + 子类**而不是笛卡尔参数化：

```python
class BaseStorageContract:
    """所有存储实现的共同契约。子类只提供被测对象。"""
    @pytest.fixture
    def store(self) -> Storage: ...
    async def test_put_then_get_returns_same(self, store): ...

class TestRedisStorage(BaseStorageContract):
    @pytest.fixture
    def store(self): return RedisStorage(...)
```

- SHOULD 契约类里写"行为不变量"，子类只提供构造。失败定位到文件，而不是 N 个 nodeid 里的第 37 个。
- MUST NOT 让契约基类被 pytest 直接收集（命名不以 `Test` 开头，或用 `__test__ = False`）。

---

## 8. 数据库测试

- MUST 对真实 PostgreSQL 测试，**不允许用 SQLite 顶替**。SQLite 没有 `JSONB`、`UUID`、数组、`tsvector`，约束与锁语义也不同，SQLite 全绿的用例到生产库经常直接失败。
- MUST 测试库地址从环境变量读，缺失时直接失败，不静默回落到默认库：

```python
TEST_DATABASE_URL = os.environ["APP_TEST_DATABASE_URL"]  # 缺失即 KeyError，主动暴露
```

- MUST 测试库结构由**迁移**建立（先 `alembic upgrade head`），不用 `Base.metadata.create_all`。`create_all` 只反映模型定义，索引、约束、默认值、回填只存在于迁移里，两套 schema 会漂移。
- MUST 并行执行时每个 worker 用**独立数据库**（`APP_TEST_DATABASE_URL` 带 worker 后缀），禁止多 worker 共享同一库同一 schema。
- MUST NOT 依赖自增 ID 的具体数值，也不依赖插入顺序。

### 8.1 隔离策略一：事务回滚（默认）

适用：被测代码不自行 `commit()`（大多数 service / repository 测试）。

```python
@pytest.fixture(scope="session")
async def engine():
    # NullPool：连接不跨测试复用，避免绑定到已关闭的事件循环。生产不要用。
    eng = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()
```

`join_transaction_mode="create_savepoint"` 是 SQLAlchemy 2.0 的内置支持，业务代码里的 `commit()` 只释放 SAVEPOINT，外层事务结束时整体回滚，不需要 `after_transaction_end` 事件补丁。

### 8.2 隔离策略二：唯一前缀 + 显式清理

事务回滚解决不了一类场景：**被测代码自己管理事务**（接口测试里 handler 真的 `commit()`、后台任务、多连接并发）。这时改用"唯一前缀 + 逐表删除"：

```python
SCRATCH_PREFIX = "scratch-"

@pytest.fixture
async def scratch(db_session):
    prefix = f"{SCRATCH_PREFIX}{uuid4().hex[:12]}"
    yield Scratch(prefix=prefix)
    # 子表先于父表，避免外键冲突
    await db_session.execute(delete(OrderItem).where(OrderItem.order_id.like(f"{prefix}%")))
    await db_session.execute(delete(Order).where(Order.id.like(f"{prefix}%")))
    await db_session.commit()
```

- MUST 只删自己前缀命中的行，**禁止 `TRUNCATE`**（会踩并行 worker 与本地手工数据）。
- MUST 清理顺序子表 → 父表；有 `ON DELETE` 级联时优先依赖级联，不手写多级删除。
- MUST 清理用 `try/finally` 或 `yield` fixture，且清理失败不能让后续用例失败（记录 warning，不吞掉主用例的失败）。
- MUST 前缀长度足够（≥8 位随机），避免并行下撞前缀。

### 8.3 三档选法

| 场景 | 隔离方式 | 代价 |
| --- | --- | --- |
| service / repository 纯逻辑 | 事务回滚 | 最低，默认选它 |
| 接口测试，handler 会 commit | 唯一前缀 + 清理 | 中 |
| 需要跨连接可见（并发、锁、后台任务） | 唯一前缀 + 清理，且不开外层事务 | 最高，只在该用例使用 |

### 8.4 迁移一致性

- MUST 迁移本身单独验证：可重建库上跑 `upgrade head → downgrade base → upgrade head`，规则见 `spec/alembic/alembic-guide.md` 第八章。
- MUST 每个涉及模型的 PR 跑一次 `alembic check`（有模型变更但没生成迁移时非零退出），把它放进 CI 而不是靠 review 记性：

```bash
uv run alembic upgrade head
uv run alembic check          # 有未捕获的模型变更则失败
```

- MUST NOT 用"删掉迁移目录让检查变绿"处理失败；空迁移目录本身要判红。

### 8.5 测试卫生守卫

环境变量泄漏是最隐蔽的跨用例污染源：一个测试往 `DATABASE_URL` 写了值，后面所有测试都在打错的库上跑，且症状随机。

```python
@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    before = _snapshot_db_env()
    yield
    leaked = {k: v for k, v in _snapshot_db_env().items() if v != before[k]}
    assert not leaked, f"{item.nodeid} 泄漏了数据库环境变量：{leaked}"
```

- SHOULD 在 `tests/conftest.py` 对连接串、密钥类环境变量做"测试后未变化"断言。
- MUST 业务代码不得在 import 时读环境变量并写入模块级常量，否则任何隔离都无效。

---

## 9. 覆盖率与变异

### 9.1 覆盖率

```bash
uv run pytest --cov=app --cov-branch --cov-report=term-missing --cov-fail-under=85
```

- MUST 用分支覆盖（`--cov-branch`）。只看行覆盖会出现"`if/else` 只走一支仍算 100%"。
- MUST 全局门槛 85%，由 `fail_under` 固定；下调门槛必须在 PR 说明原因。
- SHOULD 新增模块自身不低于 90%。
- MUST NOT 为了达标把业务分支加入 `exclude_lines`。允许排除的只有：`if TYPE_CHECKING:`、`raise NotImplementedError`、`def __repr__`、明确标注 `pragma: no cover` 且写明原因的防御分支。
- MUST NOT 用 `# pragma: no cover` 覆盖整个函数——那等于把测试缺口藏起来。

### 9.2 覆盖率不替代断言

覆盖率只证明"这行被执行过"，不证明"结果被检查过"。一个 100% 覆盖但只 `assert result is not None` 的模块，回归保护接近零。

- MUST 覆盖率达标与"关键路径有语义断言"同时满足，缺一不算通过 review。
- SHOULD 高代价逻辑（金额、权限、删除、并发、幂等）逐条检查是否有"值断言"，而不只是"调用断言"。

### 9.3 慢测试

- MUST 单条超过 2 秒或依赖外部服务的用例打 `slow`，夜间跑。
- SHOULD 用 `--durations=20` 定期看长尾，超过 5 秒的用例要么拆、要么 mock 掉慢边界。

### 9.4 变异测试（按需）

对金额、鉴权、数据删除、并发控制这类"错了代价高、且测试容易写浅"的逻辑，用变异测试检查"测试是否真的会发现错误"：

```bash
uv run --with mutmut mutmut run --paths-to-mutate app/modules/orders
uv run --with mutmut mutmut results
```

- SHOULD 只在改动范围内跑，不全仓跑（耗时与收益不成比例）。
- MUST 逐个归类存活变异体：补断言，或写明"等价变异体"的理由。
- MUST NOT 把变异测试设为合并门禁；它按需或每周触发，结论进 PR 或计划 `artifacts/`。

---

## 10. 反例

| 反例 | 问题 | 改法 |
| --- | --- | --- |
| 调用一遍被测函数，不断言 | 永远通过 | 断言返回值或副作用 |
| `assert result is not None` | 几乎抓不到缺陷 | 断言关键字段值 |
| 一个用例断言创建、列表、删除 | 第一个失败掩盖后续 | 拆成三条 |
| 断言日志文本 | 改文案就红，与行为无关 | 断言返回值；日志单独用 `caplog` 测 |
| 用 `skip` 处理已知缺陷 | 缺陷隐形，且计数消失 | `xfail(strict=True)` + 缺陷号 |
| 复制实现逻辑做断言 | 实现错了两边一起错 | 固定输入 + 手算期望值 |
| `patch` 掉 service 再断言"被调用了" | 只证明调用，不证明正确 | 断言请求内容或最终状态 |
| 为了过测试把断言从 `==` 改成 `in` | 把回归保护降级 | 先判断是代码错还是期望过时 |

---

## 11. 提交前检查清单

- [ ] 新增/修改的行为有对应测试，且测试在改动前会失败（缺陷修复）。
- [ ] 测试放在对应层，没有用 E2E 覆盖单测能覆盖的逻辑，也没有用 mock 掩盖真实边界。
- [ ] 后端测试目录镜像 `app/`。
- [ ] 异步测试没写 `@pytest.mark.asyncio`（`asyncio_mode=auto` 已生效）。
- [ ] 没有同时启用 `pytest-asyncio` 与 `pytest-anyio`，也没有同时装两个 `--reruns` 提供者。
- [ ] mock 都在使用处，且带 `autospec=True`；出站 HTTP 用 respx / MockTransport，不用方法级 patch。
- [ ] 接口测试断言了状态码 + 响应体字段；鉴权覆盖无 token / 过期 / 越权。
- [ ] 拒绝类用例有第二条断言（副作用没发生）。
- [ ] 数据库测试跑在真实 PostgreSQL，隔离方式按 8.3 选的档，未用 SQLite 顶替。
- [ ] `dependency_overrides` 在 fixture 结束时清理。
- [ ] 参数化矩阵有规模守卫，`ids` 可读。
- [ ] 覆盖率达标（85% 分支），未用排除项凑数。
- [ ] 失败的测试没有用 `skip` / 重试 / 放宽断言处理。
- [ ] 未执行的测试已在报告中如实说明原因。
