import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchPayments, createPayment, reversePayment } from '@/api/payments'

vi.mock('@/api/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
}))

import { get, post } from '@/api/request'

const mockGet = get as ReturnType<typeof vi.fn>
const mockPost = post as ReturnType<typeof vi.fn>

const ok = (data: unknown) => Promise.resolve({ success: true, data, message: 'ok' })

describe('收款 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchPayments 调用 GET /payments', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchPayments({ page: 1 })
    expect(mockGet).toHaveBeenCalledWith('/payments', { page: 1 })
  })

  it('fetchPayments 按 order_id 筛选', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchPayments({ order_id: 'o1' })
    expect(mockGet).toHaveBeenCalledWith('/payments', { order_id: 'o1' })
  })

  it('createPayment 调用 POST /sales-orders/:id/payments', async () => {
    mockPost.mockResolvedValueOnce(ok({
      id: 'pay1', order_id: 'o1',
      amount: '100', payment_method: 'cash', order_status: 'confirmed',
    }))
    const res = await createPayment('o1', { amount: '100', payment_method: 'cash' })
    expect(mockPost).toHaveBeenCalledWith('/sales-orders/o1/payments', {
      amount: '100', payment_method: 'cash',
    })
    expect(res.data.order_status).toBe('confirmed')
  })

  it('createPayment 支持备注', async () => {
    mockPost.mockResolvedValueOnce(ok({
      id: 'pay2', order_id: 'o1',
      amount: '200', payment_method: 'bank_transfer', order_status: 'completed',
    }))
    await createPayment('o1', { amount: '200', payment_method: 'bank_transfer', remark: '尾款' })
    expect(mockPost).toHaveBeenCalledWith('/sales-orders/o1/payments', {
      amount: '200', payment_method: 'bank_transfer', remark: '尾款',
    })
  })

  it('reversePayment 调用 POST /payments/:id/reverse', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'pay1', status: 'reversed' }))
    const res = await reversePayment('pay1')
    expect(mockPost).toHaveBeenCalledWith('/payments/pay1/reverse')
    expect(res.data.status).toBe('reversed')
  })
})
