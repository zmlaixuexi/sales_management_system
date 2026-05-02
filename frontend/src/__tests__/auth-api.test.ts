import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../api/client', () => ({
  default: {
    post: vi.fn(() => Promise.resolve({ data: { success: true } })),
    get: vi.fn(() => Promise.resolve({ data: { success: true } })),
  },
}))

import apiClient from '../api/client'
import { authApi } from '../api/auth'

const mockPost = apiClient.post as ReturnType<typeof vi.fn>
const mockGet = apiClient.get as ReturnType<typeof vi.fn>

beforeEach(() => {
  vi.clearAllMocks()
})

describe('authApi', () => {
  it('login 调用 POST /auth/login', async () => {
    await authApi.login({ username: 'admin', password: '123' })
    expect(mockPost).toHaveBeenCalledWith('/auth/login', {
      username: 'admin',
      password: '123',
    })
  })

  it('login 返回 token 数据', async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        success: true,
        data: { access_token: 'acc', refresh_token: 'ref', token_type: 'bearer' },
      },
    })
    const res = await authApi.login({ username: 'admin', password: '123' })
    expect(res.data.data.access_token).toBe('acc')
    expect(res.data.data.refresh_token).toBe('ref')
  })

  it('refresh 调用 POST /auth/refresh 携带 refresh_token', async () => {
    await authApi.refresh('token123')
    expect(mockPost).toHaveBeenCalledWith('/auth/refresh', {
      refresh_token: 'token123',
    })
  })

  it('logout 调用 POST /auth/logout', async () => {
    await authApi.logout()
    expect(mockPost).toHaveBeenCalledWith('/auth/logout')
  })

  it('getMe 调用 GET /auth/me', async () => {
    await authApi.getMe()
    expect(mockGet).toHaveBeenCalledWith('/auth/me')
  })

  it('getMe 返回用户权限列表', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          id: 'u1', username: 'admin', display_name: '管理员',
          is_active: true, is_superuser: false,
          roles: [{ id: 'r1', name: 'admin', display_name: '管理员' }],
          permissions: ['product:list', 'order:create'],
        },
      },
    })
    const res = await authApi.getMe()
    expect(res.data.data.permissions).toContain('order:create')
    expect(res.data.data.roles[0].name).toBe('admin')
  })

  it('changePassword 调用 POST /auth/change-password', async () => {
    await authApi.changePassword('old123', 'new456')
    expect(mockPost).toHaveBeenCalledWith('/auth/change-password', {
      old_password: 'old123',
      new_password: 'new456',
    })
  })
})
