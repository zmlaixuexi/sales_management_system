import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchOrders, fetchOrder, createOrder,
  updateOrder, confirmOrder, cancelOrder,
} from '@/api/orders'

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

describe('订单 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchOrders 调用 GET /sales-orders', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchOrders({ status: 'draft' })
    expect(mockGet).toHaveBeenCalledWith('/sales-orders', { status: 'draft' })
  })

  it('fetchOrder 调用 GET /sales-orders/:id', async () => {
    mockGet.mockResolvedValueOnce(ok({ id: 'o1', order_no: 'ORD-001', items: [], payments: [] }))
    const res = await fetchOrder('o1')
    expect(mockGet).toHaveBeenCalledWith('/sales-orders/o1')
    expect(res.data.order_no).toBe('ORD-001')
  })

  it('createOrder 调用 POST /sales-orders', async () => {
    const payload = { customer_id: 'c1', items: [{ product_id: 'p1', quantity: 2 }] }
    mockPost.mockResolvedValueOnce(ok({ id: 'o2', order_no: 'ORD-002' }))
    await createOrder(payload)
    expect(mockPost).toHaveBeenCalledWith('/sales-orders', payload)
  })

  it('updateOrder 调用 PUT /sales-orders/:id', async () => {
    mockPut.mockResolvedValueOnce(ok({ id: 'o1', order_no: 'ORD-001' }))
    await updateOrder('o1', { remark: '备注' })
    expect(mockPut).toHaveBeenCalledWith('/sales-orders/o1', { remark: '备注' })
  })

  it('confirmOrder 调用 POST /sales-orders/:id/confirm', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'o1', status: 'confirmed' }))
    const res = await confirmOrder('o1')
    expect(mockPost).toHaveBeenCalledWith('/sales-orders/o1/confirm')
    expect(res.data.status).toBe('confirmed')
  })

  it('cancelOrder 调用 POST /sales-orders/:id/cancel', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'o1', status: 'cancelled' }))
    const res = await cancelOrder('o1')
    expect(mockPost).toHaveBeenCalledWith('/sales-orders/o1/cancel')
    expect(res.data.status).toBe('cancelled')
  })
})
