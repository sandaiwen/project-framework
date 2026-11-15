---
version: 2.0.0
last_updated: 2026-11-15
---

# Python 编码风格指南（Python Code Style Guide）

> 本指南用于约束 Python 代码的编写、修改与维护，适用于 AI 生成代码和人工编写代码。
>
> 核心目标是提高代码的可读性、一致性和可维护性，避免不必要的复杂设计、过度抽象以及无业务价值的重构。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

## 0. 规则约束等级

本指南使用以下约束等级：

- **MUST**：必须遵守，除非存在明确且合理的例外。
- **MUST NOT**：禁止行为。
- **SHOULD**：默认应当遵守，特殊情况下可以例外，但应有合理理由。
- **SHOULD NOT**：通常不应采用，除非存在明确需求。
- **MAY**：允许使用，根据实际情况选择。

如果规则之间存在冲突，优先遵循以下原则：

1. 正确性优先于代码风格。
2. 保持现有业务行为优先于代码改写。
3. 可读性优先于简洁性。
4. 明确性优先于技巧性。
5. 项目现有约定优先于本指南中的非强制建议。

## 1. 核心理念

以下原则适用于所有 Python 代码的编写与修改。

### 1.1 可读性优先

- MUST 优先保证代码容易理解，而不是追求代码行数最少。
- MUST 使用清晰、直观的代码表达业务意图。
- SHOULD 将复杂表达式拆分为多个简单步骤。
- SHOULD 避免不必要的一行式实现和嵌套表达式。

### 1.2 明确优先

- MUST 避免依赖隐式行为表达重要业务逻辑。
- MUST 使用具有明确语义的变量、函数和类名称。
- SHOULD 优先使用直观的控制结构，而不是复杂的技巧性写法。

### 1.3 一致性优先

- MUST 遵循当前项目已有的编码风格。
- MUST 保持同一模块内的命名、格式和设计风格一致。
- SHOULD 避免在同一项目中引入不必要的风格差异。

### 1.4 简单优先

- MUST 避免没有实际价值的抽象和封装。
- SHOULD 优先采用简单、直接的实现方式。
- SHOULD 不为尚不存在的需求提前设计复杂结构。

### 1.5 避免过度设计

- MUST 避免为了展示技术能力而引入不必要的设计模式。
- MUST NOT 仅为了形式统一而增加抽象层。
- SHOULD 根据实际复杂度决定是否引入类、接口、装饰器或其他高级特性。

## 2. 代码布局（Formatting）

### 2.1 缩进

- MUST 使用 4 个空格缩进。
- MUST NOT 使用 Tab 缩进。
- MUST 保持代码块缩进层次清晰。

### 2.2 行长度

- SHOULD 将单行代码控制在 80 个字符以内。
- MAY 对 URL、长路径、长字符串、特殊注释等进行合理例外处理。
- MUST NOT 为了满足行长度限制而破坏代码的可读性。

### 2.3 换行

- SHOULD 使用圆括号、方括号或花括号实现隐式换行。
- MUST NOT 在普通代码中使用反斜杠进行续行，除非存在无法合理替代的特殊情况。
- SHOULD 将复杂参数列表和表达式拆分为多行。

示例：

```python
result = calculate_price(
    items=items,
    discount=discount,
    tax_rate=tax_rate,
)
```

### 2.4 空行

- MUST 在模块级函数和类定义之间保留两个空行。
- MUST 在类方法之间保留一个空行。
- SHOULD 使用空行分隔逻辑上独立的代码段。
- MUST NOT 随意插入大量空行。

### 2.5 空格

- MUST 在运算符两侧使用适当空格。
- MUST 在逗号后添加空格。
- SHOULD 避免不必要的空格和过度紧凑的表达式。

## 3. 命名规范（Naming）

### 3.1 变量与函数

- MUST 使用 `lower_snake_case`。
- MUST 使用能够表达实际用途的名称。
- MUST NOT 使用无意义的缩写或单字符名称，循环索引等常见情况除外。

推荐：

```python
retry_count = 3
user_name = "Tom"


def calculate_total_price():
    ...
```

不推荐：

```python
x = 3
n = "Tom"


def calc():
    ...
```

### 3.2 类名

- MUST 使用 `UpperCamelCase`。
- SHOULD 使用名词或名词短语描述类的职责。

```python
class OrderProcessor:
    pass


class UserRepository:
    pass
```

### 3.3 常量

- MUST 使用 `UPPER_SNAKE_CASE`。
- SHOULD 在模块顶部定义模块级常量。

```python
MAX_RETRIES = 5
DEFAULT_TIMEOUT = 30
```

### 3.4 私有成员

- SHOULD 使用单下划线 `_name` 表示内部实现细节。
- MUST NOT 将双下划线 `__name` 当作普通私有成员的默认命名方式。
- MAY 在确实需要避免子类属性名称冲突时使用双下划线名称改写机制。

### 3.5 特殊名称

- MUST 遵循 Python 已有的特殊命名约定。
- MUST NOT 随意覆盖或重新定义具有特殊含义的内置名称。

例如：

```python
# 不推荐
list = [1, 2, 3]
id = 100

# 推荐
numbers = [1, 2, 3]
user_id = 100
```

## 4. 导入规范（Imports）

### 4.1 导入顺序

MUST 按照以下顺序组织导入：

1. Python 标准库。
2. 第三方库。
3. 当前项目内部模块。

不同分组之间 MUST 保留一个空行。

```python
import os
import sys

import requests

from myproject.order import OrderService
```

### 4.2 导入方式

- MUST NOT 使用 `from module import *`。
- SHOULD 优先使用明确的模块或成员导入。
- SHOULD 避免不必要的重复导入。
- SHOULD 避免循环导入。

### 4.3 导入别名

- MAY 对名称过长或容易冲突的模块使用别名。
- SHOULD 遵循第三方库和项目已有的常见别名约定。
- MUST NOT 为简单名称随意创建别名。

## 5. 类型注解（Type Hints）

### 5.1 基本要求

- MUST 为公共函数和公共方法提供参数及返回值类型注解。
- SHOULD 为复杂的内部函数添加类型注解。
- SHOULD 使用类型注解表达函数输入、输出和数据结构。
- MUST NOT 为了添加类型注解而引入不必要的复杂类型设计。

```python
def calculate_price(items: list[Item]) -> float:
    ...


def find_user(user_id: int) -> User | None:
    ...
```

### 5.2 类型表达

- SHOULD 优先使用 Python 内置泛型，例如 `list[str]`、`dict[str, int]`。
- SHOULD 优先使用 `X | None` 表示可选类型（Python 3.10+）。
- MUST 明确区分 None、空值和其他合法数据类型。
- SHOULD 避免不必要地使用 `Any`。
- MUST NOT 为了消除类型检查错误而随意使用 `cast()` 或忽略类型检查。

### 5.3 类型注解的边界

- MUST 保证类型注解与实际行为一致。
- MUST NOT 使用类型注解掩盖实际类型错误。
- SHOULD 避免过度泛型化和复杂类型嵌套。
- MAY 在存在明确复用需求时使用泛型、Protocol 等高级类型特性。

## 6. 文档字符串与注释（Docstrings & Comments）

### 6.1 Docstrings

- MUST 为模块、类和公共函数编写必要的文档字符串。
- SHOULD 使用 Google 风格 Docstring。
- MUST 描述实际行为，而不是简单重复函数名称。
- SHOULD 根据需要说明参数、返回值和异常。
- MUST 保持文档与代码实现一致。

示例：

```python
def fetch_user(user_id: int) -> User:
    """根据用户 ID 获取用户信息。

    Args:
        user_id: 用户唯一标识。

    Returns:
        对应的用户对象。

    Raises:
        UserNotFoundError: 用户不存在时抛出。
    """
```

### 6.2 注释

- SHOULD 优先解释为什么这样实现，而不是重复说明代码做了什么。
- MUST NOT 添加显而易见的冗余注释。
- MUST 在业务规则复杂或实现方式不直观时提供必要说明。
- SHOULD 及时更新过期注释。

推荐：

```python
# 跳过 CSV 文件的表头行。
row_index += 1
```

不推荐：

```python
# row_index 加 1。
row_index += 1
```

### 6.3 TODO 注释

- MAY 使用 TODO 标记尚未完成的工作。
- SHOULD 简要说明待处理事项。
- MUST NOT 将 TODO 当作掩盖未完成实现的方式。

## 7. 函数与类设计（Functions & Classes）

### 7.1 函数设计

- MUST 保持函数职责明确。
- SHOULD 优先编写短小、容易理解的函数。
- MUST NOT 为了满足固定行数限制而机械拆分函数。
- SHOULD 避免过深的条件嵌套。
- MUST 保证函数名称能够表达其主要行为。

### 7.2 参数设计

- SHOULD 将函数参数数量控制在 5 个以内。
- 参数较多时，SHOULD 考虑使用具有明确业务含义的 `dataclass` 或其他合适的数据结构。
- MUST NOT 为了减少参数数量而创建无意义的包装对象。
- SHOULD 对具有不同语义的参数使用关键字参数传递。

### 7.3 返回值

- MUST 保持返回值语义明确。
- SHOULD 避免在同一函数中混用多种不相关的返回类型。
- MUST NOT 通过隐式全局状态代替明确的返回值。
- SHOULD 避免返回调用者无法合理使用的内部临时对象。

### 7.4 副作用

- SHOULD 尽量避免不必要的副作用。
- MUST 明确函数是否会修改传入对象或外部状态。
- MUST NOT 在没有明确约定的情况下修改调用者传入的数据。
- SHOULD 优先使用显式参数传递依赖，而不是依赖全局变量。

### 7.5 可变默认参数

MUST NOT 使用列表、字典、集合等可变对象作为函数默认参数。

不推荐：

```python
def add_item(item, items=[]):
    items.append(item)
    return items
```

推荐：

```python
def add_item(item, items=None):
    if items is None:
        items = []

    items.append(item)
    return items
```

### 7.6 类设计

- MUST 保证类具有明确的职责。
- SHOULD 优先使用简单类表达具有状态和行为的数据对象。
- MUST NOT 为了形式上的面向对象而创建无实际意义的类。
- SHOULD 避免不必要的继承层次。
- MAY 在确实需要时使用组合代替继承。

## 8. 异常处理（Exceptions）

### 8.1 基本原则

- MUST 只捕获能够合理处理的异常。
- MUST NOT 随意使用裸 `except:`。
- SHOULD 避免无明确理由地捕获 `Exception`。
- SHOULD 优先捕获具体异常类型。
- MUST NOT 使用空异常处理块隐藏错误。

不推荐：

```python
try:
    process()
except Exception:
    pass
```

推荐：

```python
try:
    process()
except ValueError as exc:
    logger.error("Invalid input: %s", exc)
    raise
```

### 8.2 异常传播

- MUST 避免无意义地捕获后重新抛出相同异常。
- SHOULD 在能够处理异常的层级处理异常。
- SHOULD 在需要转换异常时保留原始异常链。

```python
try:
    load_config()
except OSError as exc:
    raise ConfigLoadError("配置文件加载失败") from exc
```

### 8.3 异常与业务逻辑

- MUST 使用明确的异常类型表达错误。
- MUST NOT 使用异常代替普通条件判断。
- SHOULD 避免使用异常处理正常、预期的业务流程。

## 9. 表达式与数据结构（Expressions & Data Structures）

### 9.1 真值判断

- SHOULD 使用 Python 原生真值判断简化容器判断。
- MUST 使用 `is None` 或 `is not None` 判断 None。
- MUST NOT 混淆 None、False、0 和空容器。

推荐：

```python
if not items:
    ...

if value is None:
    ...

if enabled:
    ...
```

不推荐：

```python
if len(items) == 0:
    ...
```

### 9.2 推导式

- MAY 使用列表、字典和集合推导式。
- SHOULD 仅在表达式简单、容易理解时使用推导式。
- MUST NOT 编写包含多层复杂条件和嵌套循环的推导式。

### 9.3 字符串处理

- SHOULD 优先使用 f-string 进行字符串格式化。
- SHOULD 避免不必要的字符串拼接。
- MUST NOT 使用字符串拼接构造不安全的 SQL 查询。

```python
message = f"Hello, {name}"
```

### 9.4 数据结构选择

- SHOULD 根据数据语义选择 list、tuple、set、dict 等合适的数据结构。
- MUST NOT 为简单数据处理引入不必要的复杂数据结构。
- SHOULD 避免深层嵌套的列表和字典结构。
- SHOULD 避免过度链式调用。

### 9.5 资源管理

- MUST 使用上下文管理器管理支持上下文管理协议的资源。
- SHOULD 使用 `with` 管理文件、锁和其他需要明确释放的资源。
- MUST 避免因异常或提前返回而导致资源未正确释放。

推荐：

```python
with open("data.txt", encoding="utf-8") as file:
    content = file.read()
```

### 9.6 内置函数与标准库

- SHOULD 优先使用 Python 内置函数和标准库中已有的能力。
- MUST NOT 为简单功能重复实现已有的标准能力。
- SHOULD 避免引入仅用于完成简单操作的额外依赖。
- MUST 新增、升级或移除依赖时按 `spec/dependency/dependency-guide.md` 执行，不直接改 `pyproject.toml`。

## 10. 日志与测试（Logging & Testing）

### 10.1 日志

- MUST 在生产代码中使用标准库 `logging`，不得使用 `print()` 代替日志记录。
- MUST 遵循项目专用日志规范。
- MUST NOT 在日志中记录密码、Token 等敏感信息。
- SHOULD 使用日志参数化格式，而不是提前进行字符串拼接。

推荐：

```python
logger.info("User ID: %s", user_id)
```

具体日志级别、格式、敏感信息处理与日志路由，参见：

`spec/logging/logging-guidelines.md`

### 10.2 测试

- SHOULD 使用 pytest 或 unittest 编写测试。
- MUST 保证新增或修改的代码具有合理的测试覆盖。
- SHOULD 优先覆盖正常场景、边界条件和异常场景。
- MUST NOT 为了让测试通过而删除、弱化或绕过原有有效测试。
- SHOULD 避免测试依赖不必要的外部资源。

AI 修改代码后，应根据修改范围执行相关测试，并如实说明未执行的测试。

本章只约束"必须有测试、不得弱化测试"这一层。测试分几层、放在哪里、用什么配置、断言什么、覆盖率门槛与回归流程，见：

- `spec/testing/README.md` —— 选层判据、目录总览、执行时机、flaky 治理
- `spec/testing/backend-testing-guide.md` —— pytest、fixture、mock、接口与数据库测试
- `spec/testing/frontend-testing-guide.md` —— Vitest、组件、数据层、快照
- `spec/testing/e2e-testing-guide.md` —— Playwright、服务编排、造数与清理
- `spec/testing/regression-testing-guide.md` —— 反向验证、登记表、基线、红灯放行
- `spec/testing/test-data-guide.md` —— 造数、隔离、外部依赖替身

## 11. AI 编码行为约束（AI Coding Rules）

本章节专门约束 AI 生成、修改和重构 Python 代码时的行为。

### 11.1 禁止过度抽象

- MUST 优先采用简单直接的实现方式。
- MUST NOT 为不存在的需求提前设计复杂抽象。
- MUST NOT 仅因为代码形式相似就创建抽象层。
- SHOULD 在存在明确复用需求、共同业务语义或复杂度降低收益时再考虑抽象。
- MUST 避免无业务意义的工厂、管理器、包装器和中间层。

### 11.2 禁止不必要的设计模式

- MUST NOT 为简单业务逻辑引入不必要的设计模式。
- SHOULD 优先使用普通函数、简单类和基础控制结构。
- MAY 在复杂度确实需要时使用策略模式、工厂模式等设计模式。
- MUST 保证引入的设计模式能够实际降低复杂度。

### 11.3 禁止无需求重构

- MUST 优先保持已有代码结构和业务行为。
- MUST NOT 在没有明确需求或实际 Bug 的情况下重写已有正确逻辑。
- MUST NOT 为了个人风格偏好随意重命名变量、函数或类。
- MUST NOT 随意调整无关模块和目录结构。
- MUST NOT 将简单功能修改扩大为大范围重构。

### 11.4 最小化修改范围

- MUST 只修改完成当前任务所必需的代码。
- MUST 保持无关代码不变。
- SHOULD 优先采用局部修改，而不是整体重写。
- SHOULD 避免对无关文件进行格式化或风格调整。
- 如果确实需要扩大修改范围，应有明确的技术理由。

### 11.5 优先复用已有实现

编写新代码之前：

- SHOULD 检查项目中是否已有相同或相近功能。
- SHOULD 优先复用已有函数、类和模块。
- MUST NOT 在已有实现能够满足需求时重复创建相同功能。
- MUST 遵循现有项目的调用方式和接口约定。

### 11.6 禁止编造接口

- MUST NOT 假设项目中存在未经确认的函数、类、属性或模块。
- MUST NOT 编造第三方库不存在的 API。
- MUST NOT 擅自假设数据库字段、配置项和环境变量。
- SHOULD 通过现有代码和实际依赖确认接口是否存在。
- 无法确认时，应明确说明不确定性，而不是编造实现。

### 11.7 禁止不必要的高级特性

普通业务代码中默认优先使用：

- 基础控制结构：if、for、while。
- 普通函数。
- 简单类。
- 标准异常处理。
- 常规数据结构。

以下特性 SHOULD 谨慎使用：

- 元类。
- 动态继承。
- 复杂装饰器。
- 反射和动态属性访问。
- 自定义魔法方法。
- 复杂描述符。
- 运行时动态代码生成。

只有存在明确需求、合理技术理由和必要测试时，才 MAY 使用上述高级特性。

### 11.8 保持接口和业务行为

- MUST 尽可能保持已有函数签名、返回值结构和异常行为。
- MUST NOT 擅自改变业务规则和默认行为。
- MUST NOT 随意改变调用顺序和数据处理流程。
- 如果需求确实要求改变已有行为，应确保修改范围明确。

### 11.9 验证修改结果

- SHOULD 对修改后的代码执行相关测试。
- SHOULD 检查导入、类型和基本语法是否正确。
- MUST NOT 声称未执行的测试已经通过。
- MUST NOT 虚构运行结果或验证结果。
- 无法执行验证时，应明确说明原因。

## 12. 底线规则（Final Principles）

所有 Python 代码都应遵循以下底线：

1. 代码必须正确实现实际需求。
2. 代码必须容易阅读和理解。
3. 代码必须保持清晰、明确的职责边界。
4. 不得引入没有实际价值的抽象和复杂设计。
5. 不得为了追求简洁而牺牲可读性。
6. 不得在没有明确需求的情况下改变已有正确逻辑。
7. 不得为了形式上的规范而增加无意义的代码。

**最终原则：如果一段代码需要花费大量时间才能理解其意图，那么它的设计或表达方式就值得重新审视。**

代码的价值在于清晰、正确和可维护，而不是复杂、炫技或形式上的优雅。