/**
 * 代码质量：真实 apiClient 拦截器边界测试
 * 覆盖错误优先级链、请求拦截器边界、配置常量、429 Retry-After 边界、
 * _toastDisplayed 标记设置
 *
 * 注意：此文件 mock antd 但使用真实 apiClient
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// mock antd message（必须在 import apiClient 之前）
vi.mock('antd', () => ({
  message: { error: vi.fn() },
}))

vi.spyOn(axios, 'post')

import apiClient from '@/api/client'
import { message } from 'antd'

const mockMsgError = vi.mocked(message.error)
const mockAxiosPost = vi.mocked(axios.post)

// ═══════════════════════════════════════════════════════
// 1. apiClient 配置常量边界
// ═══════════════════════════════════════════════════════

describe('apiClient 配置常量', () => {
  it('timeout 为 15000ms', () => {
    expect(apiClient.defaults.timeout).toBe(15000)
  })

  it('baseURL 包含 /api/v1', () => {
    expect(apiClient.defaults.baseURL).toContain('/api/v1')
  })

  it('有一个请求拦截器', () => {
    expect(apiClient.interceptors.request.handlers.length).toBeGreaterThanOrEqual(1)
  })

  it('有一个响应拦截器', () => {
    expect(apiClient.interceptors.response.handlers.length).toBeGreaterThanOrEqual(1)
  })

  it('Content-Type 默认为 application/json', () => {
    const contentType =
      apiClient.defaults.headers.common['Content-Type'] ||
      apiClient.defaults.headers['Content-Type']
    expect(contentType).toBeDefined()
    expect(String(contentType)).toContain('application/json')
  })
})

// ═══════════════════════════════════════════════════════
// 2. 请求拦截器边界
// ═══════════════════════════════════════════════════════

describe('请求拦截器边界', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('已有 Authorization 头时被覆盖为新 token', () => {
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    localStorage.setItem('access_token', 'new-token')
    const config = { headers: { Authorization: 'Bearer old-token' } }
    const result = handler(config as never)
    expect(result.headers.Authorization).toBe('Bearer new-token')
  })

  it('X-Request-ID 为标准 UUID v4 格式（小写十六进制）', () => {
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    const config = { headers: {} }
    const result = handler(config as never)
    const uuid = result.headers['X-Request-ID']
    expect(uuid).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    )
  })

  it('三个连续请求的 X-Request-ID 互不相同', () => {
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    const ids = new Set<string>()
    for (let i = 0; i < 3; i++) {
      const result = handler({ headers: {} } as never)
      ids.add(result.headers['X-Request-ID'])
    }
    expect(ids.size).toBe(3)
  })

  it('headers 为空对象时 X-Request-ID 正常生成', () => {
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    const result = handler({ headers: {} } as never)
    expect(result.headers['X-Request-ID']).toBeDefined()
    expect(typeof result.headers['X-Request-ID']).toBe('string')
  })

  it('空字符串 token 不设置 Authorization', () => {
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    localStorage.setItem('access_token', '')
    const config = { headers: {} }
    const result = handler(config as never)
    // 空字符串 '' 是 falsy，if(token) 为 false，不设置 Authorization
    expect(result.headers.Authorization).toBeUndefined()
  })
})

// ═══════════════════════════════════════════════════════
// 3. 响应拦截器错误优先级链边界
// ═══════════════════════════════════════════════════════

describe('拦截器错误优先级链', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('422 有 error.message 时显示后端消息', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: {
        status: 422,
        headers: {},
        data: { success: false, error: { code: 'VALIDATION', message: '字段校验失败' } },
      },
    }

    try { await handler(error) } catch {}
    expect(mockMsgError).toHaveBeenCalledWith('字段校验失败')
  })

  it('422 有 data.message 但无 error.message 时回退', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: {
        status: 422,
        headers: {},
        data: { message: '格式错误' },
      },
    }

    try { await handler(error) } catch {}
    expect(mockMsgError).toHaveBeenCalledWith('格式错误')
  })

  it('401 _retry=true 时不走刷新也不弹 toast', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    delete window.location
    window.location = { href: '' } as Location

    const error = {
      config: { headers: {}, _retry: true, _retry429: false },
      response: {
        status: 401,
        headers: {},
        data: { error: { message: 'token 过期' } },
      },
    }

    try { await handler(error) } catch {}
    expect(mockMsgError).not.toHaveBeenCalled()
  })

  it('402 未知状态码有 error.message 时显示', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: {
        status: 402,
        headers: {},
        data: { error: { code: 'PAYMENT_REQUIRED', message: '需要付款' } },
      },
    }

    try { await handler(error) } catch {}
    expect(mockMsgError).toHaveBeenCalledWith('需要付款')
  })

  it('503 有 error.message 时显示后端消息', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: {
        status: 503,
        headers: {},
        data: { error: { code: 'SERVICE_DOWN', message: '服务暂不可用' } },
      },
    }

    try { await handler(error) } catch {}
    expect(mockMsgError).toHaveBeenCalledWith('服务暂不可用')
  })

  it('error.message 和 data.message 同时存在时 error.message 优先', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: {
        status: 400,
        headers: {},
        data: {
          error: { message: '首选消息' },
          message: '备选消息',
        },
      },
    }

    try { await handler(error) } catch {}
    expect(mockMsgError).toHaveBeenCalledWith('首选消息')
  })

  it('200 成功响应直接透传', () => {
    const handler = apiClient.interceptors.response.handlers[0]?.fulfilled
    if (!handler) throw new Error('No success handler')

    const response = { status: 200, data: { success: true } }
    const result = handler(response as never)
    expect(result).toEqual(response)
  })

  it('无 config 的错误直接 reject 不弹 toast', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = { response: { status: 500, data: {} } }
    await expect(handler(error)).rejects.toEqual(error)
    expect(mockMsgError).not.toHaveBeenCalled()
  })
})

// ═══════════════════════════════════════════════════════
// 4. 429 Retry-After 边界
// ═══════════════════════════════════════════════════════

describe('429 Retry-After 边界', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('Retry-After 为小数时 parseInt 截断为整数', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const config = { headers: {}, _retry: false, _retry429: false }
    const error = {
      config,
      response: { status: 429, headers: { 'retry-after': '2.7' }, data: {} },
    }
    const originalAdapter = apiClient.defaults.adapter
    apiClient.defaults.adapter = async () =>
      ({ data: 'ok', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

    vi.useFakeTimers()
    const promise = handler(error)
    await vi.advanceTimersByTimeAsync(2000)
    const result = await promise
    expect(result.data).toBe('ok')

    vi.useRealTimers()
    apiClient.defaults.adapter = originalAdapter
  })

  it('Retry-After 为 "0" 时立即重试', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const config = { headers: {}, _retry: false, _retry429: false }
    const error = {
      config,
      response: { status: 429, headers: { 'retry-after': '0' }, data: {} },
    }
    const originalAdapter = apiClient.defaults.adapter
    apiClient.defaults.adapter = async () =>
      ({ data: 'zero', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

    const result = await handler(error)
    expect(result.data).toBe('zero')
    apiClient.defaults.adapter = originalAdapter
  })

  it('Retry-After 为负数时立即重试', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const config = { headers: {}, _retry: false, _retry429: false }
    const error = {
      config,
      response: { status: 429, headers: { 'retry-after': '-1' }, data: {} },
    }
    const originalAdapter = apiClient.defaults.adapter
    apiClient.defaults.adapter = async () =>
      ({ data: 'negative', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

    const result = await handler(error)
    expect(result.data).toBe('negative')
    apiClient.defaults.adapter = originalAdapter
  })

  it('Retry-After 为 "1" 时等待 1 秒后重试', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const config = { headers: {}, _retry: false, _retry429: false }
    const error = {
      config,
      response: { status: 429, headers: { 'retry-after': '1' }, data: {} },
    }
    const originalAdapter = apiClient.defaults.adapter
    apiClient.defaults.adapter = async () =>
      ({ data: 'one', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

    vi.useFakeTimers()
    const promise = handler(error)
    await vi.advanceTimersByTimeAsync(1000)
    const result = await promise
    expect(result.data).toBe('one')

    vi.useRealTimers()
    apiClient.defaults.adapter = originalAdapter
  })
})

// ═══════════════════════════════════════════════════════
// 5. _toastDisplayed 标记设置边界
// ═══════════════════════════════════════════════════════

describe('_toastDisplayed 标记边界', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('500 错误设置 _toastDisplayed=true', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: { status: 500, headers: {}, data: {} },
    }

    try {
      await handler(error)
    } catch (e) {
      expect((e as Record<string, boolean>)._toastDisplayed).toBe(true)
    }
  })

  it('网络错误设置 _toastDisplayed=true', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false },
    }

    try {
      await handler(error)
    } catch (e) {
      expect((e as Record<string, boolean>)._toastDisplayed).toBe(true)
    }
  })

  it('404 设置 _toastDisplayed=true', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: { status: 404, headers: {}, data: {} },
    }

    try {
      await handler(error)
    } catch (e) {
      expect((e as Record<string, boolean>)._toastDisplayed).toBe(true)
    }
  })

  it('403 设置 _toastDisplayed=true', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: { status: 403, headers: {}, data: {} },
    }

    try {
      await handler(error)
    } catch (e) {
      expect((e as Record<string, boolean>)._toastDisplayed).toBe(true)
    }
  })

  it('429 已重试设置 _toastDisplayed=true', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: true },
      response: { status: 429, headers: {}, data: {} },
    }

    try {
      await handler(error)
    } catch (e) {
      expect((e as Record<string, boolean>)._toastDisplayed).toBe(true)
    }
  })

  it('400 有 error.message 设置 _toastDisplayed=true', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: {
        status: 400,
        headers: {},
        data: { error: { message: '参数错误' } },
      },
    }

    try {
      await handler(error)
    } catch (e) {
      expect((e as Record<string, boolean>)._toastDisplayed).toBe(true)
    }
  })
})

// ═══════════════════════════════════════════════════════
// 6. 401 刷新边界
// ═══════════════════════════════════════════════════════

describe('401 刷新边界', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('401 有 refresh_token 但刷新失败时清除 token 并跳转', async () => {
    localStorage.setItem('access_token', 'old-token')
    localStorage.setItem('refresh_token', 'expired-refresh')
    mockAxiosPost.mockRejectedValueOnce(new Error('refresh expired'))
    delete window.location
    window.location = { href: '' } as Location

    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: { status: 401, headers: {}, data: {} },
    }

    try { await handler(error) } catch {}
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(window.location.href).toBe('/login')
  })

  it('401 无 refresh_token 时清除 access_token 并跳转', async () => {
    localStorage.setItem('access_token', 'only-access')
    delete window.location
    window.location = { href: '' } as Location

    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: { status: 401, headers: {}, data: {} },
    }

    try { await handler(error) } catch {}
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(window.location.href).toBe('/login')
  })

  it('401 刷新成功后重试使用新 access_token', async () => {
    localStorage.setItem('access_token', 'old')
    localStorage.setItem('refresh_token', 'old-refresh')
    mockAxiosPost.mockResolvedValueOnce({
      data: { data: { access_token: 'brand-new', refresh_token: 'new-r' } },
    })

    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const config = { headers: {}, _retry: false, _retry429: false }
    const error = { config, response: { status: 401, headers: {}, data: {} } }

    const originalAdapter = apiClient.defaults.adapter
    apiClient.defaults.adapter = async () =>
      ({ data: 'ok', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

    try { await handler(error) } catch {}
    expect(config.headers.Authorization).toBe('Bearer brand-new')
    apiClient.defaults.adapter = originalAdapter
  })

  it('401 刷新成功保存新 refresh_token', async () => {
    localStorage.setItem('access_token', 'old')
    localStorage.setItem('refresh_token', 'old-refresh')
    mockAxiosPost.mockResolvedValueOnce({
      data: { data: { access_token: 'new-a', refresh_token: 'new-r' } },
    })

    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: { status: 401, headers: {}, data: {} },
    }

    const originalAdapter = apiClient.defaults.adapter
    apiClient.defaults.adapter = async () =>
      ({ data: 'ok', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

    try { await handler(error) } catch {}
    expect(localStorage.getItem('refresh_token')).toBe('new-r')
    apiClient.defaults.adapter = originalAdapter
  })

  it('401 刷新使用 raw axios（不走拦截器）', async () => {
    localStorage.setItem('refresh_token', 'r')
    mockAxiosPost.mockResolvedValueOnce({
      data: { data: { access_token: 'a', refresh_token: 'r' } },
    })

    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false, _retry429: false },
      response: { status: 401, headers: {}, data: {} },
    }

    const originalAdapter = apiClient.defaults.adapter
    apiClient.defaults.adapter = async () =>
      ({ data: 'ok', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

    try { await handler(error) } catch {}
    expect(mockAxiosPost).toHaveBeenCalledWith(
      `${apiClient.defaults.baseURL}/auth/refresh`,
      expect.any(Object),
    )
    apiClient.defaults.adapter = originalAdapter
  })
})
