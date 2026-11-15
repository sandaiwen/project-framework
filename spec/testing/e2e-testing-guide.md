---
version: 1.0.0
last_updated: 2026-11-15
---

# 端到端测试规范（E2E Testing）

适用：`frontend/e2e/` 下由 Playwright 驱动的测试，以及被它驱动的真实前后端进程。

E2E 只回答一个问题：**用户从浏览器出发，能不能完成这件事。** 它能证明的只有这一件事，不要指望它承担更细的验证。

---

## 1. 边界：什么该放 E2E

必须覆盖的五类（每类至少一条）：

1. **登录 / 登出 / 会话过期后的跳转**。
2. **核心业务主路径**：创建 → 列表可见 → 详情正确（每个业务模块一条）。
3. **表单校验与错误提示**：必填缺失、格式错误、后端返回业务错误的展示。
4. **权限边界**：无权用户看不到入口，直接访问 URL 被拒。
5. **破坏性操作**：删除/取消前的二次确认，确认后状态更新。
6. **async Server Component 的渲染结果**（单测测不了，只能在这里证明）。

不适合放 E2E 的，按下面的判据下沉：

| 情况 | 下沉到 | 理由 |
| --- | --- | --- |
| 纯计算、字段格式化、校验规则 | 前端单测 | 成本低一个数量级 |
| 单组件交互、loading 态 | 组件测试 | 无需浏览器 |
| 后端状态码 / schema / 鉴权矩阵 | 后端接口测试 | 比浏览器快 50 倍 |
| 需要等很久才出现的业务状态（异步任务完成、批量回写） | 注入替身的接口测试 | 不确定性不适合当同步门禁 |
| 需要精确控制内部调用顺序 | 单元测试 | E2E 无法注入 |

最后两行是判断准则：**"要等"或"要注入"的逻辑不上 E2E**。它们不是不重要，而是放错了层就无法稳定。

---

## 2. 服务编排与探活

### 2.1 服务由配置层拉起，不由测试代码拉起

`playwright.config.ts` 的 `webServer` 负责启动被测服务；测试代码只负责"连上去"和"断言"。测试里出现 `spawn` / `exec` / `docker compose up` 一律不允许——那会让"本地能跑、CI 不能跑"成为常态。

```ts
webServer: [
  {
    command: 'npm run build && npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  {
    command: 'cd ../backend && uv run uvicorn app.main:app --port 8000',
    url: 'http://localhost:8000/healthz',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
]
```

- MUST 跑**生产构建**（`build` + `start`），不跑 `dev`。开发模式有热更新与调试开销，行为和生产不一致。
- MUST `reuseExistingServer: !process.env.CI`：本地复用已起服务，CI 每次新起。
- MUST 两个服务都配 `url`，让 Playwright 轮询就绪而不是固定等待。
- MUST 就绪判断用 HTTP 探针（`/healthz`），不用"端口通就算活着"。
- MUST NOT 在用例或 `beforeAll` 里手工 `sleep` 等服务。

### 2.2 探活只做一次，且结果是缓存的

服务级探活由 `webServer.url` 完成。测试内部**不再重复探活**；确需额外前置检查（例如数据库是否空库）时，放在 `globalSetup` 里做一次，并缓存结论。

- MUST 把"环境就绪检查"集中到 `globalSetup` 或 `webServer`，不要散落在每个 spec 的 `beforeAll`。
- SHOULD 探活失败时把**原因**写进错误信息（哪个地址、什么错、期望什么），而不是裸 `assert false`。

### 2.3 缺依赖时必须失败，不许跳过

| 情况 | 后端单测 | E2E |
| --- | --- | --- |
| 缺数据库 / 缺 key / 服务没起 | `skip` 并写明缺什么 | **`fail`** |

- MUST E2E 缺前置条件时失败，不 `test.skip()`。跳过会让"其实一个用例都没跑"看起来像绿，而 E2E 恰恰是发布前唯一的整体验证。
- MUST NOT 用 `test.skip(process.env.CI !== 'true')` 之类条件把 E2E 变成"只有 CI 才跑、本地永远绿"。本地不方便跑就写清命令，不要假装通过。
- 唯一例外：**明确标注为可选**的跨浏览器 / 可访问性用例，用 project 或 tag 排除（排除要出现在汇总里），不用 `skip`。

---

## 3. 配置

```ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['list'], ['html', { open: 'never' }], ['junit', { outputFile: 'test-results/junit.xml' }]],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    testIdAttribute: 'data-testid',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [/* 见 2.1 */],
})
```

规则：

- MUST `forbidOnly: !!process.env.CI`：防止 `test.only` 被合并进主干。
- MUST 默认只跑 chromium。加 Firefox / WebKit 或移动视口要有明确理由（跨端兼容需求），不要默认全开三引擎拖慢流水线。
- MUST 失败时保留 `trace`（`on-first-retry`）与截图；CI 上传 `playwright-report/` 与 `test-results/`。
- MUST NOT 把 `trace: 'off'` 当作提速手段长期保留；失败无法定位的代价远高于存储。
- SHOULD CI 上 `workers` 不超过数据库连接池上限的一半，避免并发把连接打满导致假失败。

---

## 4. 造数与清理

### 4.1 用 API 造数，不用 UI 点击

- MUST 前置数据通过接口创建（直接调后端 API 或测试专用 client），不用"点开页面填表单"准备数据。UI 造数会把被测流程和准备流程耦合，一处改版两条一起红。
- MUST 每条数据带唯一标识：`e2e-${Date.now()}-${randomUUID().slice(0, 8)}`，写进名称、邮箱、备注等可检索字段。
- MUST NOT 依赖库里已有的固定数据（"demo 用户""已有 3 条订单"），这类依赖会在数据变动时整片失败。
- MUST NOT 指向生产库或生产环境。

### 4.2 资源登记 + LIFO 清理

```ts
// e2e/fixtures.ts
export const test = base.extend<{ resources: ResourceManager }>({
  resources: async ({ request }, use) => {
    const rm = new ResourceManager(request)
    await rm.init()
    try {
      await use(rm)
    } finally {
      await rm.teardown()   // LIFO，单条失败不阻断其余
    }
  },
})
```

```ts
class ResourceManager {
  private cleanups: Array<() => Promise<void>> = []

  defer(fn: () => Promise<void>) { this.cleanups.push(fn) }

  async key() {
    const key = await this.createKey()
    this.defer(() => this.deleteKey(key.id))
    return key
  }

  async teardown() {
    for (const fn of this.cleanups.reverse()) {
      try { await fn() } catch { /* best-effort：清不掉不掩盖主用例失败 */ }
    }
  }
}
```

- MUST 每个创建的资源**当场登记**清理函数，不靠用例末尾手写一串 `delete`。
- MUST 清理失败不能让后续用例失败，也不能吞掉主用例的失败（用 `try/finally` 而非 `catch` 包住断言）。
- MUST 清理顺序 LIFO（后创建的先删），保证外键依赖不倒挂。
- MUST 用例开始时的 `init()` 放在 `try` 内，半途失败也要回收。

### 4.3 全局清库要有守卫

E2E 可能出现"整批跑失败、数据残留"，于是有人加一条"session 结束清库"。这条很危险：一旦 `DATABASE_URL` 指向共享实例，一次误跑就清掉别人的数据。

- MUST 清理全局数据前确认"本次真的有 E2E 用例执行过"（例如设置一个 session 级标志，只有它被置位才清库）。
- MUST 只清 `e2e-` 前缀命中的数据；`TRUNCATE` / `DROP` 只允许在专门的本地重置脚本里，且脚本名要写明 `reset-e2e-db`。
- SHOULD 提供 `npm run e2e:reset` 手工重置入口，而不是让用例自己决定什么时候清库。

### 4.4 登录态复用

- MUST 跨用例共享的登录态用 `storageState`，不用每个用例点一遍登录页。
- MUST 不同角色各一份 storage state（`admin.json` / `user.json`），按用例需要选择，不要一个账号测所有权限。

---

## 5. 等待与选择器

### 5.1 选择器优先级

`getByRole` > `getByLabel` > `getByText` > `getByTestId` > CSS。

- MUST 优先 `getByRole(name)`
- MUST NOT 按 class、`nth-child`、DOM 层级定位。
- SHOULD `data-testid` 只加在"没有稳定语义"的容器上（如虚拟列表行），并保持命名与业务一致。

### 5.2 等待

- MUST 等待用自动重试断言：`await expect(locator).toBeVisible()`、`await expect(page).toHaveURL(...)`。
- MUST NOT `waitForTimeout` / `sleep` / `page.waitFor(3000)`。
- MUST 需要"等后端最终一致"（异步任务写完、缓存刷新）时，用**轮询到截止时间**的辅助函数：

```ts
await expect
  .poll(async () => (await api.getOrder(id)).status, { timeout: 30_000, intervals: [500, 1000, 2000] })
  .toBe('paid')
```

- MUST 轮询函数超时后抛出带最后状态的错误（"期望 paid，30s 内最后一次是 pending"），不要静默返回。

---

## 6. 断言

- MUST 断言用户可见结果：URL、可见文案、元素可见性、列表条数变化。
- MUST 至少一处验证"数据真的落地"：刷新页面后仍可见，或列表接口返回包含新建项。
- MUST NOT 只断言"没有报错"。没有错误不等于功能正确。
- MUST 对关键写入额外用接口断言服务端结果（比 UI 断言更直接、更早失败）。
- MUST 错误信息带上下文：实际 URL、实际可见文案、接口返回码与片段。

```ts
test('创建订单后列表可见', async ({ page, request }) => {
  const sku = `e2e-${Date.now()}`
  await page.goto('/orders/new')
  await page.getByLabel('SKU').fill(sku)
  await page.getByRole('button', { name: '保存' }).click()

  await expect(page).toHaveURL(/\/orders$/)
  await expect(page.getByRole('cell', { name: sku })).toBeVisible()

  // 服务端确认（不依赖 UI 缓存）
  const resp = await request.get(`/api/v1/orders?sku=${sku}`)
  expect(resp.ok(), `查询失败：${resp.status()} ${await resp.text()}`).toBeTruthy()
  expect((await resp.json()).items).toHaveLength(1)
})
```

---

## 7. 代码组织：请求收敛、页面对象

- MUST 所有 API 造数与断言收敛到 `e2e/api-client.ts`（或同层模块），**spec 文件里禁止直接 `fetch` / `request.get` 拼裸 URL**。原因：URL 变更时要改一处，而不是三十处。
- SHOULD 页面交互收敛到 `e2e/pages/*.page.ts`（Page Object），spec 只写"做什么"，不写"点第几个 div"。
- MUST NOT 为每个页面都造 Page Object；只在被 ≥3 条用例复用的页面建。
- SHOULD 一个 spec 文件对应一个业务域（`orders.spec.ts`、`auth.spec.ts`），用例数超过 15 条时按场景拆分。

---

## 8. 行为清单（分母）

E2E 最大的问题是"永远觉得覆盖够了"。解法是**先写清单，再写用例**：`e2e/behaviors.yaml` 一行一个"用户可感知的行为"，用例标题带该行 id。

```yaml
# e2e/behaviors.yaml
- id: B-01
  area: auth
  tier: P0
  behavior: 邮箱密码登录成功后进入工作台
  spec: e2e/auth.spec.ts
- id: B-02
  area: orders
  tier: P0
  behavior: 创建订单后列表可见且刷新仍在
  spec: e2e/orders.spec.ts
- id: B-03
  area: orders
  tier: P1
  behavior: 无权限用户看不到删除按钮，直连 URL 被拒
  spec: e2e/orders.spec.ts
```

```ts
test('[B-02] 创建订单后列表可见且刷新仍在', async ({ page }) => { /* ... */ })
```

- MUST 每个 P0 行为都有对应用例；P1 允许延期，但要在清单里标 `status: gap` 并写明计划。
- MUST 清单与用例双向一致：有清单没用例 = 缺口，有用例没清单 = 不知道在防什么。
- SHOULD 用一条脚本在 CI 校验一致性（读 yaml + `--list` 输出，比对 id 集合），避免清单一改就腐化。
- SHOULD 在清单里记 `status: gap` 与原因（"需要第三方回调，暂不覆盖"），**缺口写出来比假装覆盖更专业**。

### 8.1 tag 分层

| tag | 含义 | 跑在 |
| --- | --- | --- |
| `@smoke` | 核心主路径，≤10 条，5 分钟内 | 合并主干、发布前 |
| `@regression` | 已修缺陷的 E2E 复现（另需登记表） | 发布前、夜间 |
| 无 tag | 全量用例 | 夜间 |

- MUST `@smoke` 覆盖 behaviors.yaml 里所有 `tier: P0` 中最关键的路径，数量控制在 10 条以内。
- MUST `package.json` 提供 `e2e` / `e2e:smoke` / `e2e:regression` 三个脚本，CI 与本地用同一条命令。

---

## 9. 失败产物

- MUST 保留 trace（`on-first-retry`）、失败截图、视频（`retain-on-failure`）。
- MUST CI 把 `playwright-report/`、`test-results/` 作为构建产物上传，保留期 ≥ 7 天。
- MUST 失败信息包含：实际 URL、实际可见文案、接口状态码与响应片段。定位靠这些，不靠重跑。
- SHOULD 对"元素不可见"类失败额外输出该区域 HTML 片段（Playwright 的 `expect(locator).toBeVisible()` 已含部分信息，不够时补一条 `console.log(await locator.page().content())` 仅在失败分支）。

---

## 10. CI 分层

| 阶段 | 命令 | 时长目标 | 阻断 |
| --- | --- | --- | --- |
| PR | 不跑 E2E（跑后端接口与前端单测） | — | — |
| 合并主干 | `npm run e2e:smoke` | < 10 min | 是 |
| 夜间 | `npm run e2e`（全量）+ `npm run e2e:regression` | 不限 | 否，次日修 |
| 发布前 | `e2e:smoke` + `e2e:regression` | < 20 min | 是 |

- MUST 合并主干与发布前由同一份 `behaviors.yaml` 的 P0 集合驱动，不维护第二份"冒烟清单"。
- MUST NOT 在 PR 上跑全量 E2E；那会让 PR 反馈从 10 分钟退化到 40 分钟，最后所有人都开始绕过流水线。

---

## 11. 反例

| 反例 | 问题 | 改法 |
| --- | --- | --- |
| `await page.waitForTimeout(3000)` | 慢且不稳，机器快时也等 3 秒 | `expect(locator)` 自动重试 |
| 用 `test.skip()` 处理"服务没起" | 整批静默不跑 | `webServer.url` 让它直接失败 |
| 每个用例点一遍登录 | 15 条用例 15 次登录 | `storageState` |
| 一个 spec 断言 20 个页面 | 第一个失败后信息全丢 | 按业务域拆 |
| 只断页面上有"保存成功" | 数据可能没落库 | 加接口断言 + 刷新后仍在 |
| 用 UI 造前置数据 | 一处改版两条一起红 | 用 API 造数 |
| 靠"重跑就过了"交付 | flaky 每天复发 | 查根因（README 3 节） |

---

## 12. 提交前检查清单

- [ ] 用例落在 `frontend/e2e/`，标题带 `behaviors.yaml` 里的 id。
- [ ] 服务由 `webServer` 拉起，跑的是 `build && start`，没有在测试里 spawn 进程。
- [ ] 缺环境时是 fail 而不是 skip。
- [ ] 数据用 API 造、带唯一前缀、登记清理，LIFO 且 best-effort。
- [ ] 没有 `waitForTimeout`；等待用自动重试断言或轮询到截止时间。
- [ ] 选择器用 role / label / text；没有 class 与 nth-child。
- [ ] 断言了用户可见结果，且至少一处验证数据落地。
- [ ] 请求收敛在 `api-client`，spec 里没有裸 URL。
- [ ] 失败产物（trace / 截图 / 报告）能被 CI 收集。
- [ ] `@smoke` 集合 ≤10 条且覆盖 P0 路径。
