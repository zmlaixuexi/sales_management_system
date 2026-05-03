import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchRoles,
  fetchPermissions,
  createRole,
  updateRole,
  deleteRole,
} from '@/api/roles'

vi.mock('@/api/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
}))

import { get, post, put, del } from '@/api/request'

const mockGet = get as ReturnType<typeof vi.fn>
const mockPost = post as ReturnType<typeof vi.fn>
const mockPut = put as ReturnType<typeof vi.fn>
const mockDel = del as ReturnType<typeof vi.fn>

const ok = (data: unknown) => Promise.resolve({ success: true, data, message: 'ok' })

describe('角色 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchRoles 调用 GET /roles', async () => {
    const roles = [
      { id: 'r1', name: 'admin', display_name: '管理员', description: null, permissions: [], user_count: 1, created_at: null, updated_at: null },
    ]
    mockGet.mockResolvedValueOnce(ok(roles))
    const res = await fetchRoles()
    expect(mockGet).toHaveBeenCalledWith('/roles')
    expect(res.data).toHaveLength(1)
    expect(res.data[0].name).toBe('admin')
  })

  it('fetchPermissions 调用 GET /roles/permissions', async () => {
    const perms = {
      '用户管理': [{ id: 'p1', code: 'user:read', name: '查看用户', module: '用户管理' }],
    }
    mockGet.mockResolvedValueOnce(ok(perms))
    const res = await fetchPermissions()
    expect(mockGet).toHaveBeenCalledWith('/roles/permissions')
    expect(res.data['用户管理']).toHaveLength(1)
  })

  it('createRole 调用 POST /roles', async () => {
    const created = { id: 'r2', name: 'sales', display_name: '销售', description: null, permissions: [], user_count: 0, created_at: '2026-05-01', updated_at: null }
    mockPost.mockResolvedValueOnce(ok(created))
    const res = await createRole({ name: 'sales', display_name: '销售', permission_ids: ['p1'] })
    expect(mockPost).toHaveBeenCalledWith('/roles', { name: 'sales', display_name: '销售', permission_ids: ['p1'] })
    expect(res.data.name).toBe('sales')
  })

  it('createRole 最少参数', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'r3', name: 'test', display_name: null, description: null, permissions: [], user_count: 0, created_at: null, updated_at: null }))
    await createRole({ name: 'test' })
    expect(mockPost).toHaveBeenCalledWith('/roles', { name: 'test' })
  })

  it('updateRole 调用 PUT /roles/:id', async () => {
    mockPut.mockResolvedValueOnce(ok(null))
    await updateRole('r1', { display_name: '超级管理员', permission_ids: ['p1', 'p2'] })
    expect(mockPut).toHaveBeenCalledWith('/roles/r1', { display_name: '超级管理员', permission_ids: ['p1', 'p2'] })
  })

  it('updateRole 仅更新描述', async () => {
    mockPut.mockResolvedValueOnce(ok(null))
    await updateRole('r1', { description: '新描述' })
    expect(mockPut).toHaveBeenCalledWith('/roles/r1', { description: '新描述' })
  })

  it('deleteRole 调用 DELETE /roles/:id', async () => {
    mockDel.mockResolvedValueOnce(ok(null))
    await deleteRole('r1')
    expect(mockDel).toHaveBeenCalledWith('/roles/r1')
  })
})
