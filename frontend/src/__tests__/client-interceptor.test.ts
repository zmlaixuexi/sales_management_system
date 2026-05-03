import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// mock antd message
vi.mock('antd', () => ({
  message: { error: vi.fn() },
}))

// mock axios.post for refresh calls
vi.spyOn(axios, 'post')

import apiClient from '@/api/client'
import { message } from 'antd'

const mockMessageError = vi.mocked(message.error)
const mockAxiosPost = vi.mocked(axios.post)

// helper: trigger response error interceptor
async function triggerErrorInterceptor(status: number, extra: Record<string, unknown> = {}) {
  const handler = apiClient.interceptors.response.handlers[0]?.rejected
  if (!handler) throw new Error('No error handler')

  const error = {
    config: { headers: {}, _retry: false, _retry429: false, ...extra.config },
    response: {
      status,
      headers: extra.headers || {},
      data: extra.data || {},
    },
  }
  return handler(error)
}

describe('apiClient 响应拦截器', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('401 有 refresh_token 时刷新并重试', async () => {
    localStorage.setItem('access_token', 'old-token')
    localStorage.setItem('refresh_token', 'refresh-123')
    mockAxiosPost.mockResolvedValueOnce({
      data: { data: { access_token: 'new-token', refresh_token: 'new-refresh' } },
    })

    const requestSpy = vi.spyOn(apiClient, 'request').mockResolvedValueOnce({ data: 'ok' } as never)

    try {
      await triggerErrorInterceptor(401)
    } catch {
      // 可能 reject，不影响断言
    }

    expect(mockAxiosPost).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      { refresh_token: 'refresh-123' },
    )
    expect(localStorage.getItem('access_token')).toBe('new-token')

    requestSpy.mockRestore()
  })

  it('401 无 refresh_token 时跳转登录页', async () => {
    localStorage.setItem('access_token', 'old-token')
    delete window.location
    window.location = { href: '' } as Location

    try {
      await triggerErrorInterceptor(401)
    } catch {
      // expected
    }

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(window.location.href).toBe('/login')
  })

  it('403 显示无权限错误提示', async () => {
    try {
      await triggerErrorInterceptor(403)
    } catch {
      // expected
    }

    expect(mockMessageError).toHaveBeenCalledWith('没有操作权限')
  })

  it('404 显示资源不存在错误提示', async () => {
    try {
      await triggerErrorInterceptor(404)
    } catch {
      // expected
    }

    expect(mockMessageError).toHaveBeenCalledWith('请求的资源不存在')
  })

  it('500 显示服务器错误提示', async () => {
    try {
      await triggerErrorInterceptor(500)
    } catch {
      // expected
    }

    expect(mockMessageError).toHaveBeenCalledWith('服务器错误，请稍后重试')
  })

  it('网络错误显示连接失败提示', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = {
      config: { headers: {}, _retry: false },
      // 无 response 表示网络错误
    }

    try {
      await handler(error)
    } catch {
      // expected
    }

    expect(mockMessageError).toHaveBeenCalledWith('网络连接失败，请检查网络')
  })

  it('重复 401 不无限重试（_retry 标记）', async () => {
    localStorage.setItem('refresh_token', 'some-refresh')
    delete window.location
    window.location = { href: '' } as Location

    // 带有 _retry=true 的请求不会再刷新
    try {
      await triggerErrorInterceptor(401, { config: { _retry: true } })
    } catch {
      // expected
    }

    expect(mockAxiosPost).not.toHaveBeenCalled()
  })

  describe('429 速率限制重试', () => {
    it('429 首次时设置 _retry429 标记防止重复重试', async () => {
      const handler = apiClient.interceptors.response.handlers[0]?.rejected
      if (!handler) throw new Error('No error handler')

      const config = { headers: {}, _retry: false, _retry429: false }
      const error = {
        config,
        response: { status: 429, headers: { 'retry-after': '2' }, data: {} },
      }

      // 不等待重试完成，只验证 flag 已设置
      vi.useFakeTimers()
      handler(error).catch(() => {})
      // 同步检查：handler 在 await setTimeout 之前已设置 flag
      expect(config._retry429).toBe(true)
      vi.useRealTimers()
    })

    it('429 重试后使用 apiClient 重发原始请求', async () => {
      const handler = apiClient.interceptors.response.handlers[0]?.rejected
      if (!handler) throw new Error('No error handler')

      const config = { headers: {}, _retry: false, _retry429: false }
      const error = {
        config,
        response: { status: 429, headers: { 'retry-after': '0' }, data: {} },
      }

      // Patch adapter to prevent real HTTP call on retry
      const originalAdapter = apiClient.defaults.adapter
      apiClient.defaults.adapter = async () => ({ data: 'retried', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

      const result = await handler(error)
      expect(config._retry429).toBe(true)
      expect(result.data).toBe('retried')

      // Restore
      apiClient.defaults.adapter = originalAdapter
    })

    it('429 无 retry-after 头时使用默认 5 秒等待', async () => {
      const handler = apiClient.interceptors.response.handlers[0]?.rejected
      if (!handler) throw new Error('No error handler')

      const config = { headers: {}, _retry: false, _retry429: false }
      const error = {
        config,
        response: { status: 429, headers: {}, data: {} },
      }

      const originalAdapter = apiClient.defaults.adapter
      apiClient.defaults.adapter = async () => ({ data: 'default-wait', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

      vi.useFakeTimers()
      const promise = handler(error)
      // 默认 retry-after='5' → 5000ms，Math.min(5000, 5000) = 5000
      await vi.advanceTimersByTimeAsync(5000)
      const result = await promise
      expect(result.data).toBe('default-wait')

      vi.useRealTimers()
      apiClient.defaults.adapter = originalAdapter
    })

    it('429 已重试过显示错误提示', async () => {
      try {
        await triggerErrorInterceptor(429, { config: { _retry429: true } })
      } catch {
        // expected
      }

      expect(mockMessageError).toHaveBeenCalledWith('请求过于频繁，请稍后再试')
    })

    it('429 Retry-After 大于 5000 时上限为 5 秒', async () => {
      const handler = apiClient.interceptors.response.handlers[0]?.rejected
      if (!handler) throw new Error('No error handler')

      const config = { headers: {}, _retry: false, _retry429: false }
      const error = {
        config,
        response: { status: 429, headers: { 'retry-after': '100' }, data: {} },
      }
      const originalAdapter = apiClient.defaults.adapter
      apiClient.defaults.adapter = async () => ({ data: 'capped', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

      vi.useFakeTimers()
      const promise = handler(error)
      // Retry-After=100 → 100*1000=100000ms，Math.min(100000, 5000)=5000
      await vi.advanceTimersByTimeAsync(5000)
      const result = await promise
      expect(result.data).toBe('capped')
      vi.useRealTimers()
      apiClient.defaults.adapter = originalAdapter
    })

    it('429 Retry-After 非数字时立即重试', async () => {
      const handler = apiClient.interceptors.response.handlers[0]?.rejected
      if (!handler) throw new Error('No error handler')

      const config = { headers: {}, _retry: false, _retry429: false }
      const error = {
        config,
        response: { status: 429, headers: { 'retry-after': 'abc' }, data: {} },
      }
      const originalAdapter = apiClient.defaults.adapter
      apiClient.defaults.adapter = async () => ({ data: 'nan-retry', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

      // parseInt('abc')=NaN, NaN*1000=NaN, setTimeout(cb, NaN)≈setTimeout(cb, 0)
      const result = await handler(error)
      expect(result.data).toBe('nan-retry')
      apiClient.defaults.adapter = originalAdapter
    })

    it('429 Retry-After 为空字符串使用默认 5 秒', async () => {
      const handler = apiClient.interceptors.response.handlers[0]?.rejected
      if (!handler) throw new Error('No error handler')

      const config = { headers: {}, _retry: false, _retry429: false }
      const error = {
        config,
        response: { status: 429, headers: { 'retry-after': '' }, data: {} },
      }
      const originalAdapter = apiClient.defaults.adapter
      apiClient.defaults.adapter = async () => ({ data: 'empty-hdr', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

      vi.useFakeTimers()
      const promise = handler(error)
      // ''||'5'='5'，parseInt('5')*1000=5000
      await vi.advanceTimersByTimeAsync(5000)
      const result = await promise
      expect(result.data).toBe('empty-hdr')
      vi.useRealTimers()
      apiClient.defaults.adapter = originalAdapter
    })
  })

  it('展示 toast 后设置 _toastDisplayed 标记', async () => {
    try {
      await triggerErrorInterceptor(403)
    } catch (e) {
      expect((e as Record<string, boolean>)._toastDisplayed).toBe(true)
    }
  })

  it('401 不设置 _toastDisplayed 标记', async () => {
    delete window.location
    window.location = { href: '' } as Location
    try {
      await triggerErrorInterceptor(401)
    } catch (e) {
      expect((e as Record<string, boolean>)._toastDisplayed).toBeUndefined()
    }
  })

  it('400 从 error.message 提取后端错误消息', async () => {
    try {
      await triggerErrorInterceptor(400, {
        data: { success: false, error: { code: 'VALIDATION_FAILED', message: '参数校验失败：名称不能为空' } },
      })
    } catch {
      // expected
    }

    expect(mockMessageError).toHaveBeenCalledWith('参数校验失败：名称不能为空')
  })

  it('400 旧格式 detail.message 兼容', async () => {
    try {
      await triggerErrorInterceptor(400, {
        data: { success: false, detail: { code: 'VALIDATION_FAILED', message: '旧格式错误' } },
      })
    } catch {
      // expected
    }

    // 旧格式不应匹配（无 error.message），走 data.message fallback
    expect(mockMessageError).not.toHaveBeenCalledWith('旧格式错误')
  })

  it('409 展示后端业务错误消息', async () => {
    try {
      await triggerErrorInterceptor(409, {
        data: { success: false, error: { code: 'PRODUCT_IN_USE', message: '商品已被引用，不能删除' } },
      })
    } catch {
      // expected
    }

    expect(mockMessageError).toHaveBeenCalledWith('商品已被引用，不能删除')
  })

  it('401 有 refresh_token 但刷新失败时清除 token 并跳转', async () => {
    localStorage.setItem('access_token', 'old-token')
    localStorage.setItem('refresh_token', 'expired-refresh')
    mockAxiosPost.mockRejectedValueOnce(new Error('refresh expired'))
    delete window.location
    window.location = { href: '' } as Location

    try {
      await triggerErrorInterceptor(401)
    } catch {
      // expected
    }

    expect(mockAxiosPost).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      { refresh_token: 'expired-refresh' },
    )
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(window.location.href).toBe('/login')
  })

  it('非 401 错误有 data.message 但无 error.message 时显示 data.message', async () => {
    try {
      await triggerErrorInterceptor(422, {
        data: { success: false, message: '参数格式不正确' },
      })
    } catch {
      // expected
    }

    expect(mockMessageError).toHaveBeenCalledWith('参数格式不正确')
  })

  it('成功响应直接返回', () => {
    const handler = apiClient.interceptors.response.handlers[0]?.fulfilled
    expect(handler).toBeDefined()
    const response = { status: 200, data: { foo: 'bar' } }
    expect(handler!(response as never)).toEqual(response)
  })

  it('无 config 的错误直接 reject 不显示 toast', async () => {
    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')

    const error = { response: { status: 500, data: {} } }
    await expect(handler(error)).rejects.toEqual(error)
    expect(mockMessageError).not.toHaveBeenCalled()
  })

  it('401 refresh 保存新 refresh_token', async () => {
    localStorage.setItem('access_token', 'old')
    localStorage.setItem('refresh_token', 'old-refresh')
    mockAxiosPost.mockResolvedValueOnce({
      data: { data: { access_token: 'new-a', refresh_token: 'new-r' } },
    })
    const requestSpy = vi.spyOn(apiClient, 'request').mockResolvedValueOnce({ data: 'ok' } as never)
    try { await triggerErrorInterceptor(401) } catch {}
    expect(localStorage.getItem('refresh_token')).toBe('new-r')
    requestSpy.mockRestore()
  })

  it('401 refresh URL 使用 apiClient.defaults.baseURL', async () => {
    localStorage.setItem('refresh_token', 'r')
    mockAxiosPost.mockResolvedValueOnce({
      data: { data: { access_token: 'a', refresh_token: 'r' } },
    })
    const requestSpy = vi.spyOn(apiClient, 'request').mockResolvedValueOnce({ data: 'ok' } as never)
    try { await triggerErrorInterceptor(401) } catch {}
    expect(mockAxiosPost).toHaveBeenCalledWith(
      `${apiClient.defaults.baseURL}/auth/refresh`,
      expect.any(Object),
    )
    requestSpy.mockRestore()
  })

  it('401 refresh 成功后重试使用新 access_token', async () => {
    localStorage.setItem('access_token', 'old')
    localStorage.setItem('refresh_token', 'old-refresh')
    mockAxiosPost.mockResolvedValueOnce({
      data: { data: { access_token: 'brand-new', refresh_token: 'new-r' } },
    })
    const originalAdapter = apiClient.defaults.adapter
    apiClient.defaults.adapter = async () => ({ data: 'ok', status: 200, statusText: 'OK', headers: {}, config: {} } as never)

    const handler = apiClient.interceptors.response.handlers[0]?.rejected
    if (!handler) throw new Error('No error handler')
    const config = { headers: {}, _retry: false, _retry429: false }
    const error = { config, response: { status: 401, headers: {}, data: {} } }

    try { await handler(error) } catch {}
    // refresh 后 config.Authorization 被更新为新 token
    expect(config.headers.Authorization).toBe('Bearer brand-new')
    apiClient.defaults.adapter = originalAdapter
  })
})

describe('apiClient 请求拦截器', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('无 token 时不设置 Authorization 头', () => {
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    const config = { headers: {} }
    const result = handler(config as never)
    expect(result.headers.Authorization).toBeUndefined()
  })

  it('有 token 时设置 Bearer 前缀', () => {
    localStorage.setItem('access_token', 'jwt-abc')
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    const config = { headers: {} }
    const result = handler(config as never)
    expect(result.headers.Authorization).toBe('Bearer jwt-abc')
  })

  it('X-Request-ID 为 UUID 格式', () => {
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    const config = { headers: {} }
    const result = handler(config as never)
    expect(result.headers['X-Request-ID']).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    )
  })

  it('每次请求生成不同的 X-Request-ID', () => {
    const handler = apiClient.interceptors.request.handlers[0]?.fulfilled
    if (!handler) throw new Error('No request handler')

    const result1 = handler({ headers: {} } as never)
    const result2 = handler({ headers: {} } as never)
    expect(result1.headers['X-Request-ID']).not.toBe(result2.headers['X-Request-ID'])
  })
})
