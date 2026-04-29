import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
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
})
