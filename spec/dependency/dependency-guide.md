---
version: 1.0.0
last_updated: 2026-11-15
---

# 依赖管理规范（Dependency Guide）

适用：后端（Python / uv）、前端（Node / npm）、第三方服务与 SDK、工具链与系统包。

本文件管**决策与形态**：要不要引入、写什么版本范围、怎么组织、怎么移除、怎么审供应链。流水线里怎么装、怎么缓存、怎么自动提 PR 见 `spec/ci_cd/ci-cd-guide.md` 第 4 节；代码里怎么调用第三方见 `spec/module/module-guide.md` 与 `spec/frontend/frontend-guide.md`。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

---

## 0. 三条底线

1. **可复现**：同一 commit 在任何机器上装出同一套依赖。锁文件是唯一真源，手改锁文件等于破坏可复现性。
2. **可追溯**：每个多出来的包都能回答"谁引入的、为什么、能不能换"。传递依赖也算。
3. **可替换**：第三方只能在封装层出现。换 SDK、换供应商时，改动应集中在一个 `client` 文件，而不是散落 40 处。

依赖问题的代价不在安装，而在**升级时**：一个包卡住主版本，整条链都动不了。所以下面的规则普遍偏向"少而稳"，而不是"新而全"。

---

## 1. 版本与锁文件

| 对象 | 唯一真源 | 提交 | 禁止 |
| --- | --- | --- | --- |
| 后端依赖 | `backend/pyproject.toml` + `backend/uv.lock` | 两者**同一次提交** | 只改 lock 不改 pyproject；手编 lock |
| 前端依赖 | `frontend/package.json` + `frontend/package-lock.json` | 同上 | 手编 lock；混用 pnpm/yarn 的 lock |
| Python 解释器 | `backend/.python-version` | 是 | 在 CI YAML 里硬编码版本 |
| Node 解释器 | 仓库根 `.nvmrc` + `package.json` 的 `engines.node` | 是 | 依赖 runner 预装版本 |

规则：

- MUST 锁文件入库，且与声明文件在同一次提交里；二者不一致的提交不允许合并。
- MUST NOT 手工编辑 `uv.lock` / `package-lock.json`。要改版本就用 `uv add` / `npm install` 让它重新解析。
- MUST NOT 删除锁文件"重新生成一版"。那会把所有传递依赖悄悄升级，且没人看得懂 diff。
- MUST NOT 在仓库内保留第二份锁文件（`requirements.txt`、`pnpm-lock.yaml`、`yarn.lock`）。迁移包管理器要一次迁完并删旧的。

### 1.1 版本说明符策略

| 场景 | 后端（pyproject） | 前端（package.json） | 理由 |
| --- | --- | --- | --- |
| 普通库依赖 | `>=1.4,<2` | `^1.4.2` | 允许兼容升级，主版本锁死 |
| 0.x 版本库（API 未稳定） | `>=0.4.1,<0.5` | `~0.4.1` | 0.x 的次版本就是破坏性变更 |
| 已知有问题的版本 | `!=1.4.3` | 同左 | 显式排除，不靠"别升到那版"的口头约定 |
| 与外部契约强绑定的 SDK | `>=2.1,<2.2` | `~2.1.3` | 只吃补丁，避免上游改字段 |
| 工具链（构建/测试） | 同上 | `^` 或精确 | 精确更适合"构建产物必须一致" |

- MUST 声明**兼容范围**，不写 `*`、`latest`、空字符串。
- MUST NOT 在声明文件里写死补丁版本（`==1.4.2`）来"保证一致"——一致性由锁文件负责，写死只会让安全补丁永远升不上来。
- SHOULD 主版本上限显式写出（`<2`）。省略上限时，一次意外的 `2.0` 会让 CI 在别人的 PR 上炸。
- MUST 版本范围与锁文件里的实际版本对得上；`uv lock --check` 与 `npm ci` 会验证这一点。

---

## 2. 后端依赖（Python / uv）

### 2.1 只用 uv，不用 pip

| 动作 | 命令 | 禁止 |
| --- | --- | --- |
| 加运行时依赖 | `uv add httpx` | `pip install httpx` |
| 加开发依赖 | `uv add --dev pytest` | 装到系统 Python |
| 加分组依赖 | `uv add --group test pytest-asyncio` | 手改 `pyproject.toml` 后不跑 `uv lock` |
| 移除 | `uv remove httpx` | 只删 import 不删声明 |
| 同步环境 | `uv sync` | `pip install -e .` |
| 一次性工具 | `uv run --with ruff ruff check` | 为跑一次脚本加永久依赖 |

- MUST 用 `uv add` / `uv remove` 修改依赖，让 `pyproject.toml` 与 `uv.lock` 同步更新。
- MUST 每个项目只有一个 `.venv`（仓库根或 `backend/` 下），由 uv 管理。禁止 `python -m venv` 另建一份。
- MUST NOT 在 CI 里 `uv add` / `uv lock` / `uv pip install`（见 ci-cd 规范第 4 节）。
- MUST NOT 用 `--no-deps` 安装；缺的传递依赖会在运行时才炸。

### 2.2 依赖分组

```toml
[project]
dependencies = ["fastapi>=0.115,<1", "sqlalchemy[asyncio]>=2.0,<3"]

[dependency-groups]
dev = ["ruff", "mypy"]
test = ["pytest", "pytest-asyncio", "httpx", "asgi-lifespan"]
docs = ["mkdocs"]
```

| 组 | 放什么 | 生产镜像是否安装 |
| --- | --- | --- |
| `project.dependencies` | 运行期必须的库 | 是 |
| `dev` | 格式化、类型检查、调试工具 | 否 |
| `test` | 测试框架与测试替身 | 否 |
| `docs` | 文档构建 | 否 |

- MUST 生产镜像只装主依赖（`uv sync --no-dev`，或按 Dockerfile 显式指定组）。
- MUST NOT 把测试库、lint 工具放进 `project.dependencies`；那会让生产镜像多背几十兆和一份攻击面。
- SHOULD 组名固定为 `dev` / `test` / `docs`，不自创 `misc`、`tools`（分不清该不该装）。

### 2.3 extras 与平台标记

- MUST 需要可选能力时用 extras（`sqlalchemy[asyncio]`），不把可选依赖写进主列表。
- MUST 平台相关依赖加环境标记，不要"先装上再说"：

```toml
dependencies = [
  "uvloop>=0.21,<1; sys_platform != 'win32'",
]
```

- SHOULD 只在确实需要时开 extras；一个 extra 引入十个包时，评估是否直接用底层包。

### 2.4 明确禁止的依赖形态

| 形态 | 为什么禁 | 例外 |
| --- | --- | --- |
| `git+https://...` 直连 | 不可复现、无版本语义、上游 force push 就变 | 上游未发布且必须用；需在 `docs/deps/decisions.md` 记录 commit SHA |
| 本地路径依赖（`-e ../xxx`） | 别人 clone 装不上 | 仅 monorepo 内部包，且 CI 同仓构建 |
| 私有 wheel 文件入库 | 二进制不可审、仓库膨胀 | 不允许 |
| 未维护的 fork | 安全补丁收不到 | 需记录接管计划与期限 |

---

## 3. 前端依赖（Node / npm）

### 3.1 dependencies 与 devDependencies

| 判定 | 放哪 |
| --- | --- |
| 运行期在浏览器或 Node 服务端被 import | `dependencies` |
| 只在构建/测试/lint 时用（`vitest`、`eslint`、`typescript`、`@types/*`） | `devDependencies` |
| 由构建打包进产物的框架（`next`、`react`） | `dependencies` |
| shadcn 生成的组件 | **都不是**（源码，见 3.5） |

- MUST 放错组会被 `npm ci --omit=dev` 暴露：生产镜像少包、启动即崩。加依赖后本地跑一次 `npm ci --omit=dev && npm run build` 自检。
- MUST `@types/*` 一律 `devDependencies`。

### 3.2 版本与 lockfile

- MUST `npm ci` 安装（严格按 lockfile），不用 `npm install`；后者会改写 lockfile。
- MUST 提交 `package-lock.json`，且 `lockfileVersion` 统一（同一 Node 大版本生成）。
- MUST `engines.node` 与 `.nvmrc` 主版本一致，CI 用 `node-version-file` 读取。
- SHOULD `packageManager` 字段写明包管理器与版本（`"npm@10.9.2"`），避免 corepack 猜。
- MUST NOT 混用包管理器；仓库里出现 `pnpm-lock.yaml` 或 `yarn.lock` 视为错误。

### 3.3 对等依赖（peer）必须对齐

React / Next 这类框架对 peer 版本敏感，装错不会报错，只会在运行时出现诡异的 hooks 错误。

- MUST `react`、`react-dom` 主次版本完全一致。
- MUST `next` 与 `react` 的支持矩阵满足官方要求（升级 Next 时同时核对 React 版本）。
- MUST `npm ls react react-dom` 无 `UNMET PEER DEPENDENCY` 或重复版本；出现重复版本时用 `overrides` 收敛，并在 PR 说明原因。

```json
{
  "overrides": {
    "react": "19.2.0",
    "react-dom": "19.2.0"
  }
}
```

### 3.4 安装脚本

- MUST 仓库 `.npmrc` 设 `ignore-scripts=true`，需要安装脚本的包按需在 CI 里显式放行。
  理由：`postinstall` 是供应链投毒最常用的入口，默认执行等于默认信任。
- MUST NOT 引入依赖 postinstall 下载二进制的包（`*-bin`、`sharp` 类）时不加评估；确需时锁版本并记录。
- SHOULD 需要 `playwright install` 这类下载步骤时，放在 CI 显式步骤里，不依赖包脚本。

### 3.5 shadcn/ui 是源码，不是依赖

- MUST 把 shadcn 生成的 `components/ui/*` 当作**本项目源码**：入库、走 review、可改。
- MUST 升级方式是用 CLI 重新生成并逐个人工比对 diff（`npx shadcn@latest add <component> --overwrite` 前先看 diff），不是升 `package.json` 版本。
- MUST `components.json` 入库，锁定样式来源与别名；改了要说明。
- MUST NOT 引入第二套 UI 库（详见 `spec/frontend/frontend-guide.md` 8.1）。

### 3.6 体积与重复

- SHOULD 设首屏 JS 预算（gzip 后 ≤ 200 KB），`next build` 输出里超出即优化或换库。
- MUST NOT 为单个函数引入整包（`lodash` 用 `lodash-es` 单函数导入，或直接写 3 行）。
- SHOULD 引入前 `npx depcheck` / `knip` 确认没有已存在但没用上的同类包。

---

## 4. 第三方服务与 SDK

"第三方依赖"不只是包，还包括模型、支付、短信、对象存储、地图这类外部服务。它们的耦合比包更难拆。

### 4.1 只能出现在封装层

- MUST 第三方 SDK 只能在 `app/integrations/<name>/client.py`（后端）或 `src/lib/<name>.ts`（前端）里 import。
- MUST NOT 在 router / service / 组件里直接 `import openai`、`import stripe`。理由：换供应商、加超时、加重试、加埋点都只有一个地方要改。
- MUST 封装层对外暴露**本项目的类型**，不把 SDK 的响应对象透传出去：

```python
# app/integrations/payment/client.py
class PaymentClient:
    async def charge(self, order_id: str, amount_cents: int) -> PaymentResult:
        """对外只返回 PaymentResult，不透传 SDK 对象。"""
```

### 4.2 超时、重试、降级必须显式

| 项 | 约束 |
| --- | --- |
| 超时 | MUST 每个外部调用都设连接超时与读超时，从配置读，不写死在代码里 |
| 重试 | MUST 只对幂等请求重试，且设上限与退避；非幂等（下单、扣款）禁止自动重试 |
| 熔断/降级 | SHOULD 有明确降级行为（返回缓存、排队、报可读错误），不允许无限等待 |
| 幂等 | MUST 写操作带幂等键 |

- MUST 这些参数可配置（环境变量或 settings），并在 `.env.example` 里列出默认值。
- MUST NOT 依赖 SDK 的默认超时（各家 60s~无限制不等）。

### 4.3 版本与弃用

- MUST 与外部契约强绑定的 SDK 只吃补丁版本（见 1.1）。
- MUST 记录每个第三方服务的**弃用跟踪**：`docs/deps/third-party.md` 一服务一行，写 SDK 版本、最近一次核对日期、已知弃用项与迁移计划。
- SHOULD 每季度核对一次各家 changelog / deprecation 公告；只靠"能跑"发现不了下线。

### 4.4 凭据

- MUST 凭据只从环境变量或密钥管理读，不写进代码、不写进 `package.json`、不写进镜像。
- MUST `.env.example` 只列键名与格式说明，不含真实值。
- MUST NOT 把凭据打进前端 bundle（`NEXT_PUBLIC_*` 是公开的）。

---

## 5. 引入新依赖的准入

### 5.1 先问四个问题

按顺序问，任何一个"是"就停：

1. **不引能不能做？** 标准库 / 已有依赖已经覆盖 → 不引。
2. **能不能用已有依赖组合出来？** 已有 ORM 能做的不再引一个查询库。
3. **自己写 50 行能不能解决？** 能，且逻辑稳定 → 自己写；否则引。
4. **这个包半年后还在吗？** 见 5.2。

### 5.2 评估清单（引入前必过）

| 维度 | 红线 | 怎么查 |
| --- | --- | --- |
| 维护状态 | 近 12 个月无提交、无发版 | 仓库 commit / release 页 |
| 采用度 | 周下载量极低且无知名使用方 | PyPI / npm 统计 |
| 许可证 | GPL/AGPL 进闭源产品；无 LICENSE | 仓库 LICENSE 文件 |
| 传递依赖 | 引入 1 个包带进 20+ 包 | `uv tree` / `npm ls --all` |
| 体积 | 前端单包 gzip > 50 KB 且非核心 | bundlephobia / `next build` |
| 安全 | 有未修的 high/critical CVE | 见第 7 节 |
| 可替代 | 官方 SDK vs 社区封装 | 优先官方 |
| 退出成本 | 只在一处使用 vs 渗透全项目 | 先设计封装层 |

- MUST 命中任一红线时，必须写下"为什么仍然引入"以及缓解措施，否则不引入。
- MUST 传递依赖数超过 20 的包，先找轻量替代（如用 `httpx` 而不是带一堆插件的 HTTP 全家桶）。

### 5.3 决策要落盘

`docs/deps/decisions.md`，一依赖一行。它不是在写文档，是在回答"半年后为什么有这个东西"：

```markdown
| 日期 | 包 / 服务 | 端 | 为什么需要 | 考虑过的替代 | 风险与缓解 | 决定人 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-15 | `tenacity` | 后端 | 统一重试策略，避免各处手写 while | 自写（约 80 行，需处理退避与抖动） | 低：仅封装层使用 | 张三 |
| 2026-11-15 | `@tanstack/react-table` | 前端 | 服务端分页表格 | 手写（排序/筛选/虚拟滚动代价高） | 中：锁定主版本，升级需回归列表页 | 李四 |
```

- MUST 每个直接依赖都能在表里找到一行；`uv tree` 里出现但表里没有的直接依赖视为未准入。
- MUST 移除依赖时同步删掉该行（表与声明文件一致）。

### 5.4 一次性工具不要变成项目依赖

- MUST 只为跑一次而需要的能力用 `uv run --with <pkg>` / `npx <pkg>`，不写进 `pyproject.toml` / `package.json`。
- MUST NOT 把 `npx some-tool@latest` 写进 CI；CI 里必须固定版本（见第 8 节）。

---

## 6. 升级

### 6.1 三类升级

| 类型 | 节奏 | 回归范围 |
| --- | --- | --- |
| 补丁（`1.4.2 → 1.4.3`） | 每周自动提 PR | 受影响模块单测 + 全量单测 |
| 次版本（`1.4 → 1.5`） | 每两周，按批 | 上述 + 接口测试 + 该依赖相关 E2E |
| 主版本（`1.x → 2.x`） | 单独排期，不批量 | **全部单测 + 全部 E2E**（见 `spec/testing/regression-testing-guide.md` 6 节第 2 条） |

- MUST 主版本升级单独一个 PR，写明破坏性变更清单与迁移动作。
- MUST 升级 PR 附上游 changelog 的相关段落，不只贴链接。
- MUST NOT 在业务功能 PR 里顺手升依赖（混合变更无法回滚，也无法判断是谁引入的失败）。

### 6.2 自动化配置约束

- MUST 开启 Dependabot 或 Renovate，覆盖：Python（uv）、npm、Docker 基础镜像、GitHub Actions。
- SHOULD 分组：补丁合成一个 PR，主版本各自独立。
- SHOULD 设 cooldown（新版本发布 3~7 天后再提），避开刚发布的破坏性版本。
- MUST 自动合并只允许：patch 级 + 全部检查通过 + 不涉及 `spec/**` / `.github/**` / 安全敏感文件。
- MUST 同时存在的升级 PR 不超过 5 个（并发多了没人真正 review）。
- SHOULD 冻结窗口内（发布前 24 小时）暂停合并依赖升级。

### 6.3 升级后必须做的事

- MUST 更新 `docs/deps/decisions.md` 里的版本备注（若该行记录了版本约束）。
- MUST 该依赖有封装层时，跑一遍封装层的契约测试（外部返回结构变了要在这里暴露）。
- MUST 锁文件 diff 里出现"未预期的包新增/删除"时，查清是谁引入的，不直接合并。

---

## 7. 移除与清理

- MUST 用 `uv remove <pkg>` / `npm uninstall <pkg>` 移除，让声明与锁文件同步。
- MUST 移除后全仓搜一遍残留：`grep -rn "import <pkg>"` / `grep -rn "from <pkg>"`，以及动态导入与字符串引用。
- MUST 清理对应配置（`.npmrc`、pytest 插件列表、`next.config` 里的插件、类型引用）。
- MUST 同步删掉 `docs/deps/decisions.md` 的行。
- SHOULD 定期（每季度）跑孤儿检测：

```bash
uv tree --outdated                     # 后端：可升级项
npm outdated                           # 前端：可升级项
npx depcheck                           # 前端：声明了但没用的依赖
npx knip                               # 前端：没用的文件/导出/依赖
```

- MUST NOT 手工从 lockfile 里删传递依赖；它会被下次解析加回来，且中间状态不可复现。

---

## 8. 工具链与系统依赖

| 对象 | 锁定方式 | 与生产一致性 |
| --- | --- | --- |
| Python | `backend/.python-version`（主次版本） | 与生产镜像主版本一致 |
| Node | 根 `.nvmrc` + `engines.node` | 与生产镜像主版本一致 |
| uv | CI 里写具体版本，不写 `latest` | — |
| npm | `packageManager` 字段 | — |
| 基础镜像 | 按 digest 固定（`postgres:18@sha256:...`） | 是 |
| 系统包（`libpq`、字体、`curl`） | Dockerfile 里 apt 装，版本随基础镜像；不 `apt upgrade` | 是 |
| 浏览器（Playwright） | `@playwright/test` 版本决定浏览器版本，锁在 lockfile | CI 与本地同版本 |

- MUST NOT 依赖 runner 预装的任何版本。
- MUST NOT 在 Dockerfile 里跑 `apt-get upgrade`：不可复现，且会让镜像在两周后与测试时不同。
- MUST 生产镜像与 CI 的 Node / Python 主版本一致；不一致时以生产为准。

---

## 9. 供应链安全

### 9.1 源

- MUST 依赖只从可信索引安装：PyPI / npm 官方，或公司私有源；私有源用 `[[tool.uv.index]]` / `.npmrc` 显式声明。
- MUST NOT 使用 HTTP 源；必须 HTTPS。
- MUST NOT 在命令行临时加 `--index-url`（会绕过项目配置，且不进版本控制）。
- SHOULD 私有源配代理缓存时，保留上游签名/哈希校验，不只是"能装就行"。

### 9.2 完整性

- MUST 保留锁文件里的哈希（`uv.lock` 的 `hash`、`package-lock.json` 的 `integrity`）。删掉哈希等于放弃完整性校验。
- MUST CI 安装用"严格按锁文件"的模式（`uv sync --locked`、`npm ci`），不允许"锁文件过期就用最新的"。
- SHOULD 发布产物附 SBOM（`syft` 可直接读 `uv.lock` / `package-lock.json`，或用 `npm sbom`），与镜像 digest 一起归档。

### 9.3 新包与拼写仿冒

- MUST 满足任一条件的新包，安装前人工审查源码：发布不足 30 天、仓库星标极少、维护者只有一人、包名与知名包高度相似、无源码仓库链接。
- MUST 核对包名与官方文档一致（`reqeusts`、`python-dateutil` vs `dateutil` 这类拼写陷阱）。
- SHOULD 内部维护"已审包"清单时，写明审查日期与审查人。

### 9.4 安装脚本

- MUST npm 侧默认 `ignore-scripts=true`（见 3.4）。
- MUST Python 侧不使用需要执行安装脚本的包；确需时在 CI 里显式允许并记录。

### 9.5 漏洞响应

| 等级 | 响应时限 | 处理 |
| --- | --- | --- |
| critical | 24 小时内评估，7 天内修复或隔离 | 阻断发布 |
| high | 7 天内评估，30 天内修复 | 阻断发布 |
| medium | 90 天内修复 | 记录，按批次处理 |
| low | 下次升级时处理 | 记录 |

- MUST 无法立即修复时写豁免，且带到期日：

```toml
# osv-scanner.toml
[[IgnoredVulns]]
id = "GHSA-xxxx-xxxx-xxxx"
ignoreUntil = 2026-12-31
reason = "上游无修复版本；该路径仅内部工具调用，不暴露公网"
```

- MUST NOT 用无限期豁免（无 `ignoreUntil`）让扫描变绿。

---

## 10. 禁止事项汇总

- MUST NOT 手改锁文件、删除锁文件重生成。
- MUST NOT 在 CI 里 `uv add` / `uv lock` / `npm install` / `pip install`。
- MUST NOT 用 `*`、`latest`、`git+`、本地路径作为生产依赖（除第 2.4 节例外并登记）。
- MUST NOT 把测试/lint 工具放进运行期依赖。
- MUST NOT 在业务代码里直接 import 第三方 SDK。
- MUST NOT 引入第二套同功能依赖（两个 HTTP 客户端、两个日期库、两个状态库）。
- MUST NOT 在同一仓库混用包管理器。
- MUST NOT 把凭据写进依赖配置、锁文件、Dockerfile。
- MUST NOT 依赖 runner 预装版本或 `:latest` 镜像。
- MUST NOT 无到期日的漏洞豁免。

---

## 11. 检查清单

**引入依赖时**

- [ ] 四个问题都问过（不引 / 已有依赖 / 自写 50 行 / 半年后还在吗）。
- [ ] 评估清单逐项过，红线项写了理由与缓解。
- [ ] 版本范围符合 1.1 的策略（有上限、无 `*`）。
- [ ] 放对分组（运行期 / dev / test），生产镜像不需要它就不进主依赖。
- [ ] `docs/deps/decisions.md` 加了一行。
- [ ] 前端额外确认：无 peer 冲突、不依赖 postinstall、体积可接受。

**升级依赖时**

- [ ] 单独 PR，附 changelog 摘要。
- [ ] 回归范围按 6.1 升级（主版本跑全量单测 + 全量 E2E）。
- [ ] 锁文件 diff 里没有未预期的新增/删除包。
- [ ] 封装层的契约测试通过。

**移除依赖时**

- [ ] 用包管理器移除，声明与锁文件同步。
- [ ] 全仓无残留 import 与配置引用。
- [ ] 删掉了 `decisions.md` 对应行。

**季度体检**

- [ ] `uv tree --outdated` / `npm outdated` 无高危滞后。
- [ ] `depcheck` / `knip` 无未使用依赖。
- [ ] 漏洞扫描无超期未修项；豁免均有到期日。
- [ ] 第三方服务弃用公告核对过，`docs/deps/third-party.md` 已更新。
