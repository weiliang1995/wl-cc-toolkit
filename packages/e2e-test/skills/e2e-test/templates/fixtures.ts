import { randomUUID } from 'node:crypto'
import fs from 'node:fs/promises'
import path from 'node:path'
import { test as base, expect } from '@playwright/test'

const NYC_OUTPUT = path.join(process.cwd(), '.nyc_output')

type CoverageWindow = { __coverage__?: unknown }

// 每个测试结束后把浏览器里 istanbul 收集到的 window.__coverage__ 写到 .nyc_output，
// 再由 `nyc report` 合并成报告。只在 VITE_COVERAGE=true 时生效。
export const test = base.extend<{ collectCoverage: void }>({
  collectCoverage: [
    async ({ page }, use) => {
      await use()
      if (process.env.VITE_COVERAGE !== 'true') return

      const coverage = await page
        .evaluate(() => (window as unknown as CoverageWindow).__coverage__)
        .catch(() => undefined)
      if (!coverage) return

      await fs.mkdir(NYC_OUTPUT, { recursive: true })
      await fs.writeFile(path.join(NYC_OUTPUT, `${randomUUID()}.json`), JSON.stringify(coverage))
    },
    { auto: true },
  ],
})

export { expect }
