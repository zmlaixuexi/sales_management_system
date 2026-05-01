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

    it('429 已重试过显示错误提示', async () => {
      try {
        await triggerErrorInterceptor(429, { config: { _retry429: true } })
      } catch {
        // expected
      }

      expect(mockMessageError).toHaveBeenCalledWith('请求过于频繁，请稍后再试')
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
})
