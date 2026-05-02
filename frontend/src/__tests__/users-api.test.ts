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

  it('fetchUsers 支持分页', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 2, page_size: 10, total: 15 }))
    const res = await fetchUsers({ page: 2, page_size: 10 })
    expect(mockGet).toHaveBeenCalledWith('/users', { page: 2, page_size: 10 })
    expect(res.data.total).toBe(15)
  })

  it('fetchUsers 返回完整用户数据', async () => {
    const items = [{
      id: 'u1', username: 'admin', display_name: '管理员',
      phone: '13800000000', email: 'admin@test.com',
      is_active: true, is_superuser: false,
      roles: [{ id: 'r1', name: 'admin', display_name: '管理员' }],
      created_at: '2026-05-01T10:00:00Z', updated_at: '2026-05-01T10:00:00Z',
    }]
    mockGet.mockResolvedValueOnce(ok({ items, page: 1, page_size: 20, total: 1 }))
    const res = await fetchUsers({ page: 1 })
    expect(res.data.items).toHaveLength(1)
    expect(res.data.items[0].username).toBe('admin')
    expect(res.data.items[0].roles[0].name).toBe('admin')
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

  it('createUser 最少参数', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'u2', username: 'min' }))
    await createUser({ username: 'min', password: 'pass123' })
    expect(mockPost).toHaveBeenCalledWith('/users', {
      username: 'min', password: 'pass123',
    })
  })

  it('createUser 含手机和邮箱', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'u3', username: 'full' }))
    await createUser({
      username: 'full', password: 'pass123',
      phone: '13900000000', email: 'full@test.com',
    })
    expect(mockPost).toHaveBeenCalledWith('/users', {
      username: 'full', password: 'pass123',
      phone: '13900000000', email: 'full@test.com',
    })
  })

  it('updateUser 调用 PUT /users/:id', async () => {
    mockPut.mockResolvedValueOnce(ok(null))
    await updateUser('u1', { display_name: '修改后', is_active: false })
    expect(mockPut).toHaveBeenCalledWith('/users/u1', {
      display_name: '修改后',
      is_active: false,
    })
  })

  it('updateUser 更新角色', async () => {
    mockPut.mockResolvedValueOnce(ok(null))
    await updateUser('u1', { role_ids: ['r1', 'r2'] })
    expect(mockPut).toHaveBeenCalledWith('/users/u1', { role_ids: ['r1', 'r2'] })
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
