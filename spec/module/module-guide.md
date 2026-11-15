---
version: 2.0.0
last_updated: 2026-11-15
---

# Python 模块编写指南（Python Module Guide）

本指南规定**一个模块如何落地成代码**：目录与文件怎么分、什么时候写成类、类怎么构造、依赖怎么传、模块怎么装配、对外暴露什么。

不涉及的内容：

- 代码格式、命名、导入顺序、类型注解、异常与日志、测试——见 `spec/python/python-code-style-guide.md`。
- 数据库迁移——见 `spec/alembic/alembic-guide.md`。
- 日志规范——见 `spec/logging/logging-guidelines.md`。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

## 0. 总纲

**实现一个模块时，默认用面向对象的方式组织：需要持有状态、依赖外部资源、或有可替换行为时，写成类；纯计算写成函数。**

这句话的两个方向都有效：

- SHOULD 默认把模块的能力收敛到一个入口类上，而不是散落成一组自由函数 + 全局变量。
- MUST NOT 为了"面向对象"创建没有状态、没有依赖、只有一个方法的类；这种情况直接写函数。

---

## 1. 模块目录结构

一个模块一个目录，结构固定：

```text
backend/app/modules/<module_name>/
├── __init__.py        # 只做对外导出，不含实现
├── service.py         # 模块入口类，编排流程
├── repository.py      # 数据访问，SQL 只出现在这里
├── models.py          # 领域对象（dataclass）
├── schemas.py         # 输入/输出数据结构（需要时）
├── errors.py          # 模块自有异常
└── config.py          # 模块独立配置（需要时）
```

要求：

- MUST 一个模块只占一个目录，目录名用 `lower_snake_case`。
- MUST 按需创建文件，不预先建空文件；`models.py`、`schemas.py` 等没有内容就不建。
- MUST NOT 在模块目录下放与模块无关的脚本、临时文件、数据文件。
- MUST NOT 出现循环依赖：`repository.py` 不得 import `service.py`。
- SHOULD 单文件不超过 400 行；超过说明该拆分了。

---

## 2. 用类还是用函数（判定表）

按场景对照，不要凭习惯选：

| 场景 | 形态 | 说明 |
| --- | --- | --- |
| 需要跨多次调用持有状态 | 类 | 例如累计器、缓存、连接池包装 |
| 依赖外部资源（DB 会话、HTTP 客户端、文件、时钟、配置） | 类，构造注入 | 便于替换与测试 |
| 存在可替换的实现（不同策略、不同数据源） | 接口 + 实现类 | 用 `Protocol` 或抽象基类定义边界 |
| 模块对外唯一入口 | 一个类 | 如 `OrderService`、`ReportExporter` |
| 无状态纯计算（格式转换、校验、计算） | 函数 | 不要包装成类 |
| 仅承载数据的结构 | `dataclass` | 不放业务逻辑 |
| 边界处的输入输出校验 | Pydantic 模型 / dataclass | 二选一，不混用 |

判定的两个必答点：

1. 这个对象里有需要**长期保存的状态**吗？
2. 这个对象需要**外部依赖**吗？

两点都是"否"，且只有一个方法 → 写函数。

---

## 3. 类的写法

### 3.1 单一职责

- MUST 一个类只做一件事，类的 docstring 用一句话说清这件事。
- MUST NOT 一个类里同时出现"流程编排"和"SQL 拼接"、"HTTP 调用"和"业务规则计算"。
- 出现两个以上不相关动词（如 `load_and_validate_and_save`）时，拆类或拆方法。

### 3.2 依赖通过构造注入

依赖（数据库会话、HTTP 客户端、配置、时钟）必须从外部传入并保存为成员。

推荐：

```python
class OrderService:
    def __init__(self, repository: OrderRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def create_order(self, payload: CreateOrderInput) -> Order:
        now = self._clock.now()
        order = Order(id=None, created_at=now, items=payload.items)
        return self._repository.save(order)
```

不推荐：

```python
class OrderService:
    def __init__(self) -> None:
        self._session = SessionLocal()          # 类内部自建依赖
        self._client = requests.Session()       # 无法替换、无法测试
```

### 3.3 构造只做赋值

- MUST 在 `__init__` 中只做参数赋值和轻量校验。
- MUST NOT 在 `__init__` 中执行数据库查询、网络请求、文件读写、启动线程。
- 需要"初始化时加载数据"时，单独提供 `load()` / `start()` 方法，由调用方显式触发。

### 3.4 不隐藏依赖

- MUST NOT 在模块级创建可变全局实例（如 `service = OrderService()`）。
- MUST NOT 用模块级单例、函数内 import 后缓存、类属性状态来绕过依赖注入。
- MUST 只用模块级常量（`UPPER_SNAKE_CASE`），且为不可变值。

### 3.5 公开面最小化

- MUST 只把调用方真正需要的方法设为公开，其余加 `_` 前缀。
- MUST NOT 暴露内部状态供外部直接改写；需要读取时提供只读方法。
- 公开方法 MUST 带完整类型注解（见代码风格指南第 5 章）。

### 3.6 组合优先于继承

- SHOULD 通过持有其他对象来复用能力，不建立多级继承。
- MUST NOT 继承层级超过两层。
- 需要多态时，先用 `Protocol` 定义行为契约，再写实现类，不用基类继承硬绑。

```python
class Notifier(Protocol):
    def send(self, message: str) -> None: ...


class EmailNotifier:
    def send(self, message: str) -> None: ...


class OrderService:
    def __init__(self, repository: OrderRepository, notifier: Notifier) -> None:
        self._repository = repository
        self._notifier = notifier
```

---

## 4. 分层与依赖方向

依赖只能向下：

```text
service.py   →  repository.py  →  models.py
     ↘________↗
        errors.py（各层都可用）
```

要求：

- MUST 由 `service.py` 承担流程编排；业务规则写在 service 或领域对象上。
- MUST 把 SQL、ORM 查询、外部 HTTP 调用放在 `repository.py` 或独立的 gateway/client 中。
- MUST NOT 在 service 里直接拼 SQL 字符串。
- MUST NOT 让 repository 反向依赖 service，也不要让 repository 直接返回 ORM 会话对象给上层。
- SHOULD 让 repository 在底层异常与模块异常之间做一次转换，上层只面对模块异常。

---

## 5. 模块对外接口

`__init__.py` 只做导出，不写实现：

```python
"""order 模块。"""

from .errors import OrderNotFoundError
from .models import Order, OrderItem
from .service import OrderService

__all__ = [
    "OrderService",
    "Order",
    "OrderItem",
    "OrderNotFoundError",
]
```

要求：

- MUST 让模块外部只通过 `from app.modules.order import OrderService` 这种方式使用模块。
- MUST NOT 让外部直接 import 模块内的 `repository`、私有辅助文件。
- MUST 在 `__all__` 中列出全部公开名称，未列出的视为内部实现。

---

## 6. 模块装配

实例的创建集中在一处，不散落在各模块内部：

```python
# backend/app/container.py

def build_order_service(session: Session, clock: Clock) -> OrderService:
    repository = OrderRepository(session)
    return OrderService(repository=repository, clock=clock)
```

要求：

- MUST 在应用启动或依赖装配处创建模块对象，并显式传入依赖。
- MUST NOT 在被调用方内部 new 出上游对象。
- MAY 在 Web 框架的依赖机制（如 FastAPI `Depends`）中完成同样的装配，但语义一致。
- 装配函数 SHOULD 与模块同名对应（`build_<module>_service`），便于查找。

---

## 7. 异常边界

- MUST 把模块自有异常定义在 `errors.py`，继承自项目统一的基础异常。
- MUST 在模块对外的方法边界上抛出模块异常，不让 `sqlalchemy`、`httpx` 等底层异常直接穿出模块。
- MUST 在 repository 层完成底层异常到模块异常的转换，并保留异常链（`raise ... from exc`）。
- SHOULD 只在本层能处理时才捕获异常；不能处理就向上抛。

细则（捕获粒度、禁止裸 `except`、异常与业务判断的界线）见代码风格指南第 8 章。

---

## 8. 数据对象

- MUST 用 `dataclass`（或项目统一的模型基类）在层之间传递业务数据，不用裸 `dict`。
- MUST 区分两种对象：领域对象（`models.py`，承载业务数据与不变量）与传输对象（`schemas.py`，承载外部输入输出）。
- MUST NOT 在领域对象里放数据库会话、HTTP 客户端这类运行时依赖。
- MUST NOT 让 `schemas.py` 的字段直接决定数据库结构；两者各自独立演进。

---

## 9. 提交前检查清单

新增或修改一个模块时，逐项确认：

- [ ] 模块目录与文件名符合第 1 章。
- [ ] 需要状态或依赖的对象写成了类，纯计算写成了函数（对照第 2 章判定表）。
- [ ] 类名是名词或名词短语，一个类只有一项职责。
- [ ] 全部外部依赖通过构造函数传入并存为成员。
- [ ] `__init__` 中没有 I/O、没有建连、没有启动线程。
- [ ] 模块级没有可变全局实例。
- [ ] 模块外只通过 `__init__.py` 导出的名称使用本模块。
- [ ] SQL 与外部调用只出现在 repository / client 中，没有反向依赖。
- [ ] 模块自有异常在 `errors.py` 中定义，边界处抛出的是模块异常。
- [ ] 层间传递的是 dataclass 或 schema，不是裸 `dict`。
- [ ] 公开方法有完整类型注解，内部实现用 `_` 前缀。
- [ ] 没有为了形式上的面向对象创建空类或单方法包装类。

---

## 10. 底线

1. 模块的能力优先收敛到类上，类的依赖优先从外部注入。
2. 用类的理由是"有状态"或"有依赖"，不是"面向对象"。
3. 一个类只做一件事，一件事只在一个地方实现。
4. 依赖方向单一，SQL 与外部调用隔离在数据访问层。
5. 模块对外只暴露 `__init__.py` 声明的内容。

**如果一段模块代码需要先读三个文件才能理解一次调用发生了什么，说明分层或依赖方向出了问题。**
