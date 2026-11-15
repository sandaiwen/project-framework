---
version: 1.0.0
last_updated: 2026-11-15
---

# 测试数据与隔离规范（Test Data & Isolation）

适用：所有层。写测试数据之前读一遍，能避免 80% 的"单跑通过、全跑失败"。

各层的具体手段见 `backend-testing-guide.md` 第 8 节、`frontend-testing-guide.md` 第 5 节、`e2e-testing-guide.md` 第 4 节；本文只规定**跨层共用的原则**。

---

## 1. 造数：只允许工厂函数

- MUST 用工厂函数造数据，放在 `backend/tests/factories.py` 与 `frontend/e2e/fixtures.ts`；禁止在每个用例里手写字典。
- MUST 工厂的默认值"能直接跑通"（不需要业务前置状态），特例通过参数覆盖：

```python
def make_order(**overrides) -> Order:
    """默认值可直接落库；只覆盖用例关心的字段。"""
    data = {
        "id": f"order-{uuid4().hex[:12]}",
        "sku": "SKU-DEFAULT",
        "qty": 1,
        "status": OrderStatus.PENDING,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    return Order(**(data | overrides))
```

- MUST NOT 在工厂里访问数据库；工厂只负责"造对象"，入库由调用方或 fixture 决定。
- SHOULD 需要落库的常见组合再包一层 fixture（`saved_order`），避免每个用例写 `session.add` + `commit`。

---

## 2. 唯一性

- MUST 唯一字段用 `uuid4()` / 时间戳生成，禁止硬编码 `test@example.com`、`SKU-1` 这类会冲突的值。
- MUST 唯一值的形态便于检索与清理：统一前缀 + 随机后缀，如 `e2e-<8位>`、`scratch-<12位>`。
- MUST NOT 用自增 ID、当前时间戳秒级精度作为唯一标识（并发下会撞）。
- SHOULD 把唯一值生成收敛到一个函数（`unique_marker()`），而不是每个用例各写一套 `Date.now()`。

```python
def unique_marker() -> str:
    """每次调用返回短唯一串，供名称/邮箱/标签使用。"""
    return uuid4().hex[:12]
```

---

## 3. 隔离：三档手段，按场景选

| 手段 | 隔离强度 | 代价 | 适用 |
| --- | --- | --- | --- |
| 事务回滚（外层事务 + SAVEPOINT） | 最强，测试间完全不可见 | 低 | 被测代码不自行 `commit()` |
| 唯一前缀 + 显式清理 | 中，靠前缀不重叠 | 中 | 被测代码会 `commit()`、后台任务、并发 |
| 独立数据库 / 独立 schema（每 worker） | 最强，但成本最高 | 高 | 并行 + 需要跨连接可见 |

- MUST 默认用事务回滚；发现"测试里查不到刚写的数据"或"数据落库了但回滚没生效"，说明被测代码自己管事务，改用唯一前缀。
- MUST 并行执行时每个 worker 独立库或独立 schema；禁止多 worker 共享同一库（外键、唯一索引、序列都会打架）。
- MUST NOT 用"跑之前清一次全库"代替隔离；那只能让失败从"必现"变成"偶发"。

### 3.1 清理的三条纪律

- MUST 只删自己创建的数据（前缀命中），禁止 `TRUNCATE` / `DELETE FROM ...`（无 where）。
- MUST 清理顺序子表 → 父表；能靠 `ON DELETE CASCADE` 就不手写多级删除。
- MUST 清理失败不掩盖主用例失败：清理异常记录 warning，不抛出覆盖原错误。

---

## 4. 用例之间不许有依赖

- MUST NOT 依赖测试执行顺序；用 `pytest-randomly` 随机顺序跑一遍，必须仍然全绿。
- MUST NOT 在测试间传递可变全局状态（模块级 list/dict、缓存单例、连接、临时文件路径）。
- MUST NOT 让用例 B 复用用例 A 创建的数据；每条用例自己造、自己清。
- SHOULD 需要共享昂贵只读资源（启动成本高的服务、只读数据集）时，用 `session` scope 且**只读**，并在 fixture docstring 写明"禁止写入"。

---

## 5. 时间、随机、外部依赖

### 5.1 时间

- MUST 时间通过依赖注入获取（`now()` / `clock.now()`），测试传入固定值。
- MUST NOT 对"今天""本月"这类相对时间做断言；要么注入时钟，要么断言范围。
- SHOULD 时区统一用 UTC 存储、按需转换；断言里写清时区，避免 CI 与本地时区差异。

### 5.2 随机

- MUST 随机值通过注入的生成器产生，或断言集合/性质而非具体值。
- MUST 需要可复现失败时，把种子打进失败信息（`random.seed(seed)` + 打印 seed）。

### 5.3 外部 HTTP 依赖

| 依赖性质 | 做法 |
| --- | --- |
| 请求/响应结构固定，主要验证"我们发了什么" | `respx`（后端）/ `msw`（前端）拦截，断言请求 |
| 需要验证线格式（编码、header、multipart） | `httpx.MockTransport` 注入真实 client |
| 需要验证超时、重试、连接复用 | 本地 stub 服务（进程内 ASGI 或 `127.0.0.1`） |
| 需要真实供应商契约（模型输出、支付回调） | **录制回放**，见 5.4 |

- MUST NOT 让单元测试打真实外网。
- MUST 真实供应商只在 `integration` 标记或 E2E 中出现，且缺凭据时按层规则处理（单测 skip、E2E fail）。

### 5.4 录制回放（接入第三方时可选）

如果项目要对接输出不稳定的第三方（大模型、支付、短信、地图），推荐"录一次、回放多次"，但**不要把录制文件当永久基线**：

- MUST 基线存外部存储（对象存储 / Redis），不入 git。理由：录制文件体积大、diff 不可读，且一旦冻结就会"永远回放一个过时响应"。
- MUST 设置过期时间（例如 24 小时），且**读取不续期**。这样每过一段时间必然重新录制一次，上游契约漂移会在一天内暴露，而不是半年后线上炸。
- MUST 只在用例通过时写入录制；失败保留旧录制，避免把错误响应当基线。
- MUST 录制前脱敏：抹掉 `Authorization` / `api-key` 等 header、指纹化用户标识、把图片 base64 换占位符。
- SHOULD 提供手动失效入口（`npm run vcr:flush` / `uv run python scripts/vcr_flush.py`），基线可疑时立刻重录。
- MUST NOT 在回放模式下跑"验证真实行为"的用例（否则回放数据会污染结论）；这类用例必须显式要求"录制关闭"。

---

## 6. 环境变量与配置

- MUST 测试读取的配置走环境变量，缺失时**直接失败**而不是回落默认值：

```python
APP_TEST_DATABASE_URL = os.environ["APP_TEST_DATABASE_URL"]  # 缺失即 KeyError
```

- MUST NOT 在测试里修改进程级环境变量后不还原；用 `monkeypatch.setenv`。
- SHOULD 在所有测试跑完后断言关键环境变量未变化（防"某个用例偷改连接串，后面全跑在错库上"）：

```python
@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    before = _snapshot_env(["DATABASE_URL", "APP_TEST_DATABASE_URL", "REDIS_URL"])
    yield
    leaked = {k: v for k, v in _snapshot_env(before).items() if v != before[k]}
    assert not leaked, f"{item.nodeid} 泄漏了环境变量：{leaked}"
```

---

## 7. 提交前检查清单

- [ ] 数据由工厂函数产生，用例里没有手写完整字典。
- [ ] 唯一字段用 `uuid4()` / 时间戳，带统一前缀。
- [ ] 隔离手段与场景匹配（事务回滚 / 前缀清理 / 独立库），没有"跑前清全库"。
- [ ] 清理只删自己的数据，顺序正确，失败不掩盖主用例。
- [ ] 用例之间无顺序依赖；`pytest-randomly` 跑一遍仍全绿。
- [ ] 时间、随机走注入；没有断言"今天"。
- [ ] 外部 HTTP 有替身；单元测试不出网。
- [ ] 录制回放（若使用）基线不入 git、有过期时间、失败不覆盖。
- [ ] 测试后环境变量未变化。
