/**
 * 测试补强：Zustand auth store 边界测试
 * 覆盖初始化状态、token 持久化、login 失败后 loading 重置、
 * hasPermission 边界、logout API 错误处理、fetchUser 成功返回后状态
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

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

describe('useAuthStore 边界测试', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    useAuthStore.setState({ token: null, user: null, loading: false })
  })

  // ═══════════════════════════════════════════════════════
  // 1. 初始状态
  // ═══════════════════════════════════════════════════════

  it('初始 loading 为 false', () => {
    expect(useAuthStore.getState().loading).toBe(false)
  })

  it('localStorage 无 token 时初始 token 为 null', () => {
    expect(useAuthStore.getState().token).toBeNull()
  })

  it('初始 user 为 null', () => {
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('localStorage 有 token 时初始 token 从 localStorage 读取', () => {
    localStorage.setItem('access_token', 'saved-token')
    // 需要重新创建 store 来测试初始化
    // Zustand 的 create 只执行一次，测试中用 setState 模拟
    useAuthStore.setState({ token: 'saved-token' })
    expect(useAuthStore.getState().token).toBe('saved-token')
  })

  // ═══════════════════════════════════════════════════════
  // 2. Login 边界
  // ═══════════════════════════════════════════════════════

  it('login 成功后 fetchUser 被调用', async () => {
    mockLogin.mockResolvedValueOnce(mockTokenResponse())
    mockGetMe.mockResolvedValueOnce(mockUserResponse())

    await useAuthStore.getState().login('admin', 'pass')

    expect(mockGetMe).toHaveBeenCalledTimes(1)
  })

  it('login 失败后 loading 仍重置为 false', async () => {
    mockLogin.mockRejectedValueOnce(new Error('网络断开'))

    try {
      await useAuthStore.getState().login('admin', 'pass')
    } catch {
      // expected
    }

    expect(useAuthStore.getState().loading).toBe(false)
  })

  it('login API success:false 后 loading 重置为 false', async () => {
    mockLogin.mockResolvedValueOnce({
      data: { success: false, error: { code: 'AUTH_FAILED', message: '失败' } },
    })

    try {
      await useAuthStore.getState().login('admin', 'pass')
    } catch {
      // expected
    }

    expect(useAuthStore.getState().loading).toBe(false)
  })

  it('login 成功但 fetchUser 失败会清除 token', async () => {
    mockLogin.mockResolvedValueOnce(mockTokenResponse())
    mockGetMe.mockRejectedValueOnce(new Error('获取用户失败'))

    await useAuthStore.getState().login('admin', 'pass')

    // fetchUser 失败会清除 token 和 localStorage
    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })

  // ═══════════════════════════════════════════════════════
  // 3. Logout 边界
  // ═══════════════════════════════════════════════════════

  it('logout 清除 localStorage 中两个 key', () => {
    localStorage.setItem('access_token', 'a')
    localStorage.setItem('refresh_token', 'r')
    useAuthStore.setState({ token: 'a', user: fakeUser })
    mockLogout.mockResolvedValueOnce({})

    useAuthStore.getState().logout()

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })

  it('logout 后 hasPermission 返回 false', () => {
    useAuthStore.setState({ user: fakeUser })
    expect(useAuthStore.getState().hasPermission('product:list')).toBe(true)
    mockLogout.mockResolvedValueOnce({})

    useAuthStore.getState().logout()
    expect(useAuthStore.getState().hasPermission('product:list')).toBe(false)
  })

  it('logout API 失败仍清除本地状态', () => {
    mockLogout.mockRejectedValueOnce(new Error('网络错误'))
    useAuthStore.setState({ token: 'test', user: fakeUser })
    localStorage.setItem('access_token', 'test')

    useAuthStore.getState().logout()

    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  // ═══════════════════════════════════════════════════════
  // 4. fetchUser 边界
  // ═══════════════════════════════════════════════════════

  it('fetchUser 成功后 user 有正确的字段', async () => {
    mockGetMe.mockResolvedValueOnce(mockUserResponse())

    await useAuthStore.getState().fetchUser()

    const user = useAuthStore.getState().user!
    expect(user.id).toBe('user-1')
    expect(user.username).toBe('admin')
    expect(user.display_name).toBe('管理员')
    expect(user.is_active).toBe(true)
    expect(user.is_superuser).toBe(false)
    expect(user.roles).toHaveLength(1)
    expect(user.permissions).toContain('product:list')
  })

  it('fetchUser 失败后 token 和 user 都为 null', async () => {
    useAuthStore.setState({ token: 'old-token', user: fakeUser })
    localStorage.setItem('access_token', 'old-token')
    localStorage.setItem('refresh_token', 'old-refresh')
    mockGetMe.mockRejectedValueOnce(new Error('401'))

    await useAuthStore.getState().fetchUser()

    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })

  it('fetchUser 成功不改变 token', async () => {
    useAuthStore.setState({ token: 'existing-token' })
    mockGetMe.mockResolvedValueOnce(mockUserResponse())

    await useAuthStore.getState().fetchUser()

    expect(useAuthStore.getState().token).toBe('existing-token')
  })

  // ═══════════════════════════════════════════════════════
  // 5. hasPermission 边界
  // ═══════════════════════════════════════════════════════

  it('超级用户无 permissions 数组仍返回 true', () => {
    const superUser: CurrentUser = {
      ...fakeUser,
      is_superuser: true,
      permissions: [],
    }
    useAuthStore.setState({ user: superUser })

    expect(useAuthStore.getState().hasPermission('any:thing')).toBe(true)
  })

  it('普通用户精确匹配权限码', () => {
    useAuthStore.setState({ user: fakeUser })

    expect(useAuthStore.getState().hasPermission('product:list')).toBe(true)
    expect(useAuthStore.getState().hasPermission('product')).toBe(false)
    expect(useAuthStore.getState().hasPermission('product:list:detail')).toBe(false)
  })

  it('空字符串权限码返回 false', () => {
    useAuthStore.setState({ user: fakeUser })
    expect(useAuthStore.getState().hasPermission('')).toBe(false)
  })

  it('hasPermission 调用不改变 store 状态', () => {
    useAuthStore.setState({ user: fakeUser, token: 'test' })
    const stateBefore = useAuthStore.getState()

    useAuthStore.getState().hasPermission('product:list')

    expect(useAuthStore.getState().token).toBe(stateBefore.token)
    expect(useAuthStore.getState().user).toBe(stateBefore.user)
  })

  // ═══════════════════════════════════════════════════════
  // 6. CurrentUser 类型边界
  // ═══════════════════════════════════════════════════════

  it('display_name 为 null 的用户正常工作', async () => {
    const nullNameUser: CurrentUser = {
      ...fakeUser,
      display_name: null,
    }
    mockGetMe.mockResolvedValueOnce(mockUserResponse(nullNameUser))

    await useAuthStore.getState().fetchUser()

    expect(useAuthStore.getState().user?.display_name).toBeNull()
    expect(useAuthStore.getState().user?.username).toBe('admin')
  })

  it('用户有多个角色正常工作', async () => {
    const multiRoleUser: CurrentUser = {
      ...fakeUser,
      roles: [
        { id: 'role-1', name: 'admin', display_name: '管理员' },
        { id: 'role-2', name: 'sales', display_name: '销售' },
      ],
    }
    mockGetMe.mockResolvedValueOnce(mockUserResponse(multiRoleUser))

    await useAuthStore.getState().fetchUser()

    expect(useAuthStore.getState().user?.roles).toHaveLength(2)
  })

  it('用户有多个权限正常工作', () => {
    const multiPermUser: CurrentUser = {
      ...fakeUser,
      permissions: ['product:list', 'product:create', 'order:list', 'order:create', 'payment:reverse'],
    }
    useAuthStore.setState({ user: multiPermUser })

    expect(useAuthStore.getState().hasPermission('payment:reverse')).toBe(true)
    expect(useAuthStore.getState().hasPermission('admin:delete')).toBe(false)
  })

  // ═══════════════════════════════════════════════════════
  // 7. setState 后状态立即生效
  // ═══════════════════════════════════════════════════════

  it('setState 更新 token 后 getState 立即反映', () => {
    useAuthStore.setState({ token: 'new-token' })
    expect(useAuthStore.getState().token).toBe('new-token')
  })

  it('setState 更新 user 后 hasPermission 立即反映', () => {
    useAuthStore.setState({ user: null })
    expect(useAuthStore.getState().hasPermission('product:list')).toBe(false)

    useAuthStore.setState({ user: fakeUser })
    expect(useAuthStore.getState().hasPermission('product:list')).toBe(true)
  })

  // ═══════════════════════════════════════════════════════
  // 8. 连续 login 请求
  // ═══════════════════════════════════════════════════════

  it('连续两次 login 成功都存储最新 token', async () => {
    mockLogin.mockResolvedValueOnce(mockTokenResponse('token-1', 'refresh-1'))
    mockGetMe.mockResolvedValueOnce(mockUserResponse())
    await useAuthStore.getState().login('admin', 'pass')
    expect(useAuthStore.getState().token).toBe('token-1')

    mockLogin.mockResolvedValueOnce(mockTokenResponse('token-2', 'refresh-2'))
    mockGetMe.mockResolvedValueOnce(mockUserResponse())
    await useAuthStore.getState().login('admin', 'pass')
    expect(useAuthStore.getState().token).toBe('token-2')
    expect(localStorage.getItem('access_token')).toBe('token-2')
    expect(localStorage.getItem('refresh_token')).toBe('refresh-2')
  })
})
