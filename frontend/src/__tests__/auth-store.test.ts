import { describe, it, expect, vi, beforeEach } from 'vitest'

// 模拟 auth API
vi.mock('../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn(),
    getMe: vi.fn(),
  },
}))

import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'
import type { CurrentUser } from '../api/auth'

const mockLogin = authApi.login as ReturnType<typeof vi.fn>
const mockGetMe = authApi.getMe as ReturnType<typeof vi.fn>
const mockLogout = authApi.logout as ReturnType<typeof vi.fn>

const fakeUser: CurrentUser = {
  id: 'user-1',
  username: 'admin',
  display_name: '管理员',
  is_active: true,
  is_superuser: false,
  roles: [{ id: 'role-1', name: 'admin', display_name: '管理员' }],
  permissions: ['product:list', 'order:create'],
}

const superUser: CurrentUser = {
  ...fakeUser,
  is_superuser: true,
  permissions: [],
}

function mockTokenResponse(access = 'access-123', refresh = 'refresh-456') {
  return {
    data: {
      success: true,
      data: { access_token: access, refresh_token: refresh, token_type: 'bearer' },
    },
  }
}

function mockUserResponse(user: CurrentUser = fakeUser) {
  return { data: { success: true, data: user } }
}

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    // 重置 store 状态
    useAuthStore.setState({ token: null, user: null, loading: false })
  })

  describe('login', () => {
    it('登录成功：存储 token 并获取用户信息', async () => {
      mockLogin.mockResolvedValueOnce(mockTokenResponse())
      mockGetMe.mockResolvedValueOnce(mockUserResponse())

      await useAuthStore.getState().login('admin', 'password')

      expect(localStorage.getItem('access_token')).toBe('access-123')
      expect(localStorage.getItem('refresh_token')).toBe('refresh-456')
      expect(useAuthStore.getState().token).toBe('access-123')
      expect(useAuthStore.getState().user?.username).toBe('admin')
      expect(useAuthStore.getState().loading).toBe(false)
    })

    it('登录失败：token 和 user 不变', async () => {
      mockLogin.mockRejectedValueOnce(new Error('网络错误'))

      await useAuthStore.getState().login('admin', 'wrong').catch(() => {})

      expect(useAuthStore.getState().token).toBeNull()
      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().loading).toBe(false)
    })

    it('登录过程中 loading 状态变化', async () => {
      let loadingDuringCall = false
      mockLogin.mockImplementationOnce(async () => {
        loadingDuringCall = useAuthStore.getState().loading
        return mockTokenResponse()
      })
      mockGetMe.mockResolvedValueOnce(mockUserResponse())

      await useAuthStore.getState().login('admin', 'password')

      expect(loadingDuringCall).toBe(true)
      expect(useAuthStore.getState().loading).toBe(false)
    })
  })

  describe('logout', () => {
    it('登出：清除 token 和用户信息', () => {
    mockLogout.mockResolvedValueOnce({})
      useAuthStore.setState({ token: 'test', user: fakeUser })
      localStorage.setItem('access_token', 'test')
      localStorage.setItem('refresh_token', 'test')

      useAuthStore.getState().logout()

      expect(localStorage.getItem('access_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
      expect(useAuthStore.getState().token).toBeNull()
      expect(useAuthStore.getState().user).toBeNull()
    })

    it('登出：调用 logout API（忽略错误）', () => {
      mockLogout.mockRejectedValueOnce(new Error('网络错误'))

      useAuthStore.getState().logout()

      expect(mockLogout).toHaveBeenCalled()
    })
  })

  describe('fetchUser', () => {
    it('获取用户信息成功', async () => {
      mockGetMe.mockResolvedValueOnce(mockUserResponse())

      await useAuthStore.getState().fetchUser()

      expect(useAuthStore.getState().user?.username).toBe('admin')
    })

    it('获取用户信息失败：清除 token', async () => {
      localStorage.setItem('access_token', 'test')
      localStorage.setItem('refresh_token', 'test')
      useAuthStore.setState({ token: 'test' })
      mockGetMe.mockRejectedValueOnce(new Error('401'))

      await useAuthStore.getState().fetchUser()

      expect(useAuthStore.getState().token).toBeNull()
      expect(useAuthStore.getState().user).toBeNull()
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })

  describe('hasPermission', () => {
    it('无用户时返回 false', () => {
      expect(useAuthStore.getState().hasPermission('product:list')).toBe(false)
    })

    it('普通用户：有权限返回 true', () => {
      useAuthStore.setState({ user: fakeUser })
      expect(useAuthStore.getState().hasPermission('product:list')).toBe(true)
    })

    it('普通用户：无权限返回 false', () => {
      useAuthStore.setState({ user: fakeUser })
      expect(useAuthStore.getState().hasPermission('user:delete')).toBe(false)
    })

    it('超级用户：始终返回 true', () => {
      useAuthStore.setState({ user: superUser })
      expect(useAuthStore.getState().hasPermission('any:permission')).toBe(true)
    })
  })
})
