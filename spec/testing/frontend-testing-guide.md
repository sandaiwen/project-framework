---
version: 1.0.0
last_updated: 2026-11-15
---

# 前端测试规范（Frontend Testing）

适用：`frontend/` 下的单元与组件测试。技术栈 Next.js（App Router）/ React 19 / TypeScript / Vitest + React Testing Library / shadcn/ui + Tailwind。

浏览器里的跨页流程、async Server Component 走 E2E，见 `spec/testing/e2e-testing-guide.md`；造数与隔离见 `spec/testing/test-data-guide.md`。

---

## 1. 工具与配置

| 用途 | 工具 |
| --- | --- |
| 单元 / 组件测试 | Vitest + React Testing Library + jsdom |
| DOM 断言 | `@testing-library/jest-dom`（`/vitest` 入口） |
| 交互 | `@testing-library/user-event` |
| 数据层 | 注入 client，或 `msw` 拦截 HTTP |
| E2E | Playwright |
| 可访问性（可选） | `@axe-core/playwright` |

```bash
npm i -D vitest @vitejs/plugin-react jsdom \
  @testing-library/react @testing-library/dom @testing-library/jest-dom \
  @testing-library/user-event vite-tsconfig-paths @vitest/coverage-v8
```

`vitest.config.mts`：

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['e2e/**', 'node_modules/**', '.next/**'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/app/**/layout.tsx',
        'src/app/**/page.tsx',
        'src/app/**/loading.tsx',
        'src/app/**/error.tsx',
      ],
      reporter: ['text-summary', 'html', 'lcov'],
      thresholds: { lines: 80, branches: 75, functions: 80, statements: 80 },
    },
  },
})
```

`vitest.setup.ts`：

```ts
import '@testing-library/jest-dom/vitest'
```

`package.json` 脚本：

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "e2e": "playwright test"
  }
}
```

规则：

- MUST `@testing-library/jest-dom` 用 `/vitest` 入口并写进 `setupFiles`；用默认入口匹配器不会注册。
- MUST `exclude` 掉 `e2e/**`，否则 Vitest 会尝试加载 Playwright 用例并报错。
- MUST `coverage.include` 明确写出源码范围；不写则只统计"被 import 过的文件"，未测文件不进分母，覆盖率虚高。
- MUST 排除 `page.tsx` / `layout.tsx` / `loading.tsx` / `error.tsx`（纯装配层），但不得排除 `features/**` 下的业务代码。
- MUST 这些命令真的进 CI。**有配置无执行等于没有门禁**：仓库里躺着 400 个测试文件、CI 里一条不跑，"已覆盖"就是错觉。

---

## 2. 能测与不能测

| 对象 | 可单测 | 方式 |
| --- | --- | --- |
| 纯函数（格式化、校验、计算） | 是 | 直接断言输入输出 |
| 自定义 hook | 是 | `renderHook` |
| 同步 Client Component | 是 | RTL 渲染 + `userEvent` |
| 同步 Server Component | 是 | RTL 渲染（无 hooks 时） |
| **async Server Component** | **否** | 走 E2E |
| 数据请求函数 | 是 | 注入 fetch 实现或 MSW |
| 样式、动画、布局 | 否 | 人工/截图评审，不写断言 |

- MUST async Server Component 的测试用 Playwright 覆盖。Vitest 不支持 async Server Component，硬测只能得到"重新实现一遍组件"的假测试。
- MUST NOT 为第三方组件库（shadcn 生成的 `components/ui/*`）写行为测试；它们的行为由上游负责。只测自己业务层的封装。
- MUST NOT 断言 CSS 类名、DOM 层级、组件内部 state；这些随实现变动，不随需求变动。
- SHOULD 一个组件测试文件只测一个组件，文件与被测组件同目录、同名 + `.test.tsx`。

---

## 3. 组件测试

```tsx
import { expect, test, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OrderTable } from './order-table'

test('空列表时展示空态', () => {
  render(<OrderTable orders={[]} />)
  expect(screen.getByText('暂无订单')).toBeInTheDocument()
})

test('点击删除后调用回传函数', async () => {
  const user = userEvent.setup()
  const onDelete = vi.fn()
  render(<OrderTable orders={[{ id: '1', sku: 'A-1' }]} onDelete={onDelete} />)

  await user.click(screen.getByRole('button', { name: '删除 A-1' }))

  expect(onDelete).toHaveBeenCalledWith('1')
})
```

规则：

- MUST 用 `getByRole` / `getByLabelText` / `getByText` 查询。`getByTestId` 只在没有语义可依靠时使用，并说明原因。
- MUST NOT 用 `container.querySelector` 按 class 选元素。
- MUST 交互用 `userEvent`，不用 `fireEvent`（`userEvent` 走完整事件序列，更接近真实点击）。
- MUST 每个组件至少覆盖：正常态、空态、错误态；有请求的组件还要有加载态。
- MUST 断言用户可见结果（文案、可见性、可访问属性）或回传函数的入参。
- MUST NOT 用 `vi.mock` 掉被测组件自身依赖的 hooks 来"让它能渲染"——这等于把被测逻辑整体替换掉，应改为传入 props。

### 3.1 四种状态用一个用例族

把状态覆盖写成同一组断言，避免"加了 error 分支但没人测"：

```tsx
test.each([
  ['loading', { status: 'loading' as const }],
  ['empty', { status: 'success' as const, data: [] }],
  ['error', { status: 'error' as const, error: new Error('boom') }],
  ['success', { status: 'success' as const, data: [order] }],
])('%s 状态渲染对应内容', (_, props) => {
  render(<OrderTable {...props} />)
  // 每个状态断言一个稳定标识，不强绑文案
})
```

- SHOULD 用 `test.each` 而不是复制四份；新增状态时缺一格会立刻被发现。

---

## 4. 快照

- MUST NOT 用整页/大组件快照作为主要断言。快照只反映"输出变了"，不判断"变对了"，且会随无关改动大面积失效。
- MAY 对稳定的纯渲染片段用小范围快照，且必须与人工评审一起提交。
- MUST 更新快照前逐条看 diff，禁止 `-u` 批量覆盖后不看内容。
- MUST 快照文件入库，且与组件同目录，便于 review 时看到"哪一块变了"。

---

## 5. 数据层测试

- MUST 测取数函数时拦截 HTTP 而非替换全局 `fetch`：优先注入 client，其次 `msw`。
- MUST 断言请求 URL、方法、关键参数，以及响应到领域对象的转换结果。
- MUST NOT 在组件测试里打真实后端；需要"真实配合"的放 E2E。
- MUST 对错误路径至少覆盖：非 2xx、网络异常、JSON 解析失败三种。后两种最容易被漏，也最常在生产出现。

```ts
import { expect, test, vi } from 'vitest'

test('查询订单带上分页参数', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }),
  )
  const list = createOrderApi({ fetch: fetchMock })

  await list({ page: 2, size: 20 })

  expect(fetchMock).toHaveBeenCalledWith('/api/v1/orders?page=2&size=20', expect.anything())
})
```

### 5.1 类型与契约

- MUST 前端 API 类型由后端 `openapi.json` **生成**，不手写（`npx openapi-typescript docs/openapi.json -o src/types/api.d.ts`）。
- MUST 生成物入库；CI 里重生成后跑 `git diff --exit-code src/types/api.d.ts`，不一致即失败（规则见 regression 规范 7.1）。
- MUST NOT 为了"让类型对上"改生成文件；改后端契约或改生成命令。
- SHOULD 用 `expectTypeOf`（Vitest 内置）对关键映射做类型断言，防止 `any` 悄悄扩散。

---

## 6. 可访问性（可选）

对登录、表单、列表这类核心页面，SHOULD 加一条 axe 检查（放 E2E，不放单测）：

```ts
import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('登录页无可访问性违规', async ({ page }) => {
  await page.goto('/login')
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations).toEqual([])
})
```

不为每个页面都加；只为用户高频到达、含表单交互的页面加。细则见 `spec/frontend/frontend-guide.md` 的无障碍章节。

---

## 7. 反例

| 反例 | 问题 | 改法 |
| --- | --- | --- |
| 只断言"渲染没报错" | 什么都没验证 | 断言可见文案或可访问属性 |
| 按 class 选元素 | 改样式就红，改行为不红 | `getByRole` |
| `waitFor` 里包一个立即为真的断言 | 等价于 sleep | 直接 `findBy*` 等待元素出现 |
| 每个组件一份整页快照 | 噪声大、review 看不完 | 小范围快照或删掉 |
| `vi.mock` 掉数据 hooks | 测的是 mock 不是组件 | 传 props 或用 MSW |
| 只测成功路径 | 错误态在生产首现 | 覆盖 4 种状态 |
| 写了测试但 CI 不跑 | 门禁形同不存在 | 加进 CI（README 2 节） |

---

## 8. 提交前检查清单

- [ ] 测试文件与被测文件同目录、同名 + `.test.ts(x)`，且被 `include` 命中。
- [ ] 组件覆盖正常/空/错误/加载四态（有请求时）。
- [ ] 查询用 role / label / text；没有 `querySelector` 与 class 选择器。
- [ ] 交互用 `userEvent`；等待用 `findBy*` 或 `waitFor` 包真实条件。
- [ ] 没有新增整页快照；更新快照前看过 diff。
- [ ] 数据层断言了 URL、方法、关键参数与转换结果；错误路径有覆盖。
- [ ] `src/types/api.d.ts` 是生成物且与 `docs/openapi.json` 一致。
- [ ] 覆盖率达标（lines 80 / branches 75），未通过 `exclude` 排除业务代码。
- [ ] `npm run test:run` 与 `npx tsc --noEmit` 都在 CI 里执行。
