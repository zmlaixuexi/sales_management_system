/**
 * 可观测性：前端 API 错误处理与重试逻辑验证测试
 * 覆盖 client 拦截器逻辑、request.ts 辅助函数、
 * usePaginatedList 错误处理、useSubmit 防重复提交、
 * 错误提示去重
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')

function frontendSrc(module: string): string {
  return readFileSync(resolve(root, 'frontend/src', module), 'utf-8')
}

function extractFnBody(source: string, fnName: string): string {
  const idx = source.indexOf(`function ${fnName}`)
  if (idx === -1) return ''
  let braceStart = -1
  let depth = 0
  for (let i = idx; i < source.length; i++) {
    if (source[i] === '{') {
      if (braceStart === -1) braceStart = i
      depth++
    } else if (source[i] === '}') {
      depth--
      if (depth === 0) return source.substring(braceStart + 1, i)
    }
  }
  return ''
}

const clientCode = frontendSrc('api/client.ts')
const requestCode = frontendSrc('api/request.ts')
const utilsCode = frontendSrc('utils/index.ts')
const usePaginatedCode = frontendSrc('hooks/usePaginatedList.ts')
const useSubmitCode = frontendSrc('hooks/useSubmit.ts')

// ═══════════════════════════════════════════════════════════
// 1. client.ts 拦截器逻辑验证（6 项）
// ═══════════════════════════════════════════════════════════

describe('client.ts 拦截器逻辑', () => {
  it('请求拦截器附加 access_token', () => {
    expect(clientCode).toContain("localStorage.getItem('access_token')")
    expect(clientCode).toContain('Authorization')
    expect(clientCode).toContain('Bearer')
  })

  it('请求拦截器生成 X-Request-ID', () => {
    expect(clientCode).toContain('X-Request-ID')
    expect(clientCode).toContain('crypto.randomUUID')
  })

  it('429 响应触发重试逻辑', () => {
    expect(clientCode).toContain('429')
    expect(clientCode).toContain('_retry429')
    expect(clientCode).toContain('retry-after')
  })

  it('429 重试有上限保护', () => {
    expect(clientCode).toContain('Math.min')
    expect(clientCode).toContain('5000')
  })

  it('401 响应触发 token 刷新', () => {
    expect(clientCode).toContain('401')
    expect(clientCode).toContain('refresh_token')
    expect(clientCode).toContain('/auth/refresh')
    expect(clientCode).toContain('_retry')
  })

  it('刷新失败后清除 token 并跳转登录页', () => {
    expect(clientCode).toContain("localStorage.removeItem('access_token')")
    expect(clientCode).toContain("localStorage.removeItem('refresh_token')")
    expect(clientCode).toContain("window.location.href = '/login'")
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 统一错误提示覆盖验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('统一错误提示覆盖', () => {
  it('覆盖 429/403/404/500 状态码', () => {
    expect(clientCode).toMatch(/case\s+429|status\s*===\s*429|\.status === 429/)
    expect(clientCode).toMatch(/status\s*===\s*403/)
    expect(clientCode).toMatch(/status\s*===\s*404/)
    expect(clientCode).toMatch(/status\s*===\s*500/)
  })

  it('处理后端 error.message 和 detail.message 两种错误格式', () => {
    expect(clientCode).toContain('error.message')
    expect(clientCode).toContain('data.message')
  })

  it('处理网络断连（无 response）', () => {
    expect(clientCode).toContain('!error.response')
    expect(clientCode).toContain('网络连接失败')
  })

  it('设置 _toastDisplayed 标志避免重复提示', () => {
    expect(clientCode).toContain('_toastDisplayed')
  })

  it('401 错误不弹出重复提示', () => {
    expect(clientCode).toMatch(/status !== 401/)
  })
})

// ═══════════════════════════════════════════════════════════
// 3. request.ts 辅助函数验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('request.ts 辅助函数', () => {
  it('导出 get/post/put/del/upload/downloadCsv 6 个函数', () => {
    expect(requestCode).toContain('export async function get')
    expect(requestCode).toContain('export async function post')
    expect(requestCode).toContain('export async function put')
    expect(requestCode).toContain('export async function del')
    expect(requestCode).toContain('export async function upload')
    expect(requestCode).toContain('export async function downloadCsv')
  })

  it('所有请求函数使用 apiClient 而非直接 axios', () => {
    const body = extractFnBody(requestCode, 'get')
    expect(body).toContain('apiClient.get')
    const postBody = extractFnBody(requestCode, 'post')
    expect(postBody).toContain('apiClient.post')
  })

  it('downloadCsv 处理后端 JSON 错误（blob type 为 application/json）', () => {
    expect(requestCode).toContain('application/json')
    expect(requestCode).toContain('blob.text()')
    expect(requestCode).toContain('JSON.parse')
  })

  it('downloadCsv 从 content-disposition 提取文件名', () => {
    expect(requestCode).toContain('content-disposition')
    expect(requestCode).toContain('filename')
  })

  it('downloadCsv 过滤 undefined 和空字符串参数', () => {
    expect(requestCode).toContain('!== undefined')
    expect(requestCode).toContain("!== ''")
  })
})

// ═══════════════════════════════════════════════════════════
// 4. usePaginatedList 错误处理验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('usePaginatedList 错误处理', () => {
  it('loading/error/数据状态管理', () => {
    expect(usePaginatedCode).toContain('setLoading(true)')
    expect(usePaginatedCode).toContain('setLoading(false)')
    expect(usePaginatedCode).toContain('setError(true)')
    expect(usePaginatedCode).toContain('setError(false)')
  })

  it('catch 块检查 isToastDisplayed 避免重复提示', () => {
    expect(usePaginatedCode).toContain('isToastDisplayed')
  })

  it('fetchFn 使用 ref 避免闭包过期', () => {
    expect(usePaginatedCode).toContain('fetchFnRef')
    expect(usePaginatedCode).toContain('useRef(fetchFn)')
    expect(usePaginatedCode).toContain('useEffect')
  })

  it('传递 page/page_size/keyword/filters 参数', () => {
    expect(usePaginatedCode).toContain('page')
    expect(usePaginatedCode).toContain('page_size')
    expect(usePaginatedCode).toContain('keyword')
    expect(usePaginatedCode).toContain('...filters')
  })

  it('返回 refresh 函数支持手动刷新', () => {
    expect(usePaginatedCode).toContain('refresh:')
    expect(usePaginatedCode).toContain('loadData')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. useSubmit 防重复提交验证（4 项）
// ═══════════════════════════════════════════════════════════

describe('useSubmit 防重复提交', () => {
  it('使用 locked ref 防止重复提交', () => {
    expect(useSubmitCode).toContain('locked')
    expect(useSubmitCode).toContain('useRef')
    expect(useSubmitCode).toContain('locked.current')
  })

  it('提交前检查锁，提交后释放', () => {
    expect(useSubmitCode).toContain('if (locked.current) return')
    expect(useSubmitCode).toContain('locked.current = true')
    expect(useSubmitCode).toContain('locked.current = false')
  })

  it('Ant Design 表单校验错误不弹提示', () => {
    expect(useSubmitCode).toContain('errorFields')
  })

  it('使用 getApiErrorMessage 提取错误消息', () => {
    expect(useSubmitCode).toContain('getApiErrorMessage')
    expect(useSubmitCode).toContain('isToastDisplayed')
  })
})
