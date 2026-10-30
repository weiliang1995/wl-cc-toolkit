import { expect, test as setup } from '@playwright/test'

const AUTH_FILE = 'e2e/.auth/user.json'

// 用测试账号登录一次，保存 storageState，供需要登录的测试复用。
// 选择器和路由按项目实际的登录页调整。
setup('authenticate', async ({ page }) => {
  const email = process.env.E2E_USER_EMAIL
  const password = process.env.E2E_USER_PASSWORD
  if (!email || !password) {
    throw new Error('Missing E2E_USER_EMAIL / E2E_USER_PASSWORD in .env.e2e')
  }

  await page.goto('/sign-in')
  await page.getByLabel(/email/i).fill(email)
  await page.getByLabel(/password/i).fill(password)
  await page.getByRole('button', { name: /sign in|log in/i }).click()

  // 登录成功的判断条件：离开登录页
  await expect(page).not.toHaveURL(/sign-in/)

  await page.context().storageState({ path: AUTH_FILE })
})
