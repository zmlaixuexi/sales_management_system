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
})
