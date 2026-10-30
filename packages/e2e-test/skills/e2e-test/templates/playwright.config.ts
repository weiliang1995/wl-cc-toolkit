import { defineConfig, devices } from '@playwright/test'

// Playwright 不会自动读 .env，这里加载测试账号等变量（Node >= 20.12）
try {
  process.loadEnvFile('.env.e2e')
} catch {
  // .env.e2e 不存在时忽略，CI 里直接用环境变量
}

// 用独立端口，避免和平时开着的 dev server 冲突
const PORT = Number(process.env.E2E_PORT ?? 5199)
const BASE_URL = `http://localhost:${PORT}`
const COVERAGE = process.env.VITE_COVERAGE === 'true'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
  ],
  webServer: {
    // 按框架/包管理器调整，例如 Next.js: `pnpm next dev -p ${PORT}`
    command: `pnpm dev --port ${PORT} --strictPort`,
    url: BASE_URL,
    // 覆盖率模式必须用插桩过的新 server，不能复用
    reuseExistingServer: !process.env.CI && !COVERAGE,
    timeout: 120_000,
  },
})
