---
name: e2e-test
description: 为前端项目搭建 Playwright E2E 测试（含 istanbul 分支覆盖率与 Playwright MCP），并分析代码中的每个分支自动生成、运行、修复测试用例。用户提到 E2E、Playwright、端到端测试、补测试覆盖率，或调用 /e2e-test 时使用。
argument-hint: "[--all | --route <path> | --file <path> | --uncovered [path] | --setup-only]"
---

# e2e-test

本 skill 同时给 Claude Code 和 Codex 用。模板和脚本都在本 SKILL.md 所在的目录下，下文用 `<skill>/` 表示（Claude Code 加载时会给出 base directory；Codex 的 skill 列表里有 SKILL.md 的路径）。

## 参数

本次参数：`$ARGUMENTS`

（Claude Code 会把上面替换成用户输入的参数。如果你看到的是字面量 `$ARGUMENTS`，说明当前工具不做替换，就从用户调用本 skill 的那条消息里取参数，例如 `$e2e-test --route /sign-in`。）参数是原样文本，按下面的约定理解：

| 参数 | 行为 |
|---|---|
| `--setup-only` | 只做第 1 步（搭环境），不生成测试 |
| `--route <path>` | 只测一个路由，如 `--route /sign-in` |
| `--file <path>` | 找出渲染/调用该文件的所有路由，测这些路由里与该文件相关的分支 |
| `--all` | 扫描全部路由，每个路由生成测试 |
| `--uncovered [path]` | 先跑覆盖率，只为未覆盖的分支补测试；可选 path 前缀过滤（如 `src/lib`） |
| 无参数 | 完成第 1 步后，列出发现的路由和当前覆盖率，问用户要测哪个范围 |

## 第 0 步：识别项目

读 `package.json`、lockfile、构建配置，确定：
- 包管理器：`pnpm-lock.yaml` → pnpm，`yarn.lock` → yarn，`bun.lock*` → bun，否则 npm
- 框架：`vite.config.*` → Vite；`next.config.*` → Next.js；其他照实处理
- 路由定义位置（如 `App.tsx` 里的 `<Routes>`、`app/`/`pages/` 目录）
- 后端/API：找 API base URL、SDK 初始化文件（如 `lib/appwrite/config.ts`、`lib/api.ts`），后面 mock 错误分支要用
- 是否有登录：有 AuthContext / 受保护路由 / sign-in 页面就算有

## 第 1 步：搭环境（幂等，已存在的跳过，只补缺的）

已有 `playwright.config.*` 时，逐项检查下面每一项，缺什么补什么，不要覆盖用户已改过的配置。

1. **安装依赖**（dev）：`@playwright/test`、`nyc`；Vite 项目加 `vite-plugin-istanbul`。Next.js 用 `babel-plugin-istanbul` 或 `swc-plugin-coverage-instrumenter`，按项目实际编译器选。然后 `npx playwright install chromium`。
2. **复制模板**（按框架调整 dev 命令和端口）：
   - `<skill>/templates/playwright.config.ts` → `playwright.config.ts`
   - `<skill>/templates/fixtures.ts` → `e2e/fixtures.ts`
   - `<skill>/templates/nycrc.json` → `.nycrc.json`（`exclude` 里加上项目的纯 UI 库目录，如 shadcn 的 `src/components/ui/**`）
   - 有登录时：`<skill>/templates/auth.setup.ts` → `e2e/auth.setup.ts`，按项目登录页的实际 label/按钮文字改选择器
3. **插桩**（Vite）：在 `vite.config.*` 的 plugins 里加
   ```ts
   istanbul({
     include: 'src/*',
     exclude: ['node_modules', 'e2e/'],
     extension: ['.js', '.jsx', '.ts', '.tsx'],
     requireEnv: true, // 只有 VITE_COVERAGE=true 时才插桩，平时 dev 不受影响
   })
   ```
4. **package.json scripts**：
   ```json
   "test:e2e": "playwright test",
   "test:e2e:ui": "playwright test --ui",
   "test:e2e:coverage": "rm -rf .nyc_output coverage/e2e; VITE_COVERAGE=true playwright test; nyc report"
   ```
5. **.gitignore** 追加：`.nyc_output/`、`coverage/`、`test-results/`、`playwright-report/`、`e2e/.auth/`、`.env.e2e`
6. **测试账号**：有登录时，检查 `.env.e2e` 是否有 `E2E_USER_EMAIL` / `E2E_USER_PASSWORD`。没有就停下来问用户要一个**测试环境**的账号，不要自己注册到生产后端、不要猜。同时生成 `.env.e2e.example`（只有 key，没有值）。
7. **Playwright MCP**：按当前所在的工具配置，已经配过就跳过：
   - Claude Code：项目根 `.mcp.json` 里没有 playwright 条目时，运行
     `claude mcp add playwright --scope project -- npx @playwright/mcp@latest`
   - Codex：`codex mcp list` 里没有 playwright 时，运行
     `codex mcp add playwright -- npx @playwright/mcp@latest`（写入用户级 `~/.codex/config.toml`）

   新加的 MCP 要重启会话才生效：告诉用户这一点，本次会话继续用 `playwright test` 跑测试，不依赖 MCP。
8. **lint 兼容**：项目 ESLint 会扫到 `e2e/` 的话，确认新文件能通过 lint（或在 ESLint 配置里给 `e2e/` 合适的 globals/规则）。
9. 跑一次 `test:e2e`（此时可能只有 auth.setup）确认环境能起来。

## 第 2 步：确定范围

- `--route`：直接用。
- `--file`：从该文件向上追溯 import，找到挂载它的页面组件，再映射到路由。
- `--all`：从路由定义列出全部路由。路由数 > 3 且当前工具支持 subagent 时，**每个路由派一个 subagent 并行处理**第 3–4 步（不支持就按路由逐个顺序处理，每处理完一个就写盘，避免上下文过长），prompt 里带上本 skill 的第 3–4 步规则、项目的测试账号/fixture 约定、负责的路由；各 subagent 只写自己的 `e2e/<route>.spec.ts`。全部完成后由你统一跑第 5 步。
- `--uncovered`：先跑 `test:e2e:coverage`，再运行
  `node <skill>/scripts/uncovered-branches.mjs coverage/e2e/coverage-final.json [path前缀]`，
  拿到未覆盖的分支清单（文件:行号 + 分支类型），按所属路由分组后进入第 3 步，只针对这些分支写测试。

## 第 3 步：分析分支

对范围内的每个路由，读页面组件**以及它用到的**表单、hooks（react-query 等）、校验 schema、API 层、路由守卫、context。列出分支清单，至少检查：

- **条件渲染**：`if`/early return、三元、`&&`、`switch`
- **数据状态**：loading / pending、error、空数据、有数据
- **表单**：schema 里的每一条校验规则各一个失败用例 + 一个全部通过的用例；提交中按钮禁用；提交成功/失败
- **路由守卫**：未登录访问受保护页面、已登录访问登录页的重定向
- **权限/身份**：作者 vs 非作者看到的操作按钮不同
- **API 层**：每个 `catch`、每个 `if (!result) throw` 都是一个错误分支
- **交互**：toast、弹窗、文件上传（`setInputFiles`）、导航跳转

把清单（分支 → 计划的测试名）先简短列给用户看，然后直接开始写，不用等确认。判断为 E2E 无法触达的分支（纯防御性代码、类型守卫）标出来，留到最后报告，不要硬写。

## 第 4 步：写测试

文件：`e2e/<route-name>.spec.ts`（`/` → `home.spec.ts`，`/posts/:id` → `post-details.spec.ts`）。已有文件就追加，不要重写已有测试。

规则：
- **必须** `import { test, expect } from './fixtures'`，不能直接从 `@playwright/test` 导入，否则不收集覆盖率。
- 需要登录的测试 `test.use({ storageState: 'e2e/.auth/user.json' })`；测未登录行为的显式 `test.use({ storageState: { cookies: [], origins: [] } })`。
- 选择器优先级：`getByRole` > `getByLabel` > `getByPlaceholder` > `getByText` > `getByTestId`。都不行时才给源码加 `data-testid`，并在报告里列出改了哪些源码。
- 禁止 `waitForTimeout`；用 web-first 断言（`await expect(locator).toBeVisible()`）。
- 正常流程打真实（测试）后端；**错误分支用 `page.route()` mock** 第 0 步找到的 API URL，返回对应的错误状态码/响应体。mock 的响应格式要照着该 SDK 的真实错误格式写。
- 创建数据用唯一值（`` `e2e-${Date.now()}` ``），能删的在 `afterEach` 里删掉。
- 每个 `test()` 标题写清楚覆盖的分支：`'shows validation error when password is shorter than 8 chars'`。用 `test.describe` 按路由/功能分组。
- 一个页面加载后尽量用页面内点击导航，少用多次 `page.goto`（整页刷新会丢掉之前的覆盖率数据）。

## 第 5 步：运行 → 修复 → 补覆盖

1. `test:e2e` 跑新测试。失败时看错误和 trace，判断是**测试写错**还是**应用有 bug**：
   - 测试写错（选择器、时序、mock 格式）→ 修测试。
   - 应用行为看起来不对（和代码意图、文案、schema 矛盾）→ **不要改断言去迁就**。改成 `test.fixme(...)` 并在上方注释写明预期 vs 实际，最后报告给用户。
   - 同一个测试修 3 次还不过 → 停止，标 `fixme`，写明原因。
2. 全部通过后跑 `test:e2e:coverage` + `uncovered-branches.mjs`（带当前范围的 path 前缀）。
3. 范围内还有可触达但未覆盖的分支 → 回到第 3 步补，最多再循环 2 轮。
4. 跑项目的 lint 和类型检查，确保新文件不引入错误。

## 第 6 步：报告

简短列出：
- 新增/修改的测试文件和测试数量，通过 / fixme 数
- 范围内分支覆盖率：开始前 → 结束后（来自 uncovered-branches 的 summary）
- 怀疑的应用 bug（对应的 fixme 测试）
- 未覆盖且判断为 E2E 无法触达的分支，建议改用单元测试（Vitest + Testing Library）
- 为了测试改动过的源码（如加的 `data-testid`）
- 需要用户做的事（填 `.env.e2e`、重启会话以启用 MCP 等）
