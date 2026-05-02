import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchCustomers, fetchCustomer, createCustomer,
  updateCustomer, deleteCustomer, transferCustomer,
} from '@/api/customers'

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

describe('客户 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchCustomers 调用 GET /customers', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchCustomers({ page: 1, keyword: '张' })
    expect(mockGet).toHaveBeenCalledWith('/customers', { page: 1, keyword: '张' })
  })

  it('fetchCustomers 无参数时传 undefined', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchCustomers()
    expect(mockGet).toHaveBeenCalledWith('/customers', undefined)
  })

  it('fetchCustomers 返回完整客户数据', async () => {
    const items = [{
      id: 'c1', name: '张三', contact_name: '张经理',
      phone: '13800001111', email: 'zhang@test.com',
      source: 'referral', level: 'vip', owner_user_id: 'u1',
      follow_status: 'active', remark: '重要客户',
      created_at: '2026-05-01T10:00:00Z', updated_at: null,
    }]
    mockGet.mockResolvedValueOnce(ok({ items, page: 1, page_size: 20, total: 1 }))
    const res = await fetchCustomers({ page: 1 })
    expect(res.data.items[0].source).toBe('referral')
    expect(res.data.items[0].level).toBe('vip')
  })

  it('fetchCustomer 调用 GET /customers/:id', async () => {
    mockGet.mockResolvedValueOnce(ok({ id: 'c1', name: '张三' }))
    const res = await fetchCustomer('c1')
    expect(mockGet).toHaveBeenCalledWith('/customers/c1')
    expect(res.data.name).toBe('张三')
  })

  it('createCustomer 调用 POST /customers', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'c2', name: '李四' }))
    await createCustomer({ name: '李四', phone: '13800001111' })
    expect(mockPost).toHaveBeenCalledWith('/customers', { name: '李四', phone: '13800001111' })
  })

  it('createCustomer 含可选字段', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'c3', name: '王五' }))
    await createCustomer({
      name: '王五', phone: '13900002222', email: 'wang@test.com',
      source: 'website', level: 'normal', remark: '线上咨询',
    })
    expect(mockPost).toHaveBeenCalledWith('/customers', {
      name: '王五', phone: '13900002222', email: 'wang@test.com',
      source: 'website', level: 'normal', remark: '线上咨询',
    })
  })

  it('updateCustomer 调用 PUT /customers/:id', async () => {
    mockPut.mockResolvedValueOnce(ok({ id: 'c1', name: '王五' }))
    await updateCustomer('c1', { name: '王五' })
    expect(mockPut).toHaveBeenCalledWith('/customers/c1', { name: '王五' })
  })

  it('updateCustomer 更新联系方式', async () => {
    mockPut.mockResolvedValueOnce(ok({ id: 'c1' }))
    await updateCustomer('c1', { phone: '13900009999', email: 'new@test.com' })
    expect(mockPut).toHaveBeenCalledWith('/customers/c1', { phone: '13900009999', email: 'new@test.com' })
  })

  it('deleteCustomer 调用 DELETE /customers/:id', async () => {
    mockDel.mockResolvedValueOnce(ok(null))
    await deleteCustomer('c1')
    expect(mockDel).toHaveBeenCalledWith('/customers/c1')
  })

  it('transferCustomer 调用 POST /customers/:id/transfer', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'c1', owner_user_id: 'u2' }))
    await transferCustomer('c1', 'u2')
    expect(mockPost).toHaveBeenCalledWith('/customers/c1/transfer', { owner_user_id: 'u2' })
  })

  it('transferCustomer 不同目标用户', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'c2', owner_user_id: 'u3' }))
    const res = await transferCustomer('c2', 'u3')
    expect(mockPost).toHaveBeenCalledWith('/customers/c2/transfer', { owner_user_id: 'u3' })
    expect(res.data.owner_user_id).toBe('u3')
  })
})
