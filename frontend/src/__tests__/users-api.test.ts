import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchUsers, createUser, updateUser, fetchRoles } from '@/api/users'

vi.mock('@/api/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
}))

import { get, post, put } from '@/api/request'

const mockGet = get as ReturnType<typeof vi.fn>
const mockPost = post as ReturnType<typeof vi.fn>
const mockPut = put as ReturnType<typeof vi.fn>

const ok = (data: unknown) => Promise.resolve({ success: true, data, message: 'ok' })

describe('用户 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchUsers 调用 GET /users', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchUsers({ page: 1 })
    expect(mockGet).toHaveBeenCalledWith('/users', { page: 1 })
  })

  it('fetchUsers 支持关键词搜索', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchUsers({ keyword: 'admin' })
    expect(mockGet).toHaveBeenCalledWith('/users', { keyword: 'admin' })
  })

  it('createUser 调用 POST /users', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'u1', username: 'newuser' }))
    const res = await createUser({
      username: 'newuser',
      password: 'password123',
      display_name: '新用户',
      role_ids: ['r1'],
    })
    expect(mockPost).toHaveBeenCalledWith('/users', {
      username: 'newuser',
      password: 'password123',
      display_name: '新用户',
      role_ids: ['r1'],
    })
    expect(res.data.username).toBe('newuser')
  })

  it('updateUser 调用 PUT /users/:id', async () => {
    mockPut.mockResolvedValueOnce(ok(null))
    await updateUser('u1', { display_name: '修改后', is_active: false })
    expect(mockPut).toHaveBeenCalledWith('/users/u1', {
      display_name: '修改后',
      is_active: false,
    })
  })

  it('fetchRoles 调用 GET /users/roles', async () => {
    mockGet.mockResolvedValueOnce(ok([
      { id: 'r1', name: 'admin', display_name: '管理员' },
      { id: 'r2', name: 'sales', display_name: '销售' },
    ]))
    const res = await fetchRoles()
    expect(mockGet).toHaveBeenCalledWith('/users/roles')
    expect(res.data).toHaveLength(2)
    expect(res.data[0].name).toBe('admin')
  })
})
