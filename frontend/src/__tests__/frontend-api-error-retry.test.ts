/**
 * 可观测性：前端 API 错误处理与重试逻辑验证测试
 * 覆盖 client 拦截器逻辑、统一错误提示覆盖、
 * request.ts 辅助函数、usePaginatedList 错误处理、useSubmit 防重复提交
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const ROOT = resolve(import.meta.dirname, '..', '..', '..')

function read(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf-8')
}

const CLIENT = 'frontend/src/api/client.ts'
const REQUEST = 'frontend/src/api/request.ts'
const USE_SUBMIT = 'frontend/src/hooks/useSubmit.ts'
const USE_PAGINATED = 'frontend/src/hooks/usePaginatedList.ts'

// ═══════════════════════════════════════════════════════════
// 1. client 拦截器逻辑验证（6 项）
// ═══════════════════════════════════════════════════════════

describe('client 拦截器逻辑', () => {
  it('apiClient 配置 baseURL 使用环境变量回退', () => {
    const client = read(CLIENT)
    expect(client).toContain('VITE_API_BASE_URL')
    expect(client).toContain('http://localhost:8000/api/v1')
  })

  it('apiClient 配置 15 秒超时', () => {
    const client = read(CLIENT)
    expect(client).toContain('timeout: 15000')
  })

  it('请求拦截器设置 Bearer token 和 X-Request-ID', () => {
    const client = read(CLIENT)
    expect(client).toContain('interceptors.request.use')
    expect(client).toContain('Bearer')
    expect(client).toContain('X-Request-ID')
    expect(client).toContain('crypto.randomUUID()')
  })

  it('429 响应自动重试一次且有上限等待', () => {
    const client = read(CLIENT)
    expect(client).toContain('429')
    expect(client).toContain('_retry429')
    expect(client).toContain('retry-after')
    expect(client).toContain('Math.min(retryAfter, 5000)')
  })

  it('401 响应使用 refresh_token 刷新后重试原始请求', () => {
    const client = read(CLIENT)
    expect(client).toContain('401')
    expect(client).toContain('_retry')
    expect(client).toContain('/auth/refresh')
    expect(client).toContain('refresh_token')
    expect(client).toContain('apiClient(originalRequest)')
  })

  it('401 刷新失败时清除 token 并重定向登录页', () => {
    const client = read(CLIENT)
    expect(client).toContain("window.location.href = '/login'")
    expect(client).toContain("localStorage.removeItem('access_token')")
    expect(client).toContain("localStorage.removeItem('refresh_token')")
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 统一错误提示覆盖验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('统一错误提示覆盖', () => {
  it('429 返回「请求过于频繁」提示', () => {
    const client = read(CLIENT)
    expect(client).toMatch(/429[\s\S]*请求过于频繁/)
  })

  it('403 返回「没有操作权限」提示', () => {
    const client = read(CLIENT)
    expect(client).toMatch(/403[\s\S]*没有操作权限/)
  })

  it('404 返回「请求的资源不存在」提示', () => {
    const client = read(CLIENT)
    expect(client).toMatch(/404[\s\S]*请求的资源不存在/)
  })

  it('500 返回「服务器错误」提示', () => {
    const client = read(CLIENT)
    expect(client).toMatch(/500[\s\S]*服务器错误/)
  })

  it('网络断开返回「网络连接失败」提示', () => {
    const client = read(CLIENT)
    expect(client).toContain('网络连接失败')
    expect(client).toContain('!error.response')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. request.ts 辅助函数验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('request.ts 辅助函数', () => {
  it('导出 get/post/put/del/upload/downloadCsv 六个函数', () => {
    const req = read(REQUEST)
    expect(req).toContain('export async function get')
    expect(req).toContain('export async function post')
    expect(req).toContain('export async function put')
    expect(req).toContain('export async function del')
    expect(req).toContain('export async function upload')
    expect(req).toContain('export async function downloadCsv')
  })

  it('所有请求函数使用泛型 T 返回 ApiResponse<T>', () => {
    const req = read(REQUEST)
    expect(req).toContain('ApiResponse<T>')
  })

  it('upload 函数设置 multipart/form-data Content-Type', () => {
    const req = read(REQUEST)
    const uploadBody = extractFunction(req, 'upload')
    expect(uploadBody).toContain('multipart/form-data')
    expect(uploadBody).toContain('FormData')
  })

  it('downloadCsv 使用 responseType: blob', () => {
    const req = read(REQUEST)
    expect(req).toContain("responseType: 'blob'")
  })

  it('downloadCsv 处理 JSON 错误响应', () => {
    const req = read(REQUEST)
    expect(req).toContain('application/json')
    expect(req).toContain('error?.message')
  })
})

// ═══════════════════════════════════════════════════════════
// 4. usePaginatedList 错误处理验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('usePaginatedList 错误处理', () => {
  it('请求失败时设置 error 为 true', () => {
    const hook = read(USE_PAGINATED)
    expect(hook).toContain('setError(true)')
  })

  it('请求成功时清除 error 状态', () => {
    const hook = read(USE_PAGINATED)
    expect(hook).toContain('setError(false)')
  })

  it('请求开始时设置 loading 为 true', () => {
    const hook = read(USE_PAGINATED)
    expect(hook).toContain('setLoading(true)')
  })

  it('请求结束后设置 loading 为 false', () => {
    const hook = read(USE_PAGINATED)
    expect(hook).toContain('setLoading(false)')
  })

  it('返回 data, total, loading, error, refresh 等状态', () => {
    const hook = read(USE_PAGINATED)
    expect(hook).toMatch(/return\s*\{/)
    expect(hook).toContain('data,')
    expect(hook).toContain('total,')
    expect(hook).toContain('loading,')
    expect(hook).toContain('error,')
    expect(hook).toContain('refresh:')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. useSubmit 防重复提交验证（4 项）
// ═══════════════════════════════════════════════════════════

describe('useSubmit 防重复提交', () => {
  it('使用 locked ref 防止并发提交', () => {
    const submit = read(USE_SUBMIT)
    expect(submit).toContain('locked')
    expect(submit).toContain('useRef(false)')
    expect(submit).toContain('if (locked.current) return')
  })

  it('提交前锁定、完成后（finally）解锁', () => {
    const submit = read(USE_SUBMIT)
    expect(submit).toContain('locked.current = true')
    expect(submit).toContain('locked.current = false')
  })

  it('跳过 Ant Design 表单校验错误', () => {
    const submit = read(USE_SUBMIT)
    expect(submit).toContain('errorFields')
  })

  it('跳过拦截器已展示的 toast（避免重复提示）', () => {
    const submit = read(USE_SUBMIT)
    expect(submit).toContain('isToastDisplayed')
  })
})

// ═══════════════════════════════════════════════════════════
// 辅助函数
// ═══════════════════════════════════════════════════════════

function extractFunction(source: string, name: string): string {
  const patterns = [
    new RegExp(`export\\s+async\\s+function\\s+${name}\\s*<[^>]*>\\s*\\([^)]*\\)\\s*:\\s*\\w+`),
    new RegExp(`export\\s+async\\s+function\\s+${name}\\s*\\([^)]*\\)\\s*:\\s*\\w+`),
    new RegExp(`export\\s+async\\s+function\\s+${name}\\s*<[^>]*>\\s*\\(`),
    new RegExp(`export\\s+async\\s+function\\s+${name}\\s*\\(`),
    new RegExp(`(?:async )?function\\s+${name}\\s*\\(`),
  ]
  for (const pat of patterns) {
    const match = pat.exec(source)
    if (match) {
      return extractBlock(source, match.index)
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
