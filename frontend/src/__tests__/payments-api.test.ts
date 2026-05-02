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

  it('fetchPayments 支持分页参数', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 2, page_size: 10, total: 15 }))
    const res = await fetchPayments({ page: 2, page_size: 10 })
    expect(mockGet).toHaveBeenCalledWith('/payments', { page: 2, page_size: 10 })
    expect(res.data.total).toBe(15)
  })

  it('fetchPayments 返回完整收款记录', async () => {
    const items = [{
      id: 'pay1', order_id: 'o1', amount: '500.00',
      payment_method: 'cash', status: 'completed',
      remark: '全额付款', paid_at: '2026-05-01T10:00:00Z',
      created_at: '2026-05-01T10:00:00Z',
    }]
    mockGet.mockResolvedValueOnce(ok({ items, page: 1, page_size: 20, total: 1 }))
    const res = await fetchPayments({ page: 1 })
    expect(res.data.items).toHaveLength(1)
    expect(res.data.items[0].payment_method).toBe('cash')
    expect(res.data.items[0].amount).toBe('500.00')
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
      amount: '200', payment_method: 'transfer', order_status: 'completed',
    }))
    await createPayment('o1', { amount: '200', payment_method: 'transfer', remark: '尾款' })
    expect(mockPost).toHaveBeenCalledWith('/sales-orders/o1/payments', {
      amount: '200', payment_method: 'transfer', remark: '尾款',
    })
  })

  it('createPayment 微信支付方式', async () => {
    mockPost.mockResolvedValueOnce(ok({
      id: 'pay3', order_id: 'o2',
      amount: '300', payment_method: 'wechat', order_status: 'partially_paid',
    }))
    const res = await createPayment('o2', { amount: '300', payment_method: 'wechat' })
    expect(res.data.order_status).toBe('partially_paid')
  })

  it('createPayment 支付宝支付方式', async () => {
    mockPost.mockResolvedValueOnce(ok({
      id: 'pay4', order_id: 'o3',
      amount: '150', payment_method: 'alipay', order_status: 'confirmed',
    }))
    const res = await createPayment('o3', { amount: '150', payment_method: 'alipay' })
    expect(mockPost).toHaveBeenCalledWith('/sales-orders/o3/payments', {
      amount: '150', payment_method: 'alipay',
    })
    expect(res.data.payment_method).toBe('alipay')
  })

  it('reversePayment 调用 POST /payments/:id/reverse', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'pay1', status: 'reversed' }))
    const res = await reversePayment('pay1')
    expect(mockPost).toHaveBeenCalledWith('/payments/pay1/reverse')
    expect(res.data.status).toBe('reversed')
  })

  it('reversePayment 不同 ID', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'pay-uuid-999', status: 'reversed' }))
    const res = await reversePayment('pay-uuid-999')
    expect(mockPost).toHaveBeenCalledWith('/payments/pay-uuid-999/reverse')
    expect(res.data.id).toBe('pay-uuid-999')
  })
})
