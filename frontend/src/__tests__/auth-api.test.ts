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
})
