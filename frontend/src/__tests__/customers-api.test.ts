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

  it('updateCustomer 调用 PUT /customers/:id', async () => {
    mockPut.mockResolvedValueOnce(ok({ id: 'c1', name: '王五' }))
    await updateCustomer('c1', { name: '王五' })
    expect(mockPut).toHaveBeenCalledWith('/customers/c1', { name: '王五' })
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
})
