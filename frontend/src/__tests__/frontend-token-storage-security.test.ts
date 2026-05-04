/**
 * 安全加固：前端 localStorage token 存储安全验证测试
 * 覆盖 token 存储键名一致性、token 清理路径完整性、
 * 请求拦截器 token 注入、401 刷新流程、敏感操作安全性
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const ROOT = resolve(import.meta.dirname, '..', '..', '..')

function read(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf-8')
}

const AUTH_STORE = 'frontend/src/stores/auth.ts'
const CLIENT = 'frontend/src/api/client.ts'
const AUTH_API = 'frontend/src/api/auth.ts'

// ═══════════════════════════════════════════════════════════
// 1. token 存储键名一致性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('token 存储键名一致性', () => {
  it('auth store 和 client 使用相同的 access_token 键名', () => {
    const store = read(AUTH_STORE)
    const client = read(CLIENT)
    expect(store).toContain("localStorage.getItem('access_token')")
    expect(client).toContain("localStorage.getItem('access_token')")
    expect(store).toContain("localStorage.setItem('access_token'")
    expect(client).toContain("localStorage.setItem('access_token'")
  })

  it('auth store 和 client 使用相同的 refresh_token 键名', () => {
    const store = read(AUTH_STORE)
    const client = read(CLIENT)
    expect(store).toContain("'refresh_token'")
    expect(client).toContain("'refresh_token'")
  })

  it('仅使用 access_token 和 refresh_token 两个 localStorage 键', () => {
    const store = read(AUTH_STORE)
    const client = read(CLIENT)
    const allSrc = store + client
    const keys = allSrc.match(/localStorage\.\w+\('(\w+)'/g) || []
    const keyNames = new Set(keys.map((k) => k.match(/'(\w+)'/)![1]))
    expect(keyNames).toEqual(new Set(['access_token', 'refresh_token']))
  })

  it('auth store 初始化时从 localStorage 恢复 token', () => {
    const store = read(AUTH_STORE)
    expect(store).toMatch(/token:\s*localStorage\.getItem\('access_token'\)/)
  })

  it('auth API 模块不直接操作 localStorage', () => {
    const api = read(AUTH_API)
    expect(api).not.toContain('localStorage')
  })
})

// ═══════════════════════════════════════════════════════════
// 2. token 清理路径完整性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('token 清理路径完整性', () => {
  it('logout 清除两个 token 并重置状态', () => {
    const store = read(AUTH_STORE)
    const logoutBody = extractFunction(store, 'logout')
    expect(logoutBody).toContain("localStorage.removeItem('access_token')")
    expect(logoutBody).toContain("localStorage.removeItem('refresh_token')")
    expect(logoutBody).toContain('token: null')
    expect(logoutBody).toContain('user: null')
  })

  it('fetchUser 失败时清除 token', () => {
    const store = read(AUTH_STORE)
    const fetchBody = extractFunction(store, 'fetchUser')
    expect(fetchBody).toContain("localStorage.removeItem('access_token')")
    expect(fetchBody).toContain("localStorage.removeItem('refresh_token')")
  })

  it('client 401 刷新失败时清除 token', () => {
    const client = read(CLIENT)
    expect(client).toContain("localStorage.removeItem('access_token')")
    expect(client).toContain("localStorage.removeItem('refresh_token')")
  })

  it('client 刷新失败时重定向到登录页', () => {
    const client = read(CLIENT)
    expect(client).toContain("window.location.href = '/login'")
  })

  it('logout 调用后端 logout 端点', () => {
    const store = read(AUTH_STORE)
    const logoutBody = extractFunction(store, 'logout')
    expect(logoutBody).toContain('authApi.logout()')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 请求拦截器 token 注入验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('请求拦截器 token 注入', () => {
  it('请求拦截器从 localStorage 读取 access_token', () => {
    const client = read(CLIENT)
    expect(client).toContain("localStorage.getItem('access_token')")
  })

  it('请求拦截器设置 Bearer Authorization 头', () => {
    const client = read(CLIENT)
    expect(client).toMatch(/Authorization.*Bearer/)
  })

  it('请求拦截器仅在 token 存在时设置头', () => {
    const client = read(CLIENT)
    expect(client).toContain('if (token)')
  })

  it('请求拦截器添加 X-Request-ID', () => {
    const client = read(CLIENT)
    expect(client).toContain('X-Request-ID')
    expect(client).toContain('crypto.randomUUID()')
  })

  it('apiClient 配置了合理的超时', () => {
    const client = read(CLIENT)
    expect(client).toMatch(/timeout:\s*\d+/)
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 401 刷新流程验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('401 token 刷新流程', () => {
  it('401 时使用 refresh_token 请求新 token', () => {
    const client = read(CLIENT)
    expect(client).toContain('401')
    expect(client).toContain("localStorage.getItem('refresh_token')")
    expect(client).toContain('/auth/refresh')
  })

  it('刷新成功后更新两个 token', () => {
    const client = read(CLIENT)
    const refreshBlock = extractRefreshBlock(client)
    expect(refreshBlock).toContain("localStorage.setItem('access_token'")
    expect(refreshBlock).toContain("localStorage.setItem('refresh_token'")
  })

  it('刷新成功后重试原始请求', () => {
    const client = read(CLIENT)
    const refreshBlock = extractRefreshBlock(client)
    expect(refreshBlock).toMatch(/originalRequest\.headers\.Authorization/)
    expect(refreshBlock).toContain('apiClient(originalRequest)')
  })

  it('使用防重复刷新标记', () => {
    const client = read(CLIENT)
    expect(client).toContain('_retry')
  })

  it('refresh_token 通过 POST body 传递（非 URL 参数）', () => {
    const client = read(CLIENT)
    expect(client).toMatch(/refresh_token.*refreshToken/)
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 敏感操作安全性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('敏感操作安全性', () => {
  it('429 响应有自动重试机制', () => {
    const client = read(CLIENT)
    expect(client).toContain('429')
    expect(client).toContain('_retry429')
  })

  it('429 重试遵守 Retry-After 头部', () => {
    const client = read(CLIENT)
    expect(client).toContain('retry-after')
  })

  it('login 成功后存储完整的 token 对', () => {
    const store = read(AUTH_STORE)
    const loginBody = extractFunction(store, 'login')
    expect(loginBody).toContain("localStorage.setItem('access_token'")
    expect(loginBody).toContain("localStorage.setItem('refresh_token'")
    expect(loginBody).toContain('access_token')
    expect(loginBody).toContain('refresh_token')
  })

  it('login 成功后获取用户信息', () => {
    const store = read(AUTH_STORE)
    const loginBody = extractFunction(store, 'login')
    expect(loginBody).toContain('fetchUser()')
  })

  it('auth store 有 hasPermission 权限检查函数', () => {
    const store = read(AUTH_STORE)
    expect(store).toContain('hasPermission')
    expect(store).toContain('is_superuser')
    expect(store).toContain('permissions.includes')
  })
})

// ═══════════════════════════════════════════════════════════
// 辅助函数
// ═══════════════════════════════════════════════════════════

function extractFunction(source: string, name: string): string {
  // 匹配对象方法: name: async (...) => { ... } 或 name: (...) => { ... }
  const patterns = [
    new RegExp(`${name}:\\s*async\\s*\\([^)]*\\)\\s*=>\\s*\\{`),
    new RegExp(`${name}:\\s*\\([^)]*\\)\\s*=>\\s*\\{`),
    new RegExp(`${name}:\\s*\\(\\)\\s*=>\\s*\\{`),
    new RegExp(`(?:async )?function\\s+${name}\\s*\\(`),
  ]

  for (const pat of patterns) {
    const match = pat.exec(source)
    if (match) {
      const start = match.index
      return extractBlock(source, start)
    }
  }
  return ''
}

function extractBlock(source: string, start: number): string {
  let depth = 0
  let i = source.indexOf('{', start)
  if (i === -1) return ''
  const begin = i
  for (; i < source.length; i++) {
    if (source[i] === '{') depth++
    else if (source[i] === '}') {
      depth--
      if (depth === 0) return source.substring(begin, i + 1)
    }
  }
  return source.substring(begin)
}

function extractRefreshBlock(client: string): string {
  // 提取 401 处理块
  const idx = client.indexOf('401')
  if (idx === -1) return ''
  return extractBlock(client, idx)
}
