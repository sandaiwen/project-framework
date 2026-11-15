---
version: 7.0.0
last_updated: 2026-11-15
---

# CI/CD 规范（CI/CD Guide）

本文件约束**代码从提交到生产**的整条链路：分支与提交、流水线阶段、依赖锁定、构建产物、环境与密钥、数据库迁移在流水线中的位置、部署与回滚、供应链安全、发布与度量。

技术栈为 **FastAPI + Next.js + PostgreSQL**。示例以 **GitHub Actions** 为准（`.github/workflows/` 按附录 A 落地时创建）；换 GitLab CI、Jenkins、Gitea Actions 时**语法可变，阶段划分与门禁条件不变**。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

## 0. 总纲

### 0.1 三项目标

| 目标 | 含义 | 反例 |
| --- | --- | --- |
| **可重复** | 同一个 commit 在任何时间、任何机器上产出同一份产物 | 每次部署重新构建镜像，依赖重新解析 |
| **可追溯** | 生产上跑的产物能反查到 commit、流水线运行、构建者 | 部署 `:latest`，出问题不知道跑的是哪版 |
| **可回滚** | 回退是一次**指针切换**，不是重新构建、不是 `git revert` 等 CI | 回滚靠改代码再走一遍流水线 |

### 0.2 流水线是通往生产的唯一路径

- MUST 生产环境只能通过流水线部署。禁止 SSH 到生产改代码、改配置、手工 `docker run`。
- MUST NOT 在 CI 里直连生产数据库做手工 SQL；唯一例外是本文第 7 章规定的迁移步骤。
- 紧急情况走 12.2 的 break-glass 流程，**事后必须补齐记录与 PR**。

### 0.3 门禁必须可判定

- MUST 每个门禁都对应一个**退出码**或一个**数值阈值**，能由机器判断通过与否。
- MUST NOT 设置"检查是否合理""确认影响可控"这类无法自动判定的门禁。
- 人工审批只用于两类事：**需要业务判断**（是否发版、是否接受风险）与**不可逆操作**（生产迁移）。

### 0.4 与其它规范的分工

CI/CD 不重新定义其它规范的内容，只规定"在流水线的哪一步执行、失败怎么办"。

| 关注点 | 由谁定义 | 本文件的位置 |
| --- | --- | --- |
| 跑哪些测试、分几层、覆盖率门槛 | `spec/testing/README.md` 第 2 节 | 只把该分层映射到工作流文件与阻断条件 |
| 回归集怎么登记、怎么看是否达标、什么级别能放行 | `spec/testing/regression-testing-guide.md` 第 5、10 节 | 只把它作为阶段 5 的门禁，要求发布时附回归报告 |
| 迁移文件怎么写、怎么命名、怎么回滚 | `spec/alembic/alembic-guide.md` | 只规定迁移在流水线中的**时序**与失败处置 |
| 代码结构、分层、依赖方向 | `spec/module/module-guide.md`、`spec/frontend/frontend-guide.md` | 不管 |
| 代码风格、类型、异常 | `spec/python/python-code-style-guide.md` | 只规定用哪些命令检查 |
| 要不要引某个依赖、版本范围怎么写、怎么升级与移除 | `spec/dependency/dependency-guide.md` | 只规定"用哪条命令装、怎么缓存、自动提 PR 落在哪" |
| 日志格式与字段 | `spec/logging/logging-guidelines.md` | 不管；需要新增发布版本字段时先改该规范 |
| 任务计划与验收标准 | `spec/plans/plan-writing-guide.md` | 部署失败产物归档到计划的 `artifacts/` |
| 提交信息格式，以及本地怎么切提交、暂存范围、失败重来 | `spec/git/commit-guide.md` | 只规定提交进入流水线之后的事（检查、合并、门禁），以及各 `type` 的流水线后果 |

---

## 1. 分支与提交

### 1.1 分支模型

采用 **trunk-based development**，`main` 永远处于可发布状态。

| 规则 | 说明 |
| --- | --- |
| MUST `main` 是唯一长期分支，任何时候都能部署 | 存在第二个长期分支就意味着有"未验证的集成点" |
| MUST 功能分支从 `main` 拉出、向 `main` 合并，存活不超过 2 个工作日 | 超过就说明改动太大，拆成多次合并 |
| MUST NOT 建 `develop` / `release` 长期分支 | 发布用 tag，修复用短分支 |
| SHOULD 使用 git worktree 或短分支做并行任务 | — |

### 1.2 提交信息

格式、`type` 取值、`scope` 约定、破坏性变更标记一律见 `spec/git/commit-guide.md` 第 3 章，**本节不重复定义**，只写流水线侧的后果：

| type | 流水线侧的额外动作 |
| --- | --- |
| `feat!` / 含 `BREAKING CHANGE:` | 主版本递增；必须写变更说明与迁移方案 |
| `fix` | 必须带回归用例与 `docs/regression/registry.yaml` 登记条目（`spec/testing/regression-testing-guide.md` 第 3、5 节） |
| `build` / `deps` | 必须走完整 CI，不允许跳过 |

- MUST 破坏性变更显式标记——它决定版本号递增，以及第 7.3 节是否要求分阶段迁移。

### 1.3 `main` 保护

| 保护项 | 设置 |
| --- | --- |
| 必需检查 | 静态检查、后端测试、前端测试、镜像构建（见 2.2），**全部为必需** |
| 必需评审 | 至少 1 次批准；作者不能自批 |
| 分支最新 | 合并前必须与 `main` 同步 |
| 禁止直推 | 包括管理员；`main` 不接受 `push` |
| 禁止强推 / 删除 | `main` 与 `v*` tag 一律禁止 |
| CODEOWNERS | `.github/workflows/**`、`scripts/ci/**`、`spec/**` 必须由 owner 评审 |

`.github/workflows/` 必须纳入 CODEOWNERS：改了 workflow 就能改门禁，这是最容易绕过的口子。

### 1.4 合并策略

- MUST 用 **squash merge**，一个 PR 产出一条 commit。
- MUST PR 标题符合 1.2 的格式（squash 后它成为 commit 标题）。
- 理由：一条 commit 对应一个完整变更集，`git revert` 与 `git bisect` 才可靠。

### 1.5 PR 内容要求

PR 描述必须包含三块，缺任何一块由评审人打回：

```markdown
**改了什么**
（一句话说清行为变化，不是罗列文件）

**怎么验证**
（可执行的命令或页面操作步骤；贴真实输出，不写"已测试"）

**怎么回滚**
（回滚动作；涉及迁移的写清是代码回滚还是数据回滚）
```

---

## 2. 流水线阶段

### 2.1 工作流划分

**一个工作流一个职责**，不要把所有事塞进一个文件。

| 文件 | 触发 | 职责 | 阻断性 |
| --- | --- | --- | --- |
| `ci.yml` | `pull_request`、`push: main` | 静态检查、测试、覆盖率、镜像构建（不推送） | 阻断合并 |
| `release.yml` | `push: tags v*` | 构建并推送镜像、产出 digest、SBOM、provenance，调用部署 | 阻断发布 |
| `deploy.yml` | `workflow_call`（被 release 调用）、`workflow_dispatch` | 迁移、部署、冒烟、失败回滚 | 阻断发布 |
| `nightly.yml` | `schedule` | 全量 E2E、慢测试、全量回归、依赖与镜像重扫 | 不阻断，次日修 |
| `maintenance.yml` | `schedule`、`workflow_dispatch` | 镜像与产物保留策略、缓存清理、tag 校验 | 不阻断 |

规则：

- MUST NOT 把部署逻辑写进 `ci.yml`——PR 触发的 workflow 不应持有生产凭证。
- MUST 部署入口唯一：只有 `release.yml` 能调用 `deploy.yml`，禁止绕过打 tag 直接部署。
- SHOULD `nightly.yml` 与 `ci.yml` 共用同一批脚本，避免两套命令。

### 2.2 阶段表

| # | 阶段 | 内容 | 目标时长 | 失败处理 | 产物 |
| --- | --- | --- | --- | --- | --- |
| 1 | 静态检查 | `ruff check`、`ruff format --check`、`mypy`、`tsc --noEmit`、`eslint`、`python scripts/tasks-index.py --check`（索引与计划目录一致） | < 2 min | 阻断 | 注解 |
| 2 | 单元与接口测试 | pytest（含覆盖率门槛）、Vitest | < 8 min | 阻断 | `coverage.xml`、JUnit XML |
| 3 | 数据库迁移演练 | 空库 `upgrade head → downgrade base → upgrade head` | < 3 min | 阻断 | 迁移日志 |
| 4 | 镜像构建 | 多阶段构建、SBOM、provenance；**CI 只构建不推送** | < 6 min | 阻断 | 本地镜像 |
| 5 | 回归集 | 登记表一致性校验 + `-m regression` + `-t regression` + `--grep @regression` | < 5 min | 阻断（`main` 与发布） | `regression-report.md` |
| 6 | E2E 冒烟 | 核心流程（见 `e2e-testing-guide` 第 1 节与 `behaviors.yaml` 的 P0 集合） | < 15 min | 阻断（仅 `main`） | `playwright-report/` |
| 7 | 安全扫描 | 依赖、密钥、镜像、SAST | < 4 min | 阻断（可修复高危） | SARIF |
| 8 | 迁移执行 | 目标环境 `alembic upgrade head` | < 10 min | 阻断部署 | 迁移日志 |
| 9 | 部署 | 拉取 digest、`up -d --wait` | < 10 min | 阻断 | 部署记录 |
| 10 | 部署后验证 | 健康检查 + 关键接口 + 一次真实读写 | < 3 min | **自动回滚** | 冒烟日志 |

阶段 1→2→3 在 PR 上全跑；阶段 4 在 PR 上只验证"能构建"；阶段 5、6 在 `main` 与发布链路；阶段 7 高危阻断、中低危记录；阶段 8~10 只在发布链路。

阶段 5 的登记表校验与回归报告格式见 `spec/testing/regression-testing-guide.md` 第 5、10、12 节；P0 级失败即阻断发布，不接受"重跑一次"。

### 2.3 反馈时长

- MUST PR 从推送到出结果 **< 10 分钟**（与 `spec/testing/README.md` 第 2 节一致）。
- 超时的处理顺序：**路径过滤 → 缓存 → 分片并行 → 最后才是砍测试**。
- MUST NOT 用"跳过测试"换速度；如需临时跳过，必须开 issue 并写明恢复日期。

### 2.4 失败处理原则

- MUST 先读失败日志再改，禁止"重跑一次看看"。
- MUST NOT 为了让流水线变绿而降低门禁、加 `continue-on-error`、加宽 `|| true`。
- MUST 无法当场修的问题记为 `skip` 并附 issue 链接，不允许静默删除用例。
- MUST 平台抖动导致的失败（runner 拉不到镜像、网络超时）可以重跑，**但要在 PR 里说明是抖动而非代码问题**。

---

## 3. 工作流文件规范

### 3.1 文件与命名

- MUST 路径 `.github/workflows/<职责>.yml`，文件名小写、动词或名词短语（`ci.yml`、`release.yml`、`deploy.yml`）。
- MUST `name:` 与文件名一致，便于在 UI 里定位。
- MUST 每个 workflow 顶部注释写明职责与触发条件。

### 3.2 权限最小化

- MUST 顶层写 `permissions:`，默认 `contents: read` 或 `permissions: {}`。
- MUST 写权限只在 **job 级**授予（`packages: write`、`id-token: write`、`pull-requests: write`）。
- MUST NOT 在顶层授予写权限——它会被该 workflow 的所有 job 继承。

```yaml
permissions: {}          # 顶层全关

jobs:
  build:
    permissions:
      contents: read
      packages: write     # 只有这个 job 能推镜像
      id-token: write     # 只有这个 job 能做 OIDC / 无密钥签名
```

### 3.3 触发器选择

| 场景 | 用 | 不用 |
| --- | --- | --- |
| PR 验证 | `pull_request` | `pull_request_target` |
| 发布 | `push: tags` | `workflow_run` 链式触发 |
| 手工发布 / 回滚 | `workflow_dispatch`（带 typed inputs） | 提交注释触发 |
| 可复用 | `workflow_call` | 复制粘贴 YAML |

- MUST NOT 用 `pull_request_target`：它在基仓库上下文运行，能拿到密钥与写权限；一旦 checkout PR 代码就等于把生产凭证交给外部提交者。
- MUST 若确有必须（如需要给 PR 打标签），该 workflow **不得 checkout 或执行 PR 代码**，且权限只到 `pull-requests: write`。
- MUST 注释触发式命令（`/deploy`）先校验 `author_association` 与 actor 权限。

### 3.4 并发与超时

- MUST 每个 job 设 `timeout-minutes`。默认 360 分钟，卡住的 job 会占满并发额度。
- MUST CI 用 `concurrency` 且 `cancel-in-progress: true`：同一分支的旧运行没有意义。
- MUST **部署用 `concurrency` 且 `cancel-in-progress: false`**：部署被中途取消会留下半完成状态。

`ci.yml`：

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

`deploy.yml`（注意两个取值都相反）：

```yaml
concurrency:
  group: deploy-${{ inputs.environment }}
  cancel-in-progress: false
```

### 3.5 可复用工作流

- MUST 按 **commit SHA** 引用外部复用工作流，不用 `@main`。
- MUST 显式传所需 secrets，**禁止 `secrets: inherit`**——它把调用方的全部密钥一次性交给被调用方。
- MUST 在 `workflow_call` 里声明 `inputs` 的类型与 `required`，避免字符串误传。

### 3.6 脚本外置

- MUST 超过 5 行的 bash 移到 `scripts/ci/*.sh`，workflow 里只留一行调用。
- MUST 脚本首行 `set -euo pipefail`。
- 理由：YAML 里的多行 bash 无法本地执行、无法单独测试、diff 不可读。

### 3.7 缓存

- MUST 缓存键包含 lock 文件哈希（`uv.lock`、`package-lock.json`）。
- MUST NOT 在 `release.yml` / `deploy.yml` 恢复由 PR 写入的缓存——缓存可被投毒。
- SHOULD 优先用官方 action 的缓存能力（`setup-uv` 的 `enable-cache`、`setup-node` 的 `cache: npm`），少自己写 `actions/cache`。

### 3.8 路径过滤与"必需检查"

单仓两栈时先用全量跑，流水线变慢后再加过滤。加过滤时必须注意：

- MUST NOT 让"必需检查"因为路径不匹配而被**跳过**——被跳过的必需检查在 GitHub 上可能显示为通过。
- 正确做法：用 `workflow` 级 `paths` 控制，或保留一个总会运行的 job，在无事可做时立即成功并注明"无相关改动"。

```yaml
on:
  pull_request:
    paths-ignore:
      - 'docs/**'
      - '**/*.md'
```

---

## 4. 依赖与工具链锁定

**依赖策略（要不要引、版本怎么写、怎么升级、怎么移除、供应链怎么审）见 `spec/dependency/dependency-guide.md`。本节只规定流水线侧：用哪条命令装、怎么缓存、自动化落在哪。**

### 4.1 CI 安装命令

| 生态 | 命令 | 说明 |
| --- | --- | --- |
| Python 校验 | `uv lock --check` | 不安装，只验证锁文件与 `pyproject.toml` 一致 |
| Python 安装 | `uv sync --locked --no-group dev` | **锁文件过期即报错**，这是 CI 要的行为；只装运行期依赖 |
| 执行命令 | `uv run --locked <cmd>` | 不在运行时改写锁文件 |
| Docker 构建内 | `uv sync --frozen` | 前一步已用 `--locked` 校验过，这里只求速度 |
| Node 安装 | `npm ci` | 严格按 lockfile；`npm install` 会改写 lockfile |

- MUST CI 用 `--locked`，**禁止 `--frozen` 作为唯一校验**：`--frozen` 跳过新鲜度检查，`pyproject.toml` 加了依赖也会静默成功，测试的就不是评审过的那套依赖。允许的用法只有"同一次运行里，`--locked` 之后才 `--frozen`"。
- MUST `uv lock --check` 与 `npm ci` 都失败即阻断，不允许"锁文件过期就重生成一版"。
- MUST NOT 在 CI 里执行 `uv lock`、`uv add`、`uv pip install`、`npm install`。
- MUST 安装步骤失败时输出锁文件与声明文件的差异片段，让失败可判断（是"没提交锁文件"还是"锁文件过期"）。

### 4.2 缓存

| 生态 | 缓存 | key |
| --- | --- | --- |
| uv | `~/.cache/uv` + `.venv` | `hashFiles('**/uv.lock')` |
| npm | `~/.npm` | `hashFiles('**/package-lock.json')` |

- MUST 缓存 key 绑定锁文件哈希；绑定 `package.json` 会让"改了 lock 但声明没变"时命中旧缓存。
- MUST 缓存只加速，不承担正确性：命中缓存后仍要跑 `uv sync --locked` / `npm ci`。

### 4.3 升级自动化

- MUST 由 Dependabot 或 Renovate 提 PR，配置入库（`.github/dependabot.yml` 或 `renovate.json`）。
- MUST 覆盖：Python（uv）、npm、Docker 基础镜像、GitHub Actions。
- MUST 升级 PR 走完整 CI，不允许"只改 lockfile 不用测"。
- SHOULD 分组与 cooldown 按 `spec/dependency/dependency-guide.md` 6.2 配置；CI 侧只保证"跑得动、看得见"。
- MUST 同一时间打开的升级 PR 不超过 5 个；超出的由人关闭并排期。

### 4.4 流水线内的禁止事项

- MUST NOT 在 CI 里 `pip install -g`、`npx <工具>@latest`、`apt-get upgrade`。
- MUST NOT 用 `:latest` 作为基础镜像或部署镜像。
- MUST NOT 提交 `.env`、凭据文件、`node_modules/`、`.venv/`。
- MUST NOT 让 CI 的 Node / Python 主版本与生产镜像不一致（不一致时以生产为准改 CI）。

---

## 5. 构建产物

### 5.1 build once，promote by digest

同一次构建的产物，原样穿过所有环境：

```text
commit ──▶ 构建一次 ──▶ registry/app@sha256:9f3c…（不可变）
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
           staging        （同一 digest）   production
```

- MUST 只构建一次。禁止"为 staging 构建一次、为 production 再构建一次"。
- MUST 环境之间传递的是 **digest**（`sha256:…`），不是 tag。
- 理由：`FROM python:3.13-slim` 解析的是 tag，tag 会移动。staging 15:00 构建、production 17:00 构建，中间上游发了个新 patch，生产跑的就不是测试过的那份字节。

### 5.2 标签策略

| 标签 | 示例 | 用途 | 能否用于部署 |
| --- | --- | --- | --- |
| commit | `sha-9f3c1ab` | 每次构建唯一，便于追溯 | 可以（但优先用 digest） |
| 语义版本 | `v1.4.2` | 人读的发布标识 | 可以 |
| 环境别名 | `staging`、`production` | 指向当前部署的 digest | 只能作为"指针"，实际部署仍写死 digest |
| digest | `@sha256:…` | 唯一精确引用 | **推荐，唯一应写进部署配置的形式** |
| `latest` | `latest` | 无 | **禁止** |

- MUST 一次构建打多个标签（commit + 语义版本），不要为了多个标签构建多次。
- MUST 环境别名只能通过 `docker buildx imagetools create` 重指向，**不得重新构建**。
- MUST NOT 用 tag 覆盖来"修"一次发布——发新 digest，然后有意地移动指针。

### 5.3 镜像规范

| 要求 | 说明 |
| --- | --- |
| MUST 多阶段构建 | 构建依赖不进入运行镜像；运行层不含编译器、测试依赖、源码工具链 |
| MUST 非 root 运行 | 创建专用用户；`USER app` / `USER nextjs` |
| MUST `.dockerignore` | 排除 `.git`、`node_modules`、`.venv`、`tests`、`docs`、`.env*`；上下文越小构建越快 |
| MUST 基础镜像按 digest | `FROM python:3.13-slim@sha256:…`，由 Dependabot 提 PR 更新 |
| MUST 依赖层在源码层之前 | 先 `COPY pyproject.toml uv.lock` 再 `COPY .`，改代码不失效依赖缓存 |
| MUST 单进程 | 一容器一进程；不在容器里跑 supervisor、cron、nginx |
| MUST 暴露健康检查 | 用语言自带的 HTTP 客户端，运行镜像里通常没有 `curl` |
| MUST NOT 在镜像里放密钥 | 配置一律运行时注入（见 6.2） |
| MUST NOT 用 `--privileged`、挂载 docker socket | — |

后端（FastAPI）要点：

- 启动命令 `uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips`，worker 数由编排层（副本数）决定，不靠 `--workers`。
- 运行镜像里 `.venv` 从构建层整体复制，`PATH` 指向它，不用系统 Python 装包。

前端（Next.js）要点：

- MUST `next.config.ts` 设 `output: 'standalone'`，运行镜像只带 `.next/standalone` + `.next/static` + `public`。
- MUST 用 `node server.js` 启动，不用 `next start`——standalone 产物里没有 `next` CLI。
- MUST 构建期与运行期分离：`NEXT_PUBLIC_*` 在**构建时**内联，其余环境变量在**运行时**读取。构建一次跨环境复用的前提是：跨环境不同的值都走运行时读取。

### 5.4 SBOM 与来源证明

- MUST 每次发布产出 SBOM（`sbom: true`）与 provenance（`provenance: mode=max`），随镜像推送。
- SHOULD 用无密钥方式签名（cosign keyless，依赖 OIDC），并在部署前校验。
- MUST 部署前能回答：这个 digest 由哪个 commit、哪次流水线、谁触发的构建产生。

### 5.5 保留策略

- MUST 保留**所有曾经部署过的 digest**，不设过期——它们是回滚的唯一依据。
- MUST 至少保留最近 20 个 commit 标签镜像。
- SHOULD 未打标签的镜像 7 天后清理（构建缓存层除外）。
- MUST 清理用自动化任务（`maintenance.yml`），不手工删 registry。

### 5.6 回滚

- MUST 回滚 = 部署上一个已确认的 digest，不重新构建、不 revert 代码。
- MUST 保留上一版 digest 的可查记录（主机上的 `.deployed-digest` 文件，或部署记录表）。
- MUST 定期演练回滚（每季度至少一次），确认旧 digest 仍可拉取。

---

## 6. 环境与配置

### 6.1 环境划分

| 环境 | 用途 | 数据 | 谁能部署 |
| --- | --- | --- | --- |
| `local` | 开发机 | 本地容器，可随意重置 | 开发者 |
| `ci` | 流水线内 | 每次全新容器 | 流水线 |
| `staging` | 发布前验证 | 脱敏副本或合成数据 | 流水线自动 |
| `production` | 生产 | 真实数据 | 流水线 + 人工审批 |

- MUST NOT 设共享的 `dev` 服务器——它会退化成"谁都能改、谁都不敢删"的环境。开发用本地 compose。
- MUST staging 与 production 由**同一份部署配置**部署，差异只体现在变量值上。

### 6.2 配置注入

遵循 12-factor：**配置来自环境变量，不来自代码、不来自镜像**。

- MUST 一个镜像跑所有环境，环境差异全部通过环境变量注入。
- MUST 提交 `.env.example`（只有键名与说明、无真实值），**禁止提交 `.env`**。
- MUST 应用启动时校验必需变量，缺失即启动失败并给出明确错误（不带出值）。
- MUST NOT 在代码里写 `if env == "production"` 分支——配置差异用变量表达，不用代码分支。

### 6.3 密钥分级

| 级别 | 存放 | 用于 |
| --- | --- | --- |
| 仓库级 secret | GitHub repo secrets | 非敏感、多环境共用的值（如只读 registry token） |
| 环境级 secret | GitHub environment secrets | 生产数据库密码、部署私钥——**只有该 environment 的 job 能读** |
| 短期凭证（推荐） | OIDC 换取 | 云厂商、registry、KMS；无需长期密钥 |

- MUST 生产凭证放 **environment**，不放仓库级——仓库级 secrets 对所有 workflow 可见。
- MUST 优先 OIDC：`id-token: write` 只给需要它的那个 job，云侧信任策略限定到具体 repo + 分支/环境。
- MUST NOT 用个人访问令牌（PAT）做 CI 凭证。
- MUST NOT 把结构化数据（JSON/YAML）整块塞进一个 secret——脱敏按精确匹配，整块塞进去几乎必然漏。

### 6.4 环境审批

生产环境必须配置：

| 设置 | 值 |
| --- | --- |
| Required reviewers | 至少 1 人；开启 **Prevent self-review** |
| 管理员绕过 | 关闭 |
| 部署分支限制 | 只允许 `main` 与 `v*` tag |
| Wait timer | 高危变更可加（如 5 分钟观察窗） |

- MUST 审批人看得到这次部署的 commit 范围与迁移内容，否则审批无意义。
- MUST NOT 让同一个人既触发又批准。

### 6.5 环境一致性

- MUST staging 与 production 的 PostgreSQL **主版本相同**。
- MUST Node 与 Python 主版本相同。
- MUST 数据库扩展（`pg_trgm`、`pgvector` 等）在两边都装、版本一致。
- 允许的差异只有：域名、副本数、资源配额、数据量与数据来源。差异必须写进部署配置的注释，不靠口头传递。

---

## 7. 数据库迁移在流水线中的位置

迁移文件怎么写、怎么命名、内容规则、回滚写法——全部见 `spec/alembic/alembic-guide.md`。本章只规定**时序**与**失败处置**。

### 7.1 核心时序：expand → 部署代码 → backfill → contract

部署过程中，旧代码与新代码会同时对着同一个库运行。因此任何变更都必须让**两个版本同时可用**。

```text
① expand   加新列/新表/新索引（不动旧的）         ── 迁移 + 双写代码
② migrate  回填数据（分批、可中断）               ── 后台任务
③ cutover  代码只读新结构                         ── 部署
④ contract 删除旧列/旧表（确认无人引用后）        ── 独立迁移
```

- MUST 四个阶段可以跨多次发布，不必挤进一次部署。
- MUST 迁移在**部署新代码之前**执行（expand 阶段）；contract 阶段的迁移在**部署之后**很久才执行。
- MUST 禁止把 `RENAME COLUMN`、`DROP COLUMN`、加 `NOT NULL`、改类型混在一次发布里。

### 7.2 迁移 job 的规则

- MUST 迁移是**独立 job**，在部署 job 之前，`needs` 显式声明。
- MUST 迁移 job 加 `concurrency`（按环境分组）、`cancel-in-progress: false`，且 `timeout-minutes` 不超过业务可接受的维护窗口。
- MUST 迁移失败即**终止发布**，不允许"忽略迁移失败继续部署"。
- MUST 迁移 job 有明确的目标环境标识（`environment:`），拿到的是该环境的凭证。
- MUST 部署前自动备份或打快照（生产必须）；备份失败即终止。
- SHOULD 迁移耗时超过 30 秒的，在 PR 里注明预估时长与锁影响。

### 7.3 变更类型与执行顺序

| 变更 | 顺序 | 说明 |
| --- | --- | --- |
| 加可空列 | 迁移 → 代码 | 新代码期望列存在 |
| 加 `NOT NULL` 列 | 迁移（可空）→ 回填 → 代码 → 迁移（加约束） | 直接加会锁表 + 失败 |
| 删列 / 删表 | 代码（停用）→ 迁移（删除） | 顺序反了旧代码直接报错 |
| 改名 | expand-contract 三步 | 任何单步都不安全 |
| 加索引 | `CREATE INDEX CONCURRENTLY`，且不能放在事务里 | 见 alembic-guide 6.1 |
| 改类型 | 新增列 + 双写 + 回填 + 切换 + 删旧列 | 直接 `ALTER TYPE` 会重写表 |
| 加外键 | 先加 `NOT VALID`，回填后 `VALIDATE` | 避免全表锁 |
| 加枚举值 | 迁移 → 代码 | 只能追加，不能删改 |

### 7.4 回滚：代码回滚 ≠ 迁移回滚

| 情况 | 处理 |
| --- | --- |
| 新代码有问题，迁移是 expand（只加不减） | 回滚代码即可，**不要**回滚迁移——旧代码不认识新列也不会坏 |
| 迁移把库改坏（数据错、锁表） | 停止流量 → 执行 `downgrade` → 回滚代码；**先确认 downgrade 不丢数据** |
| contract 阶段删了列，之后要回滚 | 代码回滚也救不回来，必须从备份恢复 → 这是 contract 必须延后的原因 |

- MUST 每次发布在 PR 里写明"这次回滚是只回代码，还是也要动数据"。
- MUST NOT 假设 `downgrade` 一定安全：它是代码，同样可能有 bug；数据删除类迁移的 downgrade 通常无法恢复数据。

### 7.5 演练

- MUST `ci.yml` 在空库上跑 `upgrade head → downgrade base → upgrade head`，证明链路可逆且可重复。
- SHOULD 在 staging 用生产规模副本演练一次耗时与锁；数据量大时先 `ANALYZE` 再评估执行计划。
- MUST NOT 只在空库上验证就上生产——空库 0 行时任何 DDL 都快。

---

## 8. 部署

### 8.1 策略选择

| 部署形态 | 默认策略 | 适用 |
| --- | --- | --- |
| 单机 Docker Compose | 重建 + 健康检查门禁 + 失败回滚 | 内部系统、早期阶段 |
| 多副本容器编排 | 滚动更新（`maxUnavailable: 0`） | 常规 |
| 高风险变更 | 蓝绿（切流量）或金丝雀（按比例放量 + 数值门禁） | 核心链路、大版本 |

- MUST 任何策略都必须有**自动回滚**，不依赖人发现。
- MUST 滚动更新的 `maxUnavailable` 为 0，保证部署期间容量不降。
- SHOULD 早期不做金丝雀——先有健康检查、冒烟、回滚，再加金丝雀。

### 8.2 健康检查

两个端点，职责不同，不要合并：

| 端点 | 检查什么 | 用途 | 失败后果 |
| --- | --- | --- | --- |
| `GET /healthz` | 进程能响应 | 存活探针 | 重启容器 |
| `GET /readyz` | 依赖可用（数据库连接、必要外部服务） | 就绪探针 | 摘掉流量，不重启 |

- MUST `/healthz` 不查数据库——数据库抖动时重启应用毫无帮助，只会放大故障。
- MUST 启动期给足 `start_period`（迁移后冷启动可能较慢），避免刚起就被判死。
- MUST 探针超时短（3 秒内）、失败阈值小（3 次），避免挂死实例长时间接流量。
- MUST `/healthz` 返回版本信息（`{"status":"ok","version":"1.4.2","commit":"9f3c1ab"}`），用于确认"线上到底是哪版"。

### 8.3 部署后验证

部署完成不等于成功。MUST 依次验证：

1. **就绪**：`/readyz` 连续 3 次返回 200。
2. **版本**：`/healthz` 返回的 `commit` 等于本次要部署的 commit——防止"部署成功但拉的是旧镜像"。
3. **关键接口**：一到两个只读接口返回预期结构。
4. **一次真实读写**（staging 必须，production 视风险）：走完整链路写一条测试数据并清理。

任一步失败即触发回滚。`scripts/ci/smoke.sh` 提供实现，见附录 A.7。

### 8.4 自动回滚条件

回滚必须是**数值条件**，不能是"看着不对就回滚"。

| 条件 | 阈值 | 观察窗 |
| --- | --- | --- |
| 冒烟脚本失败 | 任一检查非 0 退出 | 立即 |
| 就绪探针连续失败 | 3 次 | 立即 |
| HTTP 5xx 比例 | > 2% | 持续 3 分钟 |
| P95 延迟 | > 部署前基线的 1.5 倍 | 持续 5 分钟 |
| 关键业务错误码（如支付失败） | > 基线 2 倍 | 持续 5 分钟 |

- MUST 阈值写进部署配置或监控规则，不写在 wiki 里。
- MUST 回滚动作可自动执行——但**自动回滚后必须通知到人**，否则会掩盖反复失败的发布。
- SHOULD 缺监控时先只做"冒烟失败即回滚"，不要虚构阈值。

### 8.5 发布冻结窗口

- MUST 业务高峰、月末结算、大促期间冻结发布。冻结期写进发布计划。
- 冻结期只允许：安全修复、数据错乱修复。二者都需要额外一次审批。
- MUST NOT 在周五下班前发布非紧急变更（无值守时出问题无人处理）。

### 8.6 参照命令

Docker Compose（单机）：

```bash
# 部署指定 digest
API_IMAGE="ghcr.io/OWNER/REPO/api@sha256:…" docker compose pull api
API_IMAGE="ghcr.io/OWNER/REPO/api@sha256:…" docker compose up -d --wait --no-deps api

# 回滚：换成上一个 digest，命令完全一样
```

Kubernetes：

```bash
kubectl -n prod set image deploy/api api=ghcr.io/OWNER/REPO/api@sha256:… 
kubectl -n prod rollout status deploy/api --timeout=180s
kubectl -n prod rollout undo deploy/api        # 回滚
```

---

## 9. 安全与供应链

### 9.1 action 固定到 SHA

- MUST 第三方 action 固定到**完整 commit SHA**，并加注释标明版本。
- MUST 该 SHA 来自 action 官方仓库的 tag，不是随手取的默认分支 commit。
- MUST 开启（或组织级配置）"要求所有 action 固定 SHA"的策略。

```yaml
- uses: actions/checkout@<40位SHA>          # v5.0.0
- uses: astral-sh/setup-uv@<40位SHA>        # v6.0.0
```

解析 SHA 的方法（不要凭记忆写）：

```bash
gh api repos/actions/checkout/commits/v5.0.0 --jq .sha
```

注意：固定到 SHA 后，Dependabot 仍会提版本更新 PR，但**不会**为它报安全告警（安全告警只覆盖语义化版本引用）。所以固定 SHA 的同时必须开启 `github-actions` 生态的版本更新。

### 9.2 注入防护

PR 标题、分支名、commit message、issue 内容、`workflow_dispatch` 的输入，全部是**不可信输入**。

- MUST 通过 `env:` 传给脚本，再用引号引用；禁止把 `${{ }}` 直接拼进 `run:`。
- MUST NOT 把不可信值写进 `$GITHUB_ENV`、`$GITHUB_OUTPUT`、`$GITHUB_PATH`——它们会成为后续步骤的变量或可执行路径。

禁止：

```yaml
- run: |
    echo "PR 标题: ${{ github.event.pull_request.title }}"
```

正确：

```yaml
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: |
    printf 'PR 标题: %s\n' "$PR_TITLE"
```

### 9.3 密钥不落日志

- MUST NOT `echo` 密钥、`env` 全量打印、把密钥写进会被上传的文件。
- MUST 派生的敏感值用 `::add-mask::` 遮蔽。
- MUST `actions/checkout` 设 `persist-credentials: false`，避免 token 留在 `.git/config` 里被后续步骤或产物带出。
- MUST NOT 把 `secrets` 上下文整体传给第三方 action。

### 9.4 扫描

| 类型 | 工具 | 阻断条件 |
| --- | --- | --- |
| 依赖漏洞（SCA） | Dependabot / `pip-audit` / `npm audit` | 有可修复的 high/critical |
| 密钥泄漏 | gitleaks / GitHub secret scanning | 任一命中 |
| 镜像漏洞 | Trivy / Grype | 可修复的 high/critical |
| 静态分析（SAST） | CodeQL / Semgrep | 按规则集配置 |

- MUST 只阻断"**可修复的**高危"——把所有发现都阻断会让人习惯性忽略。
- MUST 中低危记录为 issue，定期处理，不阻断。
- MUST 定期重扫已部署镜像（`nightly.yml`）：漏洞大多来自基础镜像与系统包，不是自己的代码。

### 9.5 签名（阶段三）

- SHOULD 用 cosign 无密钥签名，部署前 `cosign verify` 校验身份与 issuer。
- SHOULD 用 `actions/attest-build-provenance` 生成来源证明，部署前 `gh attestation verify`。
- 未开启签名时，至少保证"按 digest 部署 + provenance 可查"。

### 9.6 fork PR 与 runner

- MUST fork PR 的 workflow 拿不到任何 secret，token 只读。
- MUST 公共仓库禁止使用自托管 runner——PR 代码可在 runner 上任意执行。
- MUST 私有仓库的自托管 runner 一次只跑一个 job（ephemeral），且与生产网络隔离。
- MUST runner 上的工作目录不得存放生产凭证。

---

## 10. 可观测与度量

### 10.1 部署记录

每次部署 MUST 留下一条记录，字段固定：

| 字段 | 示例 |
| --- | --- |
| 时间（UTC） | `2026-11-15T09:12:31Z` |
| 环境 | `production` |
| 镜像 digest | `sha256:9f3c…` |
| commit | `9f3c1ab` |
| 版本 | `v1.4.2` |
| 触发者 | `github:alice` / `workflow_dispatch:alice` |
| 结果 | `succeeded` / `rolled_back` / `failed` |
| 回滚目标 | `sha256:7a1b…`（如有） |

- MUST 记录落到可查询的地方（部署流水线日志 + 一个可 grep 的文件/表）。
- MUST 部署事件与监控图对齐：出问题时第一件事是"这个时间点有没有部署"。

### 10.2 DORA 五项

按 DORA 现行口径（已从四项扩展到五项）计算：

| 指标 | 定义 | 数据来源 |
| --- | --- | --- |
| **变更前置时间** | 从 commit 进 `main` 到生产可用 | commit 时间 → 部署记录时间 |
| **部署频率** | 单位时间成功部署次数 | 部署记录 |
| **失败部署恢复时间** | 部署失败/引发事故后恢复到正常的时间 | 部署记录 + 事故记录 |
| **变更失败率** | 需要立即干预的部署占比 | 部署结果标记 |
| **部署返工率** | 因生产事故而产生的非计划部署占比 | 部署记录的原因字段 |

计算规则：

- MUST 按**服务**分别算，不要跨服务混算。
- MUST 从流水线与事故记录自动算，不用问卷。
- MUST NOT 把指标当考核目标——被当作目标就会出现"拆小部署刷频率"这类游戏行为。
- MUST 同时看吞吐（前三项）与不稳定度（后两项）：只看速度会奖励鲁莽，只看稳定会奖励不发布。

### 10.3 流水线自身指标

| 指标 | 目标 | 异常含义 |
| --- | --- | --- |
| PR 反馈时长（中位数） | < 10 min | 测试或缓存有问题 |
| PR 反馈时长（P95） | < 20 min | 有慢测试，需拆分或标记 `slow` |
| 失败率 | < 10% | 高于此说明门禁不稳或环境不可靠 |
| 被隔离的 flaky 用例数 | 趋于 0 | 持续增长说明在掩盖问题 |
| 从失败到修复的中位时长 | < 1 个工作日 | 长期红着等于没有门禁 |

### 10.4 通知

- MUST `main` 失败、部署失败、自动回滚 → 立即通知负责人。
- MUST NOT 每个 PR 失败都通知到群——PR 失败由作者在界面上看。
- SHOULD 通知内容包含：环境、digest、commit、失败阶段、日志链接。

---

## 11. 发布与版本

### 11.1 版本号

遵循 **语义化版本** `MAJOR.MINOR.PATCH`，语义对应用户可见行为：

| 变化 | 递增 |
| --- | --- |
| 不兼容的 API / 行为变更 | MAJOR |
| 向后兼容的新功能 | MINOR |
| 向后兼容的缺陷修复 | PATCH |

- MUST 版本号在 `main` 上通过 tag 产生，不在提交里手改。
- MUST 内部重构、纯样式调整不单独发版。

### 11.2 变更日志

- MUST 由 Conventional Commits 自动生成，按 `type` 分组（新功能 / 修复 / 破坏性变更 / 其它）。
- MUST 破坏性变更单独成段，写明迁移动作与回滚方式。
- MUST NOT 手写 changelog 再和提交记录对不上。

### 11.3 tag 与 release

- MUST tag 打在 `main` 的 commit 上，格式 `v<MAJOR>.<MINOR>.<PATCH>`。
- MUST release 内容包含：版本、变更摘要、镜像 digest、SBOM 链接、回归报告（`artifacts/regression-<version>.md`，见 `regression-testing-guide` 第 10 节）。
- MUST tag 保护：禁止移动、禁止删除。

### 11.4 hotfix

```text
线上故障 → 从最新 tag 拉 hotfix 分支 → 最小改动 + 回归用例（`regression-testing-guide` 第 3 节）+ registry 登记
        → PR 到 main（走完整 CI）→ 打 patch 版本 tag → 部署
        → 必须回灌：确认 main 已包含该修复
```

- MUST 走完整 CI，禁止"紧急所以跳过测试"。
- MUST 事故修复同时产生一条 `source: incident` 的回归条目（`regression-testing-guide` 第 2 节），否则同类故障会再次发生。
- MUST 修复必须同时存在于 `main`，否则下次发布会把故障带回来。
- MUST 记录事故编号，供 10.2 的变更失败率使用。

### 11.5 版本可见性

- MUST `/healthz` 返回 `version` 与 `commit`。
- SHOULD 前端页面或响应头暴露版本，便于用户报障时定位。

---

## 12. 权限与应急

### 12.1 角色

| 角色 | 能做什么 |
| --- | --- |
| 贡献者 | 提交 PR、跑本地与 PR 流水线 |
| 评审人 | 批准 PR；不能批准自己发起的部署 |
| 发布负责人 | 批准 `staging` → `production` 部署；可执行回滚 |
| 仓库管理员 | 改分支保护、改 workflow、管理密钥；**不参与日常发布审批** |

- MUST 改 `.github/workflows/**` 需要额外评审（CODEOWNERS）。
- MUST 生产密钥的读取权限限定到 `production` environment。

### 12.2 break-glass（应急通道）

允许手工介入的唯一情形：流水线本身故障，且线上正在受损。

- MUST 事前：确认流水线确实不可用（不是配置错误）。
- MUST 事中：最小改动、记录每条命令与时间。
- MUST 事后 24 小时内：补齐 PR（哪怕只是把手工改动原样提交）、补部署记录、写清为什么绕过流水线。
- MUST NOT 把 break-glass 变成常规路径——一个月内出现两次就说明流水线有结构性问题，要修流水线而不是继续绕过。

### 12.3 事故处置顺序

```text
① 先恢复：回滚到上一个 digest（或切流量到旧版本），让用户可用
② 再定位：看部署记录 → 看日志 → 看指标，确认是否与本次发布相关
③ 后修复：走正常 PR 流程修，不直接在线上改
```

- MUST 第一步永远是恢复服务，不是找原因。
- MUST NOT 在未回滚的情况下边查边改生产。

---

## 13. 落地路线

### 13.1 阶段一：有代码就能做

前置：git 仓库、`backend/`、`frontend/`、`uv.lock`、`package-lock.json`。

- `ci.yml`：静态检查 + 后端测试 + 前端测试 + 镜像构建（不推送）
- 分支保护 + 必需检查 + CODEOWNERS
- `backend/Dockerfile`、`frontend/Dockerfile`、`.dockerignore`
- 依赖锁定（4.1、4.2）+ Dependabot（4.4）

### 13.2 阶段二：能自动部署到 staging

- `release.yml`：构建推送、输出 digest、SBOM、provenance
- `deploy.yml`：迁移 job + 部署 + 冒烟 + 失败回滚
- staging 环境变量与密钥落地
- 部署记录（10.1）

### 13.3 阶段三：生产与度量

- 生产 environment + 审批 + 部署分支限制
- 自动回滚的数值阈值（8.4）与监控对接
- 签名与来源证明（9.5）
- DORA 自动统计（10.2）
- 金丝雀（按需）

### 13.4 当前仓库的落地前置

截至本文档编写时，仓库是**规范仓库，尚无应用代码**，因此以下内容都不存在，CI 无法真正运行：

| 缺失项 | 影响 |
| --- | --- |
| git 仓库（当前目录无 `.git`） | 分支保护、PR、tag 全部无从谈起 |
| `backend/`、`frontend/` 目录 | 工作流里的路径与命令全部落空 |
| `backend/uv.lock`、`frontend/package-lock.json` | `--locked` / `npm ci` 会直接失败 |
| `deploy/docker-compose.yml` | 部署 job 无对象 |

**结论**：本规范是"应用落地时照着做"的清单，不是"现在就能跑"的配置。先把 13.1 的三项（git、目录、lockfile）补齐，`ci.yml` 才有意义。

### 13.5 待定项

以下选项取决于实际基础设施，落地前必须定下来，定了再补对应实现：

| 待定项 | 影响范围 | 默认取向 |
| --- | --- | --- |
| 代码托管平台 | workflow 语法整体 | GitHub Actions（落地时创建 `.github/workflows/`，配置见附录 A） |
| 镜像仓库 | 5.2、6.3、8.6 | GHCR |
| 部署形态 | 8.1、8.6、附录 A.6 | 单机 Docker Compose |
| 主机与域名、TLS | 8.3 冒烟地址 | 待定 |
| 数据库形态 | 7.2 备份方式、6.5 | 自建 PostgreSQL 容器；托管则改备份实现 |
| 密钥后端 | 6.3 | GitHub environment secrets；有 Vault/KMS 则走 OIDC |
| 是否需要合规审批留痕 | 6.4、10.1 | 按实际要求加 |

---

## 14. 提交前检查清单（涉及 CI / 部署变更时）

- [ ] workflow 顶层 `permissions` 已收窄，写权限只在需要的 job 上。
- [ ] 新增的第三方 action 已固定到完整 SHA，并注释版本。
- [ ] 没有把不可信输入（PR 标题、分支名、输入参数）直接拼进 `run:`。
- [ ] 新 job 有 `timeout-minutes`；部署 job 的 `cancel-in-progress: false`。
- [ ] 超过 5 行的 bash 已移入 `scripts/ci/`，脚本有 `set -euo pipefail`。
- [ ] CI 用 `uv sync --locked` / `npm ci`，没有 `uv lock` / `npm install`。
- [ ] 镜像按 digest 引用，没有 `:latest`；基础镜像按 digest 固定。
- [ ] 运行镜像非 root，不含构建工具与测试依赖。
- [ ] 涉及结构变更时，迁移任务时序符合 7.1，PR 里写明了回滚是"只回代码"还是"要动数据"。
- [ ] 部署后验证包含了版本比对（`/healthz` 的 commit 与本次一致）。
- [ ] 失败回滚的路径存在且能执行（不是只写了文档）。
- [ ] 部署记录字段齐全（10.1）。

---

## 15. 底线

1. **只构建一次**，其余环境靠 digest 传递，不重建。
2. **生产只能由流水线进入**，手工介入必须留痕。
3. **部署可回滚**：回滚是指针切换，且上一版 digest 一定还在。
4. **迁移与代码分开部署**，破坏性变更分阶段做。
5. **门禁可判定**：数值或退出码，不写"确认合理"。
6. **不改门禁换绿**：红着就查原因，不查就关掉门禁等于没有 CI。
7. **密钥不进日志、不进镜像、不进 fork PR**。

---

## 附录 A：完整参照实现

以下文件可直接落地，只需替换 `OWNER/REPO`、SHA 占位与主机地址。SHA 未写死数值——**必须用 `gh api repos/<owner>/<repo>/commits/<tag> --jq .sha` 解析后填入**，不要凭记忆填。

### A.1 `.github/workflows/ci.yml`

```yaml
# 职责：PR 与 main 的静态检查、测试、覆盖率、镜像可构建性验证
# 触发：pull_request、push to main
name: ci

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  actionlint:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@<SHA>          # v5.0.0
        with:
          persist-credentials: false
      - uses: raven-actions/actionlint@<SHA>  # 固定版本
        with:
          fail-on-error: true

  backend:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    defaults:
      run:
        working-directory: backend
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
          POSTGRES_DB: app_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U app -d app_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      APP_TEST_DATABASE_URL: postgresql+asyncpg://app:app@127.0.0.1:5432/app_test
    steps:
      - uses: actions/checkout@<SHA>
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@<SHA>
        with:
          version: "0.13.1"
          enable-cache: true
          cache-dependency-glob: backend/uv.lock
      - name: 校验锁文件
        run: uv lock --check
      - name: 安装依赖
        run: uv sync --locked
      - name: 格式与静态检查
        run: |
          set -euo pipefail
          uv run --locked ruff check .
          uv run --locked ruff format --check .
          uv run --locked mypy app
      - name: 迁移演练（空库升降级）
        run: |
          set -euo pipefail
          uv run --locked alembic upgrade head
          uv run --locked alembic downgrade base
          uv run --locked alembic upgrade head
      - name: 测试与覆盖率
        run: |
          set -euo pipefail
          uv run --locked pytest -q \
            --cov=app --cov-branch \
            --cov-report=xml --cov-report=term-missing \
            --cov-fail-under=85
      - name: 上传测试产物
        if: always()
        uses: actions/upload-artifact@<SHA>
        with:
          name: backend-test-report
          path: |
            backend/coverage.xml
            backend/htmlcov
          retention-days: 7

  frontend:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@<SHA>
        with:
          persist-credentials: false
      - uses: actions/setup-node@<SHA>
        with:
          node-version-file: frontend/.nvmrc
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npx tsc --noEmit
      - run: npm run test:run
      - run: npm run test:coverage
      - name: 上传覆盖率
        if: always()
        uses: actions/upload-artifact@<SHA>
        with:
          name: frontend-coverage
          path: frontend/coverage
          retention-days: 7

  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    needs: [backend, frontend]
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<SHA>
        with:
          persist-credentials: false
      - uses: docker/setup-buildx-action@<SHA>
      - name: 验证后端镜像可构建
        uses: docker/build-push-action@<SHA>
        with:
          context: backend
          push: false
          cache-from: type=gha,scope=backend
          cache-to: type=gha,mode=max,scope=backend
      - name: 验证前端镜像可构建
        uses: docker/build-push-action@<SHA>
        with:
          context: frontend
          push: false
          cache-from: type=gha,scope=frontend
          cache-to: type=gha,mode=max,scope=frontend
```

### A.2 `.github/workflows/release.yml`

```yaml
# 职责：打 tag 时构建并推送镜像，产出 digest / SBOM / provenance，随后调用部署
name: release

on:
  push:
    tags: ["v*"]

permissions: {}

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  build-api:
    runs-on: ubuntu-24.04
    timeout-minutes: 25
    permissions:
      contents: read
      packages: write        # 推送镜像
      id-token: write        # provenance 证明
      attestations: write
    outputs:
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - uses: actions/checkout@<SHA>
        with:
          persist-credentials: false
      - uses: docker/setup-buildx-action@<SHA>
      - uses: docker/login-action@<SHA>
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@<SHA>
        with:
          images: ghcr.io/OWNER/REPO/api
          tags: |
            type=ref,event=tag
            type=sha,prefix=sha-
      - name: 构建并推送
        id: push
        uses: docker/build-push-action@<SHA>
        with:
          context: backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          provenance: mode=max
          sbom: true
          cache-from: type=gha,scope=api
          cache-to: type=gha,mode=max,scope=api
      - name: 来源证明
        uses: actions/attest-build-provenance@<SHA>
        with:
          subject-name: ghcr.io/OWNER/REPO/api
          subject-digest: ${{ steps.push.outputs.digest }}
          push-to-registry: true

  build-web:
    runs-on: ubuntu-24.04
    timeout-minutes: 25
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
    outputs:
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - uses: actions/checkout@<SHA>
        with:
          persist-credentials: false
      - uses: docker/setup-buildx-action@<SHA>
      - uses: docker/login-action@<SHA>
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@<SHA>
        with:
          images: ghcr.io/OWNER/REPO/web
          tags: |
            type=ref,event=tag
            type=sha,prefix=sha-
      - name: 构建并推送
        id: push
        uses: docker/build-push-action@<SHA>
        with:
          context: frontend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          provenance: mode=max
          sbom: true
          cache-from: type=gha,scope=web
          cache-to: type=gha,mode=max,scope=web
      - name: 来源证明
        uses: actions/attest-build-provenance@<SHA>
        with:
          subject-name: ghcr.io/OWNER/REPO/web
          subject-digest: ${{ steps.push.outputs.digest }}
          push-to-registry: true

  staging:
    needs: [build-api, build-web]
    uses: ./.github/workflows/deploy.yml
    with:
      environment: staging
      api_digest: ${{ needs.build-api.outputs.digest }}
      web_digest: ${{ needs.build-web.outputs.digest }}
    secrets:
      DEPLOY_HOST: ${{ secrets.STAGING_DEPLOY_HOST }}
      DEPLOY_USER: ${{ secrets.STAGING_DEPLOY_USER }}
      DEPLOY_SSH_KEY: ${{ secrets.STAGING_DEPLOY_SSH_KEY }}

  production:
    needs: [build-api, build-web, staging]
    uses: ./.github/workflows/deploy.yml
    with:
      environment: production
      api_digest: ${{ needs.build-api.outputs.digest }}
      web_digest: ${{ needs.build-web.outputs.digest }}
    secrets:
      DEPLOY_HOST: ${{ secrets.PROD_DEPLOY_HOST }}
      DEPLOY_USER: ${{ secrets.PROD_DEPLOY_USER }}
      DEPLOY_SSH_KEY: ${{ secrets.PROD_DEPLOY_SSH_KEY }}
```

> 为什么不用 `matrix` 输出 digest：matrix 的多个实例共享同一个 `outputs`，后完成的会覆盖前一个，导致"部署了 api 的 digest 到 web"。前后端是两个独立产物，必须拆成两个 job、两个输出。

### A.3 `.github/workflows/deploy.yml`

```yaml
# 职责：迁移 → 部署 → 冒烟 → 失败回滚。被 release.yml 调用，也可手工回滚。
name: deploy

on:
  workflow_call:
    inputs:
      environment:
        description: 目标环境
        required: true
        type: string
      api_digest:
        description: 后端镜像 digest（sha256:...）
        required: true
        type: string
      web_digest:
        description: 前端镜像 digest（sha256:...）
        required: true
        type: string
    secrets:
      DEPLOY_HOST:
        required: true
      DEPLOY_USER:
        required: true
      DEPLOY_SSH_KEY:
        required: true
  workflow_dispatch:
    inputs:
      environment:
        description: 目标环境
        required: true
        type: choice
        options: [staging, production]
      api_digest:
        description: 要部署的后端 digest（回滚时填上一个 digest）
        required: true
        type: string
      web_digest:
        description: 要部署的前端 digest（回滚时填上一个 digest）
        required: true
        type: string

permissions:
  contents: read
  packages: read

concurrency:
  group: deploy-${{ inputs.environment }}
  cancel-in-progress: false

jobs:
  migrate:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    environment: ${{ inputs.environment }}
    steps:
      - name: 校验 digest 格式
        env:
          API_DIGEST: ${{ inputs.api_digest }}
          WEB_DIGEST: ${{ inputs.web_digest }}
        run: |
          set -euo pipefail
          for d in "$API_DIGEST" "$WEB_DIGEST"; do
            [[ "$d" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "拒绝非 digest 引用: $d"; exit 1; }
          done
      - name: 配置 SSH
        env:
          SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          HOST: ${{ secrets.DEPLOY_HOST }}
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh && chmod 700 ~/.ssh
          printf '%s\n' "$SSH_KEY" > ~/.ssh/id_deploy && chmod 600 ~/.ssh/id_deploy
          ssh-keyscan -H "$HOST" >> ~/.ssh/known_hosts
      - name: 备份数据库
        env:
          HOST: ${{ secrets.DEPLOY_HOST }}
          USER_: ${{ secrets.DEPLOY_USER }}
        run: |
          set -euo pipefail
          ssh -i ~/.ssh/id_deploy "$USER_@$HOST" '/srv/app/scripts/backup-db.sh'
      - name: 执行迁移（expand 阶段）
        env:
          HOST: ${{ secrets.DEPLOY_HOST }}
          USER_: ${{ secrets.DEPLOY_USER }}
          API_DIGEST: ${{ inputs.api_digest }}
          WEB_DIGEST: ${{ inputs.web_digest }}
        run: |
          set -euo pipefail
          ssh -i ~/.ssh/id_deploy "$USER_@$HOST" \
            "cd /srv/app && ./scripts/ci/promote.sh migrate '$API_DIGEST' '$WEB_DIGEST'"

  deploy:
    needs: migrate
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    environment: ${{ inputs.environment }}
    steps:
      - name: 校验 digest 格式
        env:
          API_DIGEST: ${{ inputs.api_digest }}
          WEB_DIGEST: ${{ inputs.web_digest }}
        run: |
          set -euo pipefail
          for d in "$API_DIGEST" "$WEB_DIGEST"; do
            [[ "$d" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "拒绝非 digest 引用: $d"; exit 1; }
          done
      - uses: actions/checkout@<SHA>
        with:
          persist-credentials: false
      - name: 配置 SSH
        env:
          SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          HOST: ${{ secrets.DEPLOY_HOST }}
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh && chmod 700 ~/.ssh
          printf '%s\n' "$SSH_KEY" > ~/.ssh/id_deploy && chmod 600 ~/.ssh/id_deploy
          ssh-keyscan -H "$HOST" >> ~/.ssh/known_hosts
      - name: 部署
        env:
          HOST: ${{ secrets.DEPLOY_HOST }}
          USER_: ${{ secrets.DEPLOY_USER }}
          API_DIGEST: ${{ inputs.api_digest }}
          WEB_DIGEST: ${{ inputs.web_digest }}
        run: |
          set -euo pipefail
          ssh -i ~/.ssh/id_deploy "$USER_@$HOST" \
            "cd /srv/app && ./scripts/ci/promote.sh deploy '$API_DIGEST' '$WEB_DIGEST'"
      - name: 冒烟
        id: smoke
        env:
          BASE_URL: ${{ vars.APP_BASE_URL }}
          EXPECT_COMMIT: ${{ github.sha }}
        run: |
          set -euo pipefail
          ./scripts/ci/smoke.sh "$BASE_URL"
      - name: 确认部署（记录为当前 digest）
        if: success()
        env:
          HOST: ${{ secrets.DEPLOY_HOST }}
          USER_: ${{ secrets.DEPLOY_USER }}
          API_DIGEST: ${{ inputs.api_digest }}
          WEB_DIGEST: ${{ inputs.web_digest }}
        run: |
          set -euo pipefail
          ssh -i ~/.ssh/id_deploy "$USER_@$HOST" \
            "cd /srv/app && ./scripts/ci/promote.sh confirm '$API_DIGEST' '$WEB_DIGEST'"
      - name: 回滚
        if: failure()
        env:
          HOST: ${{ secrets.DEPLOY_HOST }}
          USER_: ${{ secrets.DEPLOY_USER }}
        run: |
          set -euo pipefail
          ssh -i ~/.ssh/id_deploy "$USER_@$HOST" \
            'cd /srv/app && ./scripts/ci/promote.sh rollback'
```

### A.4 `backend/Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1

# ---------- 构建层：装依赖 + 装项目 ----------
FROM python:3.13-slim@sha256:<BASE_IMAGE_DIGEST> AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# 先只拷依赖清单，改代码不失效依赖缓存
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-group dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-group dev

# ---------- 运行层：只带运行时 ----------
FROM python:3.13-slim@sha256:<BASE_IMAGE_DIGEST> AS runtime

RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --no-create-home app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
```

说明：`--no-group dev` 要求 dev 依赖声明在 `[dependency-groups] dev`。若项目仍用旧的 `[tool.uv] dev-dependencies`，改用 `--no-dev`。构建内用 `--frozen` 是允许的——CI 已用 `--locked` 校验过同一份 lockfile。

### A.5 `frontend/Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1

FROM node:22-alpine@sha256:<BASE_IMAGE_DIGEST> AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine@sha256:<BASE_IMAGE_DIGEST> AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine@sha256:<BASE_IMAGE_DIGEST> AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -S -g 1001 nodejs && adduser -S -u 1001 -G nodejs nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
```

`next.config.ts` 必须包含：

```ts
const nextConfig = {
  output: 'standalone',
}
export default nextConfig
```

### A.6 `deploy/docker-compose.yml`

```yaml
# 部署用 compose：镜像必须是 digest 引用，由 API_IMAGE / WEB_IMAGE 注入
services:
  api:
    image: ${API_IMAGE:?API_IMAGE 必须是 digest 引用}
    restart: unless-stopped
    env_file:
      - /srv/app/.env
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"]
      interval: 30s
      timeout: 3s
      start_period: 30s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  web:
    image: ${WEB_IMAGE:?WEB_IMAGE 必须是 digest 引用}
    restart: unless-stopped
    env_file:
      - /srv/app/.env
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
      interval: 30s
      timeout: 5s
      start_period: 30s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  db:
    image: postgres:18
    restart: unless-stopped
    env_file:
      - /srv/app/.env
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \"$${POSTGRES_USER}\" -d \"$${POSTGRES_DB}\""]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
```

`db` 不暴露端口；后端通过服务名访问。生产库若托管，删除 `db` 服务、把连接串指向托管实例。

### A.7 `scripts/ci/promote.sh`（部署机）

```bash
#!/usr/bin/env bash
# 用法：
#   promote.sh migrate  <api_digest> <web_digest>   # 在目标机上跑 alembic upgrade head
#   promote.sh deploy   <api_digest> <web_digest>
#   promote.sh confirm  <api_digest> <web_digest>
#   promote.sh rollback                             # 回到 .deployed-digest 记录的那一版
# 部署机执行，只接受 digest，拒绝 tag。
set -euo pipefail

action="${1:?用法: promote.sh <migrate|deploy|confirm|rollback> [api_digest] [web_digest]}"

cd /srv/app

repo="${IMAGE_REPO:?需要 IMAGE_REPO，如 ghcr.io/OWNER/REPO}"

check_digest() {
  case "$1" in
    sha256:*) ;;
    *) echo "拒绝非 digest 引用：$1" >&2; exit 1 ;;
  esac
}

# compose 解析整个文件时会对所有服务做变量插值，因此两个 digest 都要给
set_images() {
  export API_IMAGE="${repo}/api@${1}"
  export WEB_IMAGE="${repo}/web@${2}"
}

take_digests() {
  api="${1:?缺少 api digest}"
  web="${2:?缺少 web digest}"
  check_digest "$api"
  check_digest "$web"
}

case "$action" in
  migrate)
    take_digests "${2:-}" "${3:-}"
    set_images "$api" "$web"
    docker compose run --rm --no-deps api alembic upgrade head
    echo "迁移完成"
    ;;
  deploy)
    take_digests "${2:-}" "${3:-}"
    set_images "$api" "$web"
    docker compose pull --quiet api web
    docker compose up -d --wait --no-deps api web
    echo "已启动 api=${api} web=${web}"
    ;;
  confirm)
    take_digests "${2:-}" "${3:-}"
    printf 'api=%s\nweb=%s\n' "$api" "$web" > .deployed-digest
    echo "已记录当前部署"
    ;;
  rollback)
    [ -f .deployed-digest ] || { echo "没有可回滚的记录" >&2; exit 1; }
    api="$(sed -n 's/^api=//p' .deployed-digest)"
    web="$(sed -n 's/^web=//p' .deployed-digest)"
    [ -n "$api" ] && [ -n "$web" ] || { echo "回滚记录不完整" >&2; exit 1; }
    set_images "$api" "$web"
    docker compose pull --quiet api web
    docker compose up -d --wait --no-deps api web
    echo "已回滚到 api=${api} web=${web}"
    ;;
  *)
    echo "未知动作：$action" >&2
    exit 1
    ;;
esac
```

### A.8 `scripts/ci/smoke.sh`（流水线执行）

```bash
#!/usr/bin/env bash
# 用法：smoke.sh <base-url>
set -euo pipefail

base="${1:?缺少 base url}"

fail() { echo "冒烟失败：$*" >&2; exit 1; }

# 1) 就绪：连续 3 次 200
for i in 1 2 3; do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${base}/readyz" || true)"
  [ "$code" = "200" ] || fail "/readyz 第 ${i} 次返回 ${code}"
  sleep 2
done

# 2) 存活与版本
body="$(curl -fsS --max-time 5 "${base}/healthz")" || fail "/healthz 不可达"
echo "$body" | grep -q '"status":"ok"' || fail "/healthz 状态非 ok：$body"

if [ -n "${EXPECT_COMMIT:-}" ]; then
  echo "$body" | grep -q "\"commit\":\"${EXPECT_COMMIT:0:7}\"" \
    || fail "线上 commit 与本次不一致：期望 ${EXPECT_COMMIT:0:7}，实际 ${body}"
fi

# 3) 关键只读接口
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${base}/api/v1/ping" || true)"
[ "$code" = "200" ] || fail "/api/v1/ping 返回 ${code}"

echo "冒烟通过：${base}"
```

> `/api/v1/ping` 是占位路径，落地时替换为该服务的实际只读健康接口（契约见 `api-design` 约定，错误信封见 `spec/frontend/frontend-guide.md` 第 9 章）。
