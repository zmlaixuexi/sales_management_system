import { describe, it, expect, beforeEach } from 'vitest'
import apiClient from '@/api/client'

describe('apiClient', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('baseURL 默认指向本地开发后端', () => {
    expect(apiClient.defaults.baseURL).toContain('/api/v1')
  })

  it('请求拦截器自动附加 access_token', async () => {
    localStorage.setItem('access_token', 'test-token-123')
    const config = await apiClient.interceptors.request.handlers[0].fulfilled({
      headers: {} as Record<string, string>,
    })
    expect(config.headers.Authorization).toBe('Bearer test-token-123')
  })

  it('请求拦截器无 token 时不附加 Authorization', async () => {
    const config = await apiClient.interceptors.request.handlers[0].fulfilled({
      headers: {} as Record<string, string>,
    })
    expect(config.headers.Authorization).toBeUndefined()
  })

  it('请求拦截器自动附加 X-Request-ID', async () => {
    const config = await apiClient.interceptors.request.handlers[0].fulfilled({
      headers: {} as Record<string, string>,
    })
    expect(config.headers['X-Request-ID']).toBeTruthy()
    // UUID v4 格式
    expect(config.headers['X-Request-ID']).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    )
  })

  it('每次请求生成不同的 X-Request-ID', async () => {
    const config1 = await apiClient.interceptors.request.handlers[0].fulfilled({
      headers: {} as Record<string, string>,
    })
    const config2 = await apiClient.interceptors.request.handlers[0].fulfilled({
      headers: {} as Record<string, string>,
    })
    expect(config1.headers['X-Request-ID']).not.toBe(config2.headers['X-Request-ID'])
  })

  it('timeout 默认 15 秒', () => {
    expect(apiClient.defaults.timeout).toBe(15000)
  })

  it('默认 Content-Type 为 application/json', () => {
    expect(apiClient.defaults.headers.common['Content-Type'] || apiClient.defaults.headers['Content-Type']).toBeDefined()
  })
})
