---
version: 2.0.0
last_updated: 2026-11-15
---

# Logging Guidelines（日志规范）

## 1. 目的

本文档定义 Python 应用程序统一的日志记录规范。

目标是确保日志具备以下特征：

- **可读性：** 人员能够直接阅读和理解日志。
- **可检索性：** 能够通过关键字段快速定位日志。
- **一致性：** 不同模块和服务使用统一的日志格式。
- **可诊断性：** 日志能够帮助定位异常和分析问题。
- **可演进性：** 日志格式保持稳定，便于后续工具处理。

本文档只约束日志内容、格式和记录方式，不涉及日志采集、存储、监控及基础设施设计。

## 2. 核心原则

### 2.1 记录事件，而不是代码执行过程

日志应描述有意义的业务事件或系统事件，而不是简单记录函数调用和代码执行轨迹。

推荐：

```text
INFO payment-api req_123 payment_created order_id=ord_456 amount=99.00
```

不推荐：

```text
INFO payment-api req_123 entering create_payment
INFO payment-api req_123 calling validate_order
INFO payment-api req_123 validation completed
INFO payment-api req_123 exiting create_payment
```

只有在能够提供实际诊断价值时，才记录执行过程。

### 2.2 保持一致性

整个应用程序必须使用统一的：

- 日志格式。
- 字段命名。
- 日志级别语义。
- 消息组织方式。

同一类型的事件应具有相似的日志结构。

### 2.3 兼顾可读性与可解析性

日志既要便于人工阅读，也要具有稳定、可预测的结构，方便检索和解析。

避免使用随意拼接的格式和不一致的字段命名。

### 2.4 记录有价值的信息

每条日志至少应该能够回答以下一个问题：

- 发生了什么？
- 哪个操作受到影响？
- 操作结果是什么？
- 为什么发生？
- 涉及哪个业务对象或资源？

避免记录没有实际诊断价值的信息。

## 3. 日志格式

所有应用程序日志必须遵循以下格式：

```text
{timestamp} {level} {service} {operation_id} {message}
```

示例：

```text
2026-02-05T18:40:12.112Z INFO payment-api req_123 payment_created order_id=ord_456 amount=99.00
```

### 3.1 时间戳（timestamp）

- 必须使用 UTC 时区。
- 必须使用 ISO 8601 格式。
- 必须包含毫秒精度。
- 必须包含 UTC 标识符 `Z`。
- 必须由统一的日志格式化器生成。

格式：

```text
yyyy-MM-ddTHH:mm:ss.SSSZ
```

示例：

```text
2026-02-05T18:40:12.112Z
```

禁止使用本地时间或不包含时区信息的时间戳。

### 3.2 日志级别（level）

使用 Python `logging` 标准日志级别：

| 级别 | 用途 |
|---|---|
| DEBUG | 详细的诊断信息 |
| INFO | 正常的应用程序事件 |
| WARNING | 出现非预期情况，但操作仍然能够完成 |
| ERROR | 操作失败，需要关注或处理 |
| CRITICAL | 严重故障，可能导致应用程序或重要组件无法继续正常运行 |

必须使用 Python 标准名称 `WARNING` 和 `CRITICAL`，禁止使用 `WARN` 或 `FATAL`。

日志级别必须反映事件的实际严重程度，而不是简单根据代码是否进入异常分支决定。

参考场景：

| 场景 | 推荐级别 |
|---|---|
| 操作正常完成 | INFO |
| 正常的业务拒绝或校验失败 | INFO |
| 预期内的幂等冲突 | INFO |
| 缓存未命中 | DEBUG 或 INFO |
| 发生异常但通过降级成功完成操作 | WARNING |
| 依赖服务异常导致操作失败 | ERROR |
| 核心组件不可用，应用无法正常继续运行 | CRITICAL |

不要将所有异常都记录为 ERROR，也不要将正常业务行为记录为 WARNING。

### 3.3 服务名称（service）

服务名称必须：

- 使用小写 kebab-case。
- 能够明确标识所属服务或应用。
- 在同一个服务内保持一致。
- 不使用动态值。

示例：

```text
payment-api
user-service
order-worker
```

禁止使用：

```text
PaymentAPI
payment_api
payment-api-v2
```

除非版本确实属于服务标识的一部分，否则不要将版本号放入服务名称。

### 3.4 操作标识（operation_id）

`operation_id` 用于关联同一次逻辑操作产生的多条日志。

要求：

- 同一次逻辑操作的所有相关日志必须使用相同的 `operation_id`。
- 优先使用上游传入的有效关联标识。
- 没有上游标识时，在操作入口生成 UUID。
- 必须在操作生命周期内复用，不得为每条日志单独生成。
- 子操作应继承父操作的 `operation_id`。
- 不得使用 `-`、`unknown`、`none` 等占位值。
- 不得为了填充字段而伪造关联关系。

不同场景的标识来源：

| 场景 | 标识来源 |
|---|---|
| HTTP 请求 | request_id |
| 定时任务 | job_execution_id |
| 消息消费 | message_processing_id |
| 内部业务操作 | 入口处生成的 UUID |

注意：

`operation_id` 表示日志关联标识，不要求与底层 request_id、trace_id、job_id 或 message_id 使用相同的名称或语义。

如果一个业务操作跨越多个服务，应优先传递上游关联标识，确保日志能够串联。

## 4. 日志消息格式

日志消息（message）采用以下结构：

```text
Action Outcome [Reason] Context
```

各部分含义：

| 部分 | 含义 |
|---|---|
| Action | 发生了什么事件 |
| Outcome | 操作结果 |
| Reason | 结果产生的原因，可选 |
| Context | 相关业务上下文，可选 |

示例：

```text
payment_created order_id=ord_123 amount=99.00
```

```text
payment_rejected reason=insufficient_balance order_id=ord_123
```

```text
cache_refresh_failed reason=connection_timeout cache_name=user_profile
```

### 4.1 Action

Action 必须：

- 使用简洁、明确的事件描述。
- 优先使用过去分词或清晰的事件名称。
- 使用 snake_case。
- 能够独立表达发生的事情。

推荐：

```text
user_created
payment_completed
order_cancelled
cache_refresh_failed
```

不推荐：

```text
process
handle
execute
do_something
```

### 4.2 Outcome

Outcome 用于说明操作结果。

推荐使用：

```text
created
completed
rejected
failed
skipped
retried
```

避免使用含义模糊的描述，例如：

```text
success
done
finished
```

如果 Action 本身已经包含结果语义，可以不额外重复 Outcome。

### 4.3 Reason

Reason 用于说明操作结果的原因。

示例：

```text
payment_rejected reason=insufficient_balance
```

```text
request_rejected reason=invalid_signature
```

Reason 应尽量使用稳定、可检索的标识，而不是冗长的自然语言描述。

### 4.4 Context

Context 用于提供定位事件所需的上下文信息。

推荐使用 `key=value` 格式：

```text
payment_created order_id=ord_123 user_id=u_456 amount=99.00
```

要求：

- key 必须使用 snake_case。
- key 必须具有明确含义。
- 同一字段在不同日志中必须使用统一名称。
- 只记录与当前事件相关的信息。
- 避免重复记录已经存在于日志前缀中的信息。

推荐：

```text
order_id=ord_123
user_id=u_456
retry_count=3
duration_ms=120
```

不推荐：

```text
orderId=ord_123
user=123
count=3
time=120
```

## 5. 字段值格式

### 5.1 基本规则

默认情况下，字段值不加引号。

```text
user_id=u_123 retry_count=3 enabled=true
```

字段值包含空格或特殊字符时，必须使用双引号，并正确转义。

```text
error_message="connection timed out"
```

避免在单个字段中使用多行内容。

### 5.2 字段命名

字段名必须：

- 使用 snake_case。
- 简洁且具有明确语义。
- 在整个应用程序中保持一致。

推荐：

```text
request_id
user_id
order_id
error_code
duration_ms
```

### 5.3 缺失字段

没有对应信息的字段可以省略。

禁止随意使用以下占位值：

```text
unknown
none
null
-
```

如果字段确实存在且业务上需要表达空值，应明确其语义。

不要为了保持每条日志字段数量一致而填充无意义的数据。

## 6. 日志级别使用规范

### 6.1 DEBUG

用于详细的诊断信息。

适用场景：

- 关键分支的调试信息。
- 缓存命中或未命中详情。
- 需要排查的中间状态。
- 重要参数的非敏感摘要。

示例：

```text
DEBUG payment-api req_123 payment_validation_started order_id=ord_456
```

DEBUG 日志不应包含大量无意义的函数进入和退出记录。

### 6.2 INFO

用于正常的业务事件和系统事件。

适用场景：

- 业务操作成功。
- 任务开始或完成等有实际价值的生命周期事件。
- 正常的业务拒绝。
- 重要状态变化。

示例：

```text
INFO payment-api req_123 payment_created order_id=ord_456
```

不要在高频循环中无差别地记录 INFO 日志。

### 6.3 WARNING

用于非预期情况，但当前操作仍然能够完成的场景。

适用场景：

- 依赖服务短暂不可用，但降级成功。
- 重试后操作成功。
- 使用备用数据完成操作。
- 非关键资源加载失败。

示例：

```text
WARNING payment-api req_123 payment_completed_fallback reason=primary_gateway_unavailable
```

### 6.4 ERROR

用于操作失败且需要关注的场景。

适用场景：

- 业务操作因系统错误失败。
- 外部依赖调用失败，导致当前操作无法完成。
- 数据库操作异常。
- 非预期程序异常。

示例：

```text
ERROR payment-api req_123 payment_failed error_code=PAYMENT_GATEWAY_ERROR order_id=ord_456
```

ERROR 日志必须包含：

- 清晰的失败事件。
- 能够定位问题的上下文。
- `error` 或 `error_code` 等错误信息。

### 6.5 CRITICAL

用于严重故障。

适用场景：

- 核心组件无法初始化。
- 关键资源不可用，应用无法正常运行。
- 系统处于无法继续正常工作的状态。

示例：

```text
CRITICAL payment-api startup_failed error_code=DATABASE_UNAVAILABLE
```

CRITICAL 不应仅仅因为异常严重或异常类型特殊而使用，必须结合对系统运行状态的实际影响判断。

## 7. 异常与堆栈信息

### 7.1 基本原则

异常日志应提供足够的信息来定位问题。

但并非所有异常都需要输出堆栈。

- 预期内的业务异常通常不需要堆栈。
- 非预期程序异常应在适当的异常处理边界记录堆栈。
- 不要在多个层级重复记录同一个异常。
- 需要记录堆栈时，使用 Python `logging` 提供的异常信息能力。

### 7.2 推荐方式

在异常处理上下文中使用：

```python
try:
    process_payment()
except PaymentGatewayError as exc:
    logger.exception(
        "payment_failed error_code=%s order_id=%s",
        exc.code,
        order_id,
    )
    raise
```

如果不需要堆栈，可以记录必要的异常信息：

```python
try:
    process_payment()
except PaymentRejectedError as exc:
    logger.info(
        "payment_rejected reason=%s order_id=%s",
        exc.reason,
        order_id,
    )
```

### 7.3 避免重复记录

异常应尽量在能够做出处理决策的边界记录。

不要在每一层捕获异常后都记录一次相同的错误。

不推荐：

```python
def process_order():
    try:
        create_payment()
    except Exception:
        logger.exception("payment_failed")
        raise


def handle_request():
    try:
        process_order()
    except Exception:
        logger.exception("request_failed")
        raise
```

如果两处记录的是同一个异常，通常只应在最终处理边界记录一次完整堆栈。

### 7.4 堆栈输出

- 堆栈信息应与对应异常事件关联。
- 仅在具有诊断价值时输出。
- 不得将堆栈作为普通业务消息的一部分拼接。
- 避免在没有必要的情况下重复输出完整异常信息。

## 8. 禁止记录的信息

日志不得直接记录敏感信息或不必要的大量数据。

### 8.1 敏感信息

禁止记录：

- 密码。
- API Key。
- Access Token。
- Refresh Token。
- 私钥和密钥。
- 数据库连接凭据。
- 完整认证信息。
- 其他能够直接用于身份验证或访问系统的凭据。

对于个人敏感信息，应根据项目要求进行脱敏或避免记录，例如：

- 身份证号码。
- 银行卡号码。
- 手机号码。
- 电子邮箱。
- 其他个人身份信息。

### 8.2 大型数据

禁止直接记录：

- 完整 HTTP 请求或响应对象。
- 完整数据库记录。
- 大型 JSON 对象。
- 文件内容。
- 大型列表或字典。
- 未经处理的第三方响应内容。

确实需要诊断时，只记录必要的摘要和标识符。

### 8.3 高频日志

避免：

- 在高频循环中记录 INFO。
- 对每条数据处理记录完整上下文。
- 重复记录同一事件。
- 记录没有诊断价值的函数调用轨迹。

### 8.4 异常内容

不要默认认为异常消息是安全的。

异常内容可能包含：

- 用户输入。
- 请求参数。
- 数据库连接字符串。
- Token 或凭据。
- 第三方服务返回的敏感信息。

记录异常时应避免将完整请求对象、响应对象或其他敏感数据直接传入日志。

## 9. Python Logging 使用要求

Python 应用程序必须使用标准库 `logging` 或项目已有的日志封装。

### 9.1 使用参数化日志

推荐：

```python
logger.info(
    "payment_created order_id=%s amount=%s",
    order_id,
    amount,
)
```

不推荐：

```python
logger.info(f"payment_created order_id={order_id} amount={amount}")
```

参数化日志可以避免在日志级别被过滤时进行不必要的字符串格式化。

### 9.2 使用正确的日志方法

| 场景 | 方法 |
|---|---|
| DEBUG | `logger.debug()` |
| INFO | `logger.info()` |
| WARNING | `logger.warning()` |
| ERROR | `logger.error()` |
| CRITICAL | `logger.critical()` |
| 捕获异常并记录堆栈 | `logger.exception()` |

`logger.exception()` 应在 `except` 代码块中使用。

### 9.3 统一注入公共字段

以下字段应由统一日志配置自动注入：

- timestamp
- level
- service
- operation_id

业务代码不应在每条日志中手动拼接这些公共字段。

可以通过 Python `logging.Formatter`、`Filter`、`LoggerAdapter` 或项目已有封装实现。

必须确保格式化时所有必需字段均存在，避免因缺少字段导致日志格式化失败。

### 9.4 遵循项目现有日志实现

如果项目已经提供统一的 Logger、日志适配器或上下文传递机制：

- 必须优先使用现有实现。
- 不要重复创建日志配置。
- 不要自行引入另一套日志封装。
- 不要绕过公共字段注入机制。

## 10. 格式稳定性

日志格式属于应用程序的稳定输出契约。

必须遵守：

- 不得随意修改日志前缀字段顺序。
- 不得随意改变公共字段名称。
- 不得随意改变时间戳格式。
- 不得为相同事件使用不同的消息结构。
- 修改日志格式时，应考虑现有日志检索和解析逻辑。

新增字段应尽量保持向后兼容。

如果某项信息不是所有事件都需要，可以作为可选 Context 字段，而不是修改公共日志格式。

## 11. 最低合规要求

所有新增或修改的日志必须满足以下要求：

1. 使用统一的日志格式。
2. 使用 UTC 时间戳，包含毫秒和时区标识。
3. 使用 Python 标准日志级别。
4. 使用有效且可关联的 `operation_id`。
5. 使用明确的事件描述。
6. Context 字段采用统一的 snake_case 命名。
7. ERROR 和 CRITICAL 日志包含必要的错误信息和上下文。
8. 非预期异常在适当的处理边界记录堆栈。
9. 不记录密码、Token、密钥等敏感信息。
10. 不记录没有实际价值的高频日志或大型对象。
11. 优先使用项目已有的日志配置和封装。

## 12. 核心原则总结

日志规范的核心不是记录更多信息，而是记录正确的信息。

每条日志都应当：

- 描述一个有意义的事件。
- 使用统一的格式。
- 具备正确的关联标识。
- 提供足够的诊断上下文。
- 使用准确的日志级别。
- 避免敏感信息和无意义内容。

**优先保证日志的一致性、可读性和可检索性，而不是追求日志数量或复杂程度。**