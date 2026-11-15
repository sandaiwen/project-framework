---
version: 2.0.0
last_updated: 2026-11-15
---

# Alembic 迁移规范（Alembic Migration Guidelines）

本规范用于约束项目中数据库结构变更和数据迁移的编写、执行与维护。

核心目标：

- 迁移必须具有明确的执行顺序。
- 迁移应当具备可回滚能力。
- 迁移文件命名清晰，历史记录一目了然。
- 数据迁移必须考虑重复执行和失败恢复。
- 尽量使用 Alembic 原生能力，不引入不必要的复杂机制。
- 避免无业务价值的迁移重构。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。
---

## 一、目标与基本原则

### 1.1 核心目标

- 数据库结构变更必须通过迁移文件管理。
- 迁移文件必须按顺序排列，方便查看和维护。
- 每个迁移必须明确升级和回滚行为。
- 迁移执行结果必须可追踪。
- 避免手动修改数据库结构而不生成迁移记录。

### 1.2 基本原则

1. **可回滚**：结构变更必须提供对应的回滚操作。
2. **顺序明确**：迁移文件必须具有连续、清晰的顺序编号。
3. **职责单一**：一个迁移文件尽量只处理一组相关变更。
4. **简单直接**：优先使用 Alembic 和 SQLAlchemy 原生能力。
5. **安全可控**：迁移必须考虑数据完整性和执行失败的情况。
6. **不折腾**：不为简单迁移引入复杂抽象、额外框架或不必要的工具。

---

## 二、目录结构

统一使用以下目录结构：

```text
backend/
└── alembic/
    ├── env.py
    ├── alembic.ini
    └── versions/
        ├── 001_init_schema.py
        ├── 002_add_user_table.py
        ├── 003_add_user_avatar.py
        └── 004_seed_roles.py
```

要求：

- 所有迁移文件必须放在 `versions/` 目录中。
- `env.py` 负责 Alembic 迁移环境配置。
- `alembic.ini` 负责 Alembic 基础配置。
- 不得将迁移文件随意放在其他目录。
- 不得在迁移目录中存放与迁移无关的脚本。

---

## 三、Revision ID 规范

### 3.1 Revision ID 生成

- MUST 使用 Alembic 自动生成的 Revision ID。
- MUST NOT 自己编写数字 Revision ID。
- MUST NOT 将文件名中的顺序编号作为 Revision ID。
- `down_revision` MUST 正确指向父迁移的 Revision ID。

示例：

```python
revision = "a1b2c3d4"
down_revision = "9f8e7d6c"
```

### 3.2 Revision ID 与文件名的区别

Revision ID 和迁移文件名是两个不同的概念：

| 项目 | 用途 | 示例 |
|---|---|---|
| Revision ID | Alembic 内部标识迁移节点 | `a1b2c3d4` |
| down_revision | 标识当前迁移的父节点 | `9f8e7d6c` |
| 文件名 | 方便人类查看迁移顺序 | `002_add_user_table.py` |

说明：

- Alembic 使用 Revision ID 和 `down_revision` 构建迁移依赖图（DAG）。
- 文件名仅用于组织和查看，不决定迁移依赖关系。
- 手动重命名迁移文件时，不得修改 Revision ID 和 `down_revision`。
- 不得因为文件名编号变化而修改迁移依赖关系。

### 3.3 迁移依赖关系

正常情况下，迁移应形成单一、连续的迁移链。

```text
001_init_schema
       |
       v
002_add_user_table
       |
       v
003_add_user_avatar
       |
       v
004_seed_roles
```

- SHOULD 避免无必要的多分支迁移。
- 发现多个迁移分支时，应确认是否需要合并迁移。
- 不得为了调整文件顺序而随意修改已有迁移的父节点。

---

## 四、迁移文件命名规范

### 4.1 文件命名格式

统一使用：

```text
顺序号_英文描述.py
```

示例：

```text
001_init_schema.py
002_add_user_table.py
003_add_user_avatar.py
004_seed_roles.py
005_add_order_table.py
```

### 4.2 顺序编号要求

- MUST 从 `001` 开始。
- MUST 按照迁移创建顺序递增。
- MUST 使用三位数字，不足三位时补零。
- MUST 保持编号连续。
- MUST NOT 重复使用已有编号。
- MUST NOT 随意修改已发布迁移的文件编号。

### 4.3 描述命名要求

- MUST 使用英文小写字母和下划线。
- MUST 简短、明确地描述迁移内容。
- MUST NOT 使用中文、空格或无意义名称。

推荐：

```text
001_init_schema.py
002_add_user_table.py
003_add_user_email.py
004_create_order_table.py
```

不推荐：

```text
001_init.py
002_update.py
003_test.py
004_fix.py
```

### 4.4 文件名生成

Alembic 自动生成迁移文件后，可以手动调整文件名中的顺序编号和描述。

例如：

```bash
alembic revision --autogenerate -m "add user table"
```

生成后，根据当前迁移顺序重命名为：

```text
002_add_user_table.py
```

重命名时只修改文件名，不修改文件内部的 `revision` 和 `down_revision`。

---

## 五、迁移内容规范

### 5.1 基本结构

每个迁移文件 MUST 包含：

- `revision`
- `down_revision`
- `upgrade()`
- `downgrade()`

标准结构：

```python
"""Add user table."""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4"
down_revision = "9f8e7d6c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user")
```

要求：

- MUST 实现 `upgrade()`。
- MUST 实现 `downgrade()`。
- MUST NOT 使用 `raise NotImplementedError`。
- MUST NOT 留空的 `downgrade()`。
- MUST 保证迁移操作与实际数据库结构一致。

### 5.2 迁移职责

- SHOULD 一个迁移文件只处理一组相关的数据库变更。
- SHOULD 将无关的表结构变更拆分为独立迁移。
- MUST NOT 在一个迁移文件中混入大量无关操作。
- MUST NOT 将业务代码、接口调用或应用初始化逻辑放入迁移文件。

### 5.3 初始化迁移

初始化迁移文件统一命名为：

```text
001_init_schema.py
```

要求：

- MUST 明确创建初始数据库结构。
- MAY 手动编写 DDL。
- MAY 使用 `--autogenerate` 生成初始迁移，但必须人工检查。
- MUST NOT 在初始化迁移中混入业务数据。
- SHOULD 保持初始化迁移内容清晰、完整。

初始化迁移应主要包含：

- 表。
- 字段。
- 主键。
- 外键。
- 唯一约束。
- 普通索引。
- 必要的数据库约束。

### 5.4 表结构变更

常见变更包括：

- 创建表。
- 删除表。
- 添加字段。
- 删除字段。
- 修改字段类型。
- 修改字段默认值。
- 添加或删除索引。
- 添加或删除约束。

要求：

- MUST 在 `upgrade()` 中实现实际变更。
- MUST 在 `downgrade()` 中实现对应的撤销操作。
- MUST 考虑现有数据是否会影响迁移执行。
- 修改非空字段时，MUST 考虑已有记录如何获得合法值。
- 删除字段或表之前，MUST 确认是否存在需要保留的数据。

示例：

```python
def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "avatar",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "avatar")
```

### 5.5 数据迁移

数据迁移必须与普通结构迁移区分管理。

例如：

```text
004_seed_roles.py
005_migrate_user_status.py
```

要求：

- SHOULD 将独立的数据迁移放在单独的迁移文件中。
- MUST 考虑迁移重复执行、部分失败和数据一致性。
- SHOULD 使用 SQL 或 Alembic 操作完成简单的数据变更。
- MUST NOT 在迁移文件中调用项目 ORM 业务服务。
- MUST NOT 依赖当前应用代码中的业务逻辑完成历史数据迁移。

#### 5.5.1 幂等性

数据迁移 SHOULD 尽可能设计为幂等操作。

对于需要防止重复插入的数据，必须通过唯一约束、冲突处理或其他可靠机制保证不会产生重复记录。

例如 PostgreSQL：

```python
from sqlalchemy import text


def upgrade() -> None:
    op.execute(
        text("""
            INSERT INTO roles (name)
            VALUES ('admin')
            ON CONFLICT (name) DO NOTHING
        """)
    )
```

注意：

- `ON CONFLICT` 依赖数据库中存在对应的唯一约束或唯一索引。
- 不得仅通过先查询、再插入的方式假设并发情况下不会产生重复数据。
- 数据迁移必须明确依赖的数据库约束。
- 对于无法设计为幂等的迁移，必须明确其执行前提和失败恢复方式。

#### 5.5.2 数据回滚

对于初始化数据、字典数据或其他不要求恢复的业务数据，可以不执行实际数据回滚。

此时必须在迁移文件头部明确注明：

```python
# downgrade: not revert data
```

示例：

```python
"""Seed default roles."""

# downgrade: not revert data

from alembic import op
from sqlalchemy import text


revision = "a1b2c3d4"
down_revision = "9f8e7d6c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text("""
            INSERT INTO roles (name)
            VALUES ('admin')
            ON CONFLICT (name) DO NOTHING
        """)
    )


def downgrade() -> None:
    pass
```

注意：

- 只有明确允许数据保留时，才可以采用这种方式。
- `downgrade()` 不能缺失。
- 不得为了实现形式上的回滚而删除可能已经被业务使用的数据。
- 如果数据迁移修改了原有数据，必须评估是否能够安全恢复。
- 数据回滚策略必须在迁移编写时确定，不能留到回滚时再决定。

### 5.6 默认值与非空字段

新增字段时，必须考虑已有数据。

例如，向已有表添加非空字段：

```python
def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "status")
```

要求：

- MUST 保证已有记录满足新增字段的约束。
- SHOULD 优先使用数据库级 `server_default` 处理迁移期间的默认值。
- 如果需要复杂的数据转换，应先完成数据填充，再设置非空约束。
- 不得假设 Python 层默认值会自动应用于数据库迁移。

---

## 六、特殊情况处理

### 6.1 创建并发索引

PostgreSQL 创建普通索引时可能对表产生较强锁影响。

对于大表，确实需要降低索引创建期间的写入阻塞时，可以使用：

```sql
CREATE INDEX CONCURRENTLY
```

Alembic 中必须使用独立的自动提交事务块：

```python
from alembic import op


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY idx_user_email ON user(email)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY idx_user_email"
        )
```

要求：

- `CREATE INDEX CONCURRENTLY` MUST 在事务块之外执行。
- `DROP INDEX CONCURRENTLY` 同样 MUST 在事务块之外执行。
- 不得在普通事务中直接执行并发索引操作。
- 并发索引操作可能导致事务提交边界发生变化，应将其放在独立迁移中。
- 并发索引创建失败后，应检查数据库中是否留下无效索引，再决定如何重新执行。

说明：

并发索引主要适用于 PostgreSQL，不应将此写法直接套用到其他数据库。

### 6.2 循环外键

当多个表之间存在相互引用的外键时，应避免在创建表时直接形成复杂的循环依赖。

推荐分两步处理：

第一步：先创建表，不添加循环外键。

```python
def upgrade() -> None:
    op.create_table(
        "department",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("manager_id", sa.Integer(), nullable=True),
    )

    op.create_table(
        "employee",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
    )
```

第二步：创建外键约束。

```python
def upgrade() -> None:
    op.create_foreign_key(
        "fk_department_manager",
        "department",
        "employee",
        ["manager_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_employee_department",
        "employee",
        "department",
        ["department_id"],
        ["id"],
    )
```

实际编写时，应将两步操作合并到同一个迁移文件的 `upgrade()` 中。

回滚时按相反顺序删除外键和表：

```python
def downgrade() -> None:
    op.drop_constraint(
        "fk_employee_department",
        "employee",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_department_manager",
        "department",
        type_="foreignkey",
    )

    op.drop_table("employee")
    op.drop_table("department")
```

### 6.3 修改已有迁移

- MUST NOT 随意修改已经在共享环境或生产环境执行过的迁移文件。
- MUST NOT 为了修复历史迁移而直接修改数据库版本记录。
- 已发布迁移需要调整时，SHOULD 创建新的迁移文件完成修正。
- 仅在迁移尚未共享、尚未执行且没有其他依赖时，才可以考虑修改原迁移文件。

### 6.4 删除或重命名字段

- MUST 确认字段是否仍被应用代码使用。
- MUST 考虑旧版本应用与新版本数据库之间的兼容性。
- SHOULD 将字段重命名与删除操作拆分处理。
- 对存在生产数据的字段，MUST 评估数据丢失风险。

对于生产环境中的破坏性变更，优先采用分阶段迁移：

1. 新增新字段。
2. 迁移或同步数据。
3. 修改应用代码使用新字段。
4. 确认旧字段不再使用。
5. 在后续迁移中删除旧字段。

---

## 七、迁移生成与执行

### 7.1 生成迁移

自动生成结构迁移：

```bash
alembic revision --autogenerate -m "add user table"
```

生成空迁移：

```bash
alembic revision -m "seed default roles"
```

要求：

- MUST 在生成迁移后人工检查文件内容。
- MUST 确认 `upgrade()` 和 `downgrade()` 正确。
- MUST 检查是否存在意外的删除、修改或重复创建操作。
- MUST 检查 Revision ID 和父节点是否正确。
- MUST 检查迁移文件编号是否符合顺序。

### 7.2 查看迁移状态

查看当前数据库版本：

```bash
alembic current
```

查看迁移历史：

```bash
alembic history
```

查看最新迁移：

```bash
alembic heads
```

查看当前迁移图：

```bash
alembic history --verbose
```

### 7.3 执行迁移

升级到最新版本：

```bash
alembic upgrade head
```

回滚一步：

```bash
alembic downgrade -1
```

回滚到指定版本：

```bash
alembic downgrade <revision>
```

升级到指定版本：

```bash
alembic upgrade <revision>
```

---

## 八、封装脚本（backend/scripts/alembic）

仓库内提供一层封装脚本，通过 Alembic 管理数据库版本（升级 / 回滚）。本章说明脚本的位置、前置条件、各脚本职责与常用操作。

### 8.1 脚本与核心配置位置

```text
backend/scripts/alembic/
├── common.sh
├── upgrade.sh
└── downgrade.sh
```

核心配置：

- Alembic 配置：`backend/alembic.ini`
- 迁移目录：`backend/alembic/versions/`
- 数据库配置：`backend/config/app.yaml`

### 8.2 前置条件

1. **配置文件**：MUST 存在 `backend/alembic.ini`。
2. **Alembic 可用性**：系统需满足其一——已安装 `alembic` CLI，或 `python3 -m alembic` 可用。脚本会自动选择执行方式。
3. **数据库配置**：DB URL 取 `app.yaml -> db.alembic_url`；Schema 取 `db.schema`（由 `env.py` 控制）。

### 8.3 版本命名约定

与第三、四章一致：

- 迁移文件名使用顺序号（便于人工排序）。
- Alembic 内部 `revision` 使用自动生成 hash。

```text
001_init_schema.py            # 文件名顺序号
002_add_user.py

# 文件内部
revision = "a1b2c3d4e5f6"      # hash
down_revision = "prev_hash"
```

### 8.4 common.sh（基础工具层）

作用：提供执行 Alembic 的统一入口与安全校验。

核心能力：

- `run_alembic()`：统一调用 `alembic -c backend/alembic.ini`。
- `parse_to_arg`：解析 `--to <revision|head|base|-1>`。
- `require_target_revision_exists`：检查目标 revision 是否存在（保留 `head/base/-1` 特殊目标）。
- `require_single_head`：校验当前只有一个 head（避免分支未合并）。
- `get_current_revision`：获取当前数据库 revision。

### 8.5 upgrade.sh（升级流程）

作用：执行数据库向前迁移。

执行逻辑：

1. 解析 `--to <revision|head>`。
2. 校验目标 revision 存在。
3. 校验 single head。
4. 获取当前 revision。
5. 防止反向升级（目标在当前之前时拒绝执行）。
6. 执行：

```bash
alembic upgrade <target>
```

7. 若失败：尝试回滚到升级前 revision。

### 8.6 downgrade.sh（回退流程）

作用：执行数据库向后回滚。

执行逻辑：

1. 解析 `--to <revision|base|-1>`。
2. 校验目标 revision 存在。
3. 校验 single head。
4. 获取当前 revision。
5. 防止反向回退（目标在当前之后时拒绝执行）。
6. 执行：

```bash
alembic downgrade <target>
```

### 8.7 常用命令

查看当前版本：

```bash
alembic -c backend/alembic.ini current
```

查看 head：

```bash
alembic -c backend/alembic.ini heads
```

查看 migration 详情：

```bash
alembic -c backend/alembic.ini show <revision_hash>
```

使用封装脚本：

```bash
bash backend/scripts/alembic/upgrade.sh --to head
bash backend/scripts/alembic/downgrade.sh --to -1
```

直接使用 Alembic（高级用法，支持 schema）：

```bash
alembic -c backend/alembic.ini upgrade head -x schema=myschema
```

> 注意：封装脚本不转发 `-x` 参数。

### 8.8 使用脚本新建迁移的流程

1. **获取下一个文件序号**：

```bash
ls backend/alembic/versions
```

手动递增文件名前缀（如 `001` → `002`）。

2. **创建 migration**：

```bash
python3 -m alembic -c backend/alembic.ini revision \
  --autogenerate \
  -m "add user table"
```

创建后手动重命名文件为顺序号前缀（如 `002_add_user_table.py`）。

3. **审查文件**：检查 revision 为 Alembic hash、`down_revision` 正确、`upgrade` / `downgrade` 完整、类型 / 索引 / 约束符合规范。

4. **本地验证**：

```bash
bash backend/scripts/alembic/upgrade.sh --to head
bash backend/scripts/alembic/downgrade.sh --to -1
bash backend/scripts/alembic/upgrade.sh --to head
```

### 8.9 常见问题

**multiple heads**：说明存在分支未合并。

```bash
alembic merge ...
```

或手动修复 migration graph。

**revision not found**：检查 `backend/alembic/versions/`。

**rollback failure**：需手动恢复数据库或使用备份。

### 8.10 生产与协作要求

- 生产前必须备份数据库。
- CI 必须执行 migration 测试。
- 避免在高并发环境执行 DDL。
- 每个 migration 必须可回退。
- PR 必须说明变更与回滚策略。

---

## 九、每次迁移完成后的验证

每次编写迁移后，至少检查以下内容。

### 9.1 基础验证

```bash
# 查看当前数据库版本
alembic current

# 查看迁移历史
alembic history

# 升级到最新版本
alembic upgrade head

# 回滚一步
alembic downgrade -1

# 再次升级到最新版本
alembic upgrade head

# 确认当前版本
alembic current
```

### 9.2 验证要求

- MUST 确认迁移能够正常执行。
- MUST 确认 `downgrade()` 能够正常执行。
- MUST 确认回滚后能够再次升级。
- MUST 检查最终数据库结构是否符合预期。
- MUST 检查关键数据是否正确。
- 对数据迁移，应额外验证数据数量、唯一性和完整性。
- 对索引迁移，应确认索引是否真实创建成功。

注意：

上述命令应在专用测试数据库或可恢复的临时数据库中执行。

`upgrade → downgrade → upgrade` 通过，只能说明该测试环境下迁移的基本执行和回滚流程正常，不能代替生产数据兼容性、数据正确性和并发场景验证。

---

## 十、禁止事项

以下行为明确禁止：

1. MUST NOT 手动修改 `alembic_version` 表。
2. MUST NOT 自己编写数字 Revision ID。
3. MUST NOT 在迁移文件中编写与数据库变更无关的业务逻辑。
4. MUST NOT 在迁移文件中调用项目 ORM 业务服务。
5. MUST NOT 留空 `downgrade()`。
6. MUST NOT 使用 `raise NotImplementedError` 代替回滚实现。
7. MUST NOT 未经检查直接使用 `--autogenerate` 生成的迁移。
8. MUST NOT 随意修改已经发布或执行过的迁移文件。
9. MUST NOT 在没有评估数据影响的情况下删除表、字段或约束。
10. MUST NOT 在普通事务中直接执行 PostgreSQL 并发索引操作。
11. MUST NOT 在没有明确策略的情况下执行不可逆的数据变更。
12. MUST NOT 将多个无关的数据库变更堆积到一个迁移文件中。
13. MUST NOT 在没有确认数据库状态的情况下重复执行有破坏性的迁移操作。

---

## 十一、AI 编写迁移时的行为约束

本章节用于约束 AI 生成、修改和维护 Alembic 迁移文件时的行为。

### 11.1 优先检查现有迁移

- MUST 先检查现有迁移文件和迁移历史。
- MUST 确认当前最新 Revision ID。
- MUST 确认新迁移的 `down_revision` 正确。
- MUST 遵循现有文件命名和顺序编号。
- MUST NOT 假设项目中不存在尚未检查的迁移。

### 11.2 禁止编造数据库结构

- MUST NOT 擅自假设表名、字段名、索引名或约束名。
- MUST NOT 编造数据库中不存在的字段和约束。
- SHOULD 根据现有模型、迁移历史和实际数据库结构确认变更内容。
- 无法确认时，应明确说明不确定性。

### 11.3 禁止无需求重构

- MUST 只修改当前任务所需的迁移文件。
- MUST NOT 为了风格统一重写历史迁移。
- MUST NOT 随意调整已有迁移文件的顺序。
- MUST NOT 在没有明确需求的情况下合并或拆分历史迁移。
- SHOULD 优先使用局部、最小化修改。

### 11.4 必须检查回滚逻辑

- MUST 为每个结构变更编写对应的 `downgrade()`。
- MUST 检查升级和回滚操作是否相互对应。
- MUST 评估数据变更是否可逆。
- 不可逆的数据迁移 MUST 明确标注回滚策略。

### 11.5 如实验证

- SHOULD 在可用的测试数据库中执行迁移验证。
- MUST NOT 声称未执行的迁移已经通过。
- MUST NOT 虚构数据库结构或迁移执行结果。
- 无法执行验证时，应明确说明原因和未验证的内容。

---

## 十二、最低合规要求

每个新增或修改的迁移文件必须满足：

- [ ] 文件名符合顺序编号规范。
- [ ] Revision ID 使用 Alembic 自动生成的 hash。
- [ ] `down_revision` 指向正确的父迁移。
- [ ] 包含完整的 `upgrade()`。
- [ ] 包含明确的 `downgrade()`。
- [ ] 不包含无关业务逻辑。
- [ ] 已检查自动生成的迁移内容。
- [ ] 已考虑现有数据和约束的影响。
- [ ] 数据迁移已明确幂等性和回滚策略。
- [ ] 已在测试数据库中完成必要验证。

---

## 十三、最终原则

Alembic 迁移应当遵循以下原则：

1. 迁移文件必须有明确顺序。
2. Revision ID 必须由 Alembic 自动生成。
3. 文件名只负责展示顺序，不负责定义迁移依赖。
4. 每个迁移必须有明确的升级和回滚逻辑。
5. 数据迁移必须考虑幂等性和数据恢复策略。
6. 不随意修改已经发布的历史迁移。
7. 不引入没有实际价值的复杂机制。
8. 每次迁移完成后必须进行必要验证。

**最终原则：迁移文件应当简单、明确、可追踪、可回滚。不要为了迁移而增加不必要的复杂度。**

> migration 是数据库状态迁移系统，而不是业务逻辑执行器。
> upgrade / downgrade 是唯一合法变更路径。
> 脚本负责安全控制，Alembic 负责执行。

数据库迁移的价值在于安全地演进数据库结构和数据，而不是追求复杂的迁移设计。