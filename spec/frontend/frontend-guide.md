---
version: 3.0.0
last_updated: 2026-11-15
---

# Next.js 前端编写指南（Next.js Frontend Guide）

本指南规定**前端代码如何落地**：目录怎么分、什么代码放哪里、Server / Client 边界怎么划、数据在哪里取、类型从哪来、组件与状态怎么组织。

不涉及的内容：

- 后端模块结构——见 `spec/module/module-guide.md`。
- 接口实现与数据库——分别见后端模块指南与 `spec/alembic/alembic-guide.md`。
- 格式与 lint 细节——由 Prettier + ESLint 强制，本指南只规定它们管不到的结构性问题。

## 版本管理

本规范采用大版本管理方式：

- 初始版本为 `1.0.0`。
- 每次内容变更时，只递增第一个版本号。
- 版本号格式固定为 `主版本号.0.0`。
- 例如：`1.0.0` → `2.0.0` → `3.0.0`。
- 不使用 `1.1.0`、`1.0.1` 等小版本或补丁版本。
- 每次版本更新必须同步更新 `last_updated`。

## 0. 总纲

**默认服务端渲染、默认在服务端取数、`app/` 只做路由与装配。**

三个默认值构成判断基准，只有明确需要交互或浏览器 API 时才打破：

- SHOULD 新组件默认不写 `'use client'`，等确认需要状态、事件、副作用再加。
- SHOULD 新页面的数据在 Server Component 里取，不在客户端 `useEffect` 里取。
- MUST NOT 在 `app/` 下的页面文件里写业务逻辑；页面只负责取数与拼装组件。

---

## 1. 目录结构

```text
frontend/
├── src/
│   ├── app/                    # 只负责路由：页面、布局、loading、error、route handler
│   │   ├── (marketing)/        # 路由组，不影响 URL
│   │   ├── dashboard/
│   │   │   ├── page.tsx
│   │   │   ├── loading.tsx
│   │   │   └── error.tsx
│   │   └── api/                # 需要对外暴露的 Route Handler
│   ├── features/               # 业务模块，一个业务一个目录
│   │   └── <feature>/
│   │       ├── components/     # 该业务专属组件
│   │       ├── api/            # 该业务的请求函数（*.server.ts 只能在服务端引用）
│   │       ├── hooks/          # 该业务的 hooks
│   │       ├── types.ts        # 该业务的 DTO 与视图类型
│   │       ├── utils.ts        # 该业务的纯函数
│   │       └── index.ts        # 唯一公开出口
│   ├── components/
│   │   ├── ui/                 # 无业务的原子组件（按钮、输入框、表格壳）
│   │   └── layout/             # 页头、侧栏、容器等骨架
│   ├── hooks/                  # 跨业务通用 hooks
│   ├── lib/                    # 第三方封装、env、fetch 客户端、格式化
│   ├── stores/                 # 仅客户端全局状态
│   ├── types/                  # 全局类型
│   └── constants/              # 常量与枚举
├── public/
└── package.json
```

要求：

- MUST 业务代码放在 `features/<feature>/`，不允许在 `app/` 下积累业务实现。
- MUST `components/ui/` 只放无业务语义的组件；出现业务名词（订单、用户、账单）说明它属于某个 feature。
- MUST 每个 feature 只通过自己的 `index.ts` 对外暴露；其他 feature 不得深入其内部路径。
- MUST NOT 建空目录占位；目录在第一次有文件时才创建。
- SHOULD 单个组件文件不超过 200 行，超过就拆。

---

## 2. `app/` 的写法

### 2.1 页面文件只做装配

```tsx
// ✔ 推荐：app/dashboard/page.tsx
import { listOrders } from "@/features/order";
import { OrderTable } from "@/features/order";

export default async function DashboardPage() {
  const orders = await listOrders();
  return <OrderTable orders={orders} />;
}
```

```tsx
// ✗ 不推荐：页面里直接拼请求、写格式化、写分支业务
export default async function DashboardPage() {
  const res = await fetch(`${process.env.API_URL}/orders`);
  const data = await res.json();
  return <div>{data.map((o: any) => <div>{o.status === 1 ? "已付" : "未付"}</div>)}</div>;
}
```

页面文件的职责上限：取数、拼装组件、设置 metadata。超过这个范围就下沉到 feature。

### 2.2 约定文件按需添加

| 文件 | 何时添加 |
| --- | --- |
| `page.tsx` | 一定有 |
| `layout.tsx` | 该段路由需要共享外壳时 |
| `loading.tsx` | 该段有可感知的等待时 |
| `error.tsx` | 该段需要兜底错误 UI 时（必须是客户端组件） |
| `not-found.tsx` | 该段有 404 业务语义时 |
| `route.ts` | 需要以 HTTP 形式对外暴露接口时 |

### 2.3 版本相关写法（Next.js 15+）

- MUST `params`、`searchParams` 按 Promise 处理：`const { id } = await params;`
- MUST `cookies()`、`headers()` 按异步处理：`const token = (await cookies()).get("token")`
- MUST NOT 使用已废弃的同步写法，出现即视为该页面未适配当前版本。
- SHOULD 中间件文件按当前大版本命名（Next.js 16 起 `middleware.ts` 已更名为 `proxy.ts`），落盘前确认项目 Next 版本，不凭记忆写。

---

## 3. Server / Client 边界

### 3.1 判定顺序

1. 需要 `useState` / `useEffect` / 事件处理 / 浏览器 API（`window`、`localStorage`）→ 客户端组件。
2. 需要读取密钥、直连后端内部地址、访问数据库 → 必须服务端组件或服务端函数。
3. 其余一律服务端组件。

### 3.2 边界要往下压

`'use client'` 加在**叶子**组件上，不要加在页面或整块布局上。

```tsx
// ✔ 推荐：只有搜索框是客户端组件，列表仍是服务端渲染
export default async function OrdersPage() {
  const orders = await listOrders();
  return (
    <>
      <OrderSearch />        {/* 'use client' 在这里面 */}
      <OrderTable orders={orders} />
    </>
  );
}
```

```tsx
// ✗ 不推荐：整页变成客户端组件，取数退化到 useEffect
"use client";
export default function OrdersPage() { /* ... */ }
```

### 3.3 硬性约束

- MUST NOT 从客户端组件 import 标了 `server-only` 的模块、读取非 `NEXT_PUBLIC_` 的环境变量。
- MUST 传给客户端组件的 props 可被序列化：不传函数、类实例、`Date` 以外的自定义对象原始形态。
- MUST 客户端组件不直接暴露后端管理接口地址；所有请求经 `features/*/api/` 的函数，由服务端代理或由公开接口承担。
- SHOULD 客户端组件的文件首行就是 `"use client";`，不留空行、不写注释在前。

---

## 4. 数据获取

### 4.1 位置

| 场景 | 位置 |
| --- | --- |
| 页面首屏数据 | Server Component 里 `await` 调用 `features/<f>/api/*.server.ts` |
| 交互后的刷新 / 分页 | 客户端组件调用 `features/<f>/api/*.client.ts`（走公开接口） |
| 表单提交等变更 | Server Action（`"use server"`）或 `app/api/**/route.ts`，一个业务只选一种 |
| 全局配置、常量 | `lib/`，不在组件内直接读 `process.env` |

### 4.2 请求函数形态

一个接口一个函数，集中在 `features/<f>/api/`：

```ts
// ✔ 推荐：features/order/api/list-orders.server.ts
import "server-only";
import { apiFetch } from "@/lib/api-fetch";
import type { Order } from "../types";

export async function listOrders(): Promise<Order[]> {
  return apiFetch<Order[]>("/orders", { cache: "no-store" });
}
```

```ts
// ✗ 不推荐：组件里裸 fetch，URL 散落，错误与鉴权各自为政
const res = await fetch("http://192.168.1.10:8000/api/v1/orders");
```

要求：

- MUST URL 拼接只出现在 `lib/api-fetch.ts`，业务代码只传相对路径。
- MUST 缓存策略显式写出（`no-store`、`revalidate: N`），不依赖默认值。
- MUST NOT 在组件内串联多个 `await` 造成瀑布；能并行的用 `Promise.all`，必须串行处写一行注释说明原因。
- SHOULD 请求函数返回领域对象，不返回 `Response`。

### 4.3 环境变量

- `lib/env.ts` 统一读取并校验：缺失或格式不对时立刻抛错，禁止用 `undefined` 静默降级。
- 服务端专用变量（后端内部地址、密钥）不得加 `NEXT_PUBLIC_` 前缀。

---

## 5. 类型与接口契约

- MUST 后端 FastAPI 是接口的唯一事实源；前端类型与后端 schema 一一对应，字段名不自行改写。
- MUST 每个 feature 的 DTO 类型集中在 `features/<f>/types.ts`，不散落在组件里。
- MUST NOT 出现 `any`；外部数据先按 `unknown` 接收，用 zod（或等价方案）在边界解析后再进入业务。
- MUST 区分三种类型：DTO（后端返回）、ViewModel（组件需要的形状）、FormValues（表单输入），不混用一个类型贯穿到底。
- SHOULD 接口变更时同步改 `types.ts`，不允许前端靠可选字段"兼容"后端改动。

---

## 6. 组件与命名

### 6.1 命名

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| 组件文件 | `kebab-case.tsx` | `order-table.tsx` |
| 组件导出 | `PascalCase` | `export function OrderTable()` |
| hooks 文件 | `use-*.ts` | `use-order-filter.ts` |
| 工具函数文件 | `kebab-case.ts` | `format-currency.ts` |
| 服务端专用文件 | `*.server.ts` | `list-orders.server.ts` |
| 客户端请求文件 | `*.client.ts` | `create-order.client.ts` |
| 类型文件 | `types.ts` | — |
| 常量 | `UPPER_SNAKE_CASE` | `ORDER_STATUS_LABEL` |

### 6.2 组件的边界

- MUST `components/ui/` 的组件不带业务语义、不发请求、不读全局 store。
- MUST 可复用组件接收数据与回调，不自己取数；取数属于页面或 feature。
- MUST props 用 `type Props = { ... }` 定义，不用 `interface`，不用 `React.FC`。
- SHOULD 超过 4 个 boolean prop 说明该拆成组合组件，而不是继续堆开关。

### 6.3 导入规则

- MUST 使用路径别名 `@/*`；禁止 `../../../` 这类跨三层以上的相对路径。
- MUST NOT 使用 barrel 文件（`index.ts` 批量重导出）作为常规导入方式；`features/<f>/index.ts` 是唯一例外，且只导出该 feature 的公开 API。
- SHOULD 导入顺序：`react` / `next` → 第三方 → `@/` 绝对路径 → 同目录相对路径。

---

## 7. 状态管理

- MUST 服务端获取的数据不进全局 store；需要跨组件共享时优先放 URL（`searchParams`）或服务端 props。
- MUST 仅在确需跨页面共享的客户端状态才用 `stores/`（如主题、侧栏开合、多步表单草稿）。
- MUST NOT 用 store 代替路由参数表达"当前选中的详情"。
- SHOULD 单个 store 一个文件，只暴露必要的 action，不暴露内部 state setter。

---

## 8. 样式与 UI 组件

技术栈固定为 **Tailwind CSS + shadcn/ui**，两者版本以项目 `components.json` 与 `package.json` 为准。**不自行搭建组件库，不手写样式系统。**

### 8.1 组件来源

- MUST 需要任何 UI 组件（按钮、输入、表格、弹窗、下拉、日期选择）时，先 `npx shadcn@latest search` 或 `npx shadcn@latest add <component>`，不要自己写。
- MUST `components/ui/` 只放 shadcn 生成或基于其原语组合的组件，且只保留一个来源。
- MUST NOT 引入第二套 UI 库（Ant Design、MUI、Chakra 等），不混用图标库（统一 `lucide-react`）。
- MUST 优先用组件自带变体（`variant="outline"`、`size="sm"`），而不是覆盖样式实现同样效果。
- SHOULD 页面由现成组件组合而成：设置页 = `Tabs` + `Card` + 表单控件；列表页 = `Table` + `Pagination`。

**注意：shadcn 生成的 `components/ui/*` 是本项目源码，不是依赖。** 升级只能通过 CLI 重新生成并逐个人工比对 diff，不靠改 `package.json` 版本。其余依赖（版本范围、`dependencies` / `devDependencies` 分组、React 与 Next 版本对齐、`ignore-scripts`、体积预算）按 `spec/dependency/dependency-guide.md` 执行。

### 8.2 Tailwind 用法

- MUST 使用语义色 token：`bg-background`、`text-muted-foreground`、`border-border`；**禁止 `bg-blue-500`、`text-gray-600` 这类原始色值**。
- MUST NOT 手动写 `dark:` 颜色覆盖；深浅色由语义 token 自动跟随。
- MUST `className` 只表达布局与间距，不改组件颜色与字体；改外观应改主题变量或组件变体。
- MUST 用 `flex` + `gap-*`，禁止 `space-x-*` / `space-y-*`。
- MUST 宽高相等时用 `size-*`；文本截断用 `truncate`。
- MUST 条件类名用 `cn()`，禁止模板字符串拼接三元表达式。
- MUST NOT 在组件里写内联 `style={{}}`。
- SHOULD 设计变量（颜色、圆角、字号）只改 `globals.css` 的 `@theme`，不改组件。
- SHOULD 复杂类名组合抽成组件变体（`cva`），不在 JSX 里堆条件字符串。
- MUST NOT 一次性样式写全局 CSS 文件；Tailwind 表达不了的个别场景才允许 CSS Modules。

### 8.3 表单与交互

- MUST 表单用 shadcn 的字段组合（`FieldGroup`），不手搭 label + input + 错误提示三件套。
- MUST 一组互斥选项用 `ToggleGroup` / `RadioGroup`，不用一排按钮伪装。
- MUST 加载、空态、错误三态都有对应组件（`Skeleton`、空态提示、`Alert`），不允许只写正常态。
- SHOULD 危险操作（删除、重置）用 `AlertDialog` 二次确认。

---

## 9. 前端与后端的衔接

- MUST 后端接口版本前缀（如 `/api/v1`）写在 `lib/api-fetch.ts`，业务代码不重复拼。
- MUST 错误码到用户文案的映射集中在 `features/<f>/errors.ts`，不在组件里散写提示语。
- SHOULD 后端返回的统一错误结构被 `api-fetch` 解析成异常类型，业务层只 catch 语义化异常。
- SHOULD 新增接口时，先确认后端 schema，再写前端类型，最后写请求函数，顺序不颠倒。

---

## 10. 提交前检查清单

- [ ] 业务代码在 `features/`，`app/` 只做路由与装配。
- [ ] `'use client'` 只出现在叶子组件，页面文件没有全页客户端化。
- [ ] 数据在服务端取；没有 `useEffect` 里取首屏数据。
- [ ] 请求函数集中在 `features/*/api/`，URL 拼接只在 `lib/api-fetch.ts`。
- [ ] 缓存策略显式，没有依赖默认值。
- [ ] 没有 `any`；外部数据经边界解析。
- [ ] 类型与后端 schema 一致，DTO / ViewModel / FormValues 已区分。
- [ ] 跨 feature 只 import 其 `index.ts`。
- [ ] 没有 `../../../` 深层相对路径，没有常规 barrel 导入。
- [ ] 服务端密钥没有进客户端组件，`NEXT_PUBLIC_` 只用于确实公开的值。
- [ ] 命名符合第 6 章表格。
- [ ] 新增 UI 组件来自 shadcn CLI，`components/ui/` 里没有手写替代品。
- [ ] 颜色全部是语义 token，没有 `bg-blue-500` 这类原始色，没有手动 `dark:` 覆盖。
- [ ] 布局用 `gap-*`，条件类名用 `cn()`，没有内联 `style`。
- [ ] 表单有字段组合与错误提示，列表有空态，请求有加载态，失败有错误态。
- [ ] 没有引入第二套 UI 库或图标库。

---

## 11. 落地时需要注意的三件事

1. **`next dev` 可能自动生成 `AGENTS.md`**：Next.js 16.3+ 会在应用目录写入 `AGENTS.md` 与内置文档。前端应用落地后若出现 `frontend/AGENTS.md`，必须与仓库根 `AGENTS.md` 合并或改为引用，不允许两份约定并存（与"不新增 `CLAUDE.md`"同理）。
2. **官方已不再提供 Next.js 目录规范 skill**：`next-best-practices` 已下线，路由与目录约定的权威来源是本文件与项目内的 `AGENTS.md`，不要依赖外部 skill 兜底。
3. **shadcn/ui 官方 skill 已安装**（`.agents/skills/shadcn`），前端应用出现 `components.json` 后自动生效，提供组件搜索、CLI 用法、主题变量、组合规则。注意分工：skill 提供"怎么写对 shadcn 组件"的能力，本文件提供"这个项目允许写什么"的约束；冲突时以本文件为准。

---

## 12. 底线

1. 服务端优先：能不写 `'use client'` 就不写。
2. 取数在服务端，拼装在页面，业务在 feature。
3. 类型跟着后端走，不按前端方便改字段。
4. 一个 feature 一个公开出口，其余路径对外不可见。
5. 组件能用现成的就用现成的，手写 UI 必须有理由。
6. 结构问题写进本指南，写法问题交给 lint，不靠口头约定。
