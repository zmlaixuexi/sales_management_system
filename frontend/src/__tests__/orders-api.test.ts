import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchOrders, fetchOrder, createOrder,
  updateOrder, confirmOrder, cancelOrder, fetchOrderLogs,
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

  it('fetchOrders 按关键词搜索', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchOrders({ keyword: 'ORD-001' })
    expect(mockGet).toHaveBeenCalledWith('/sales-orders', { keyword: 'ORD-001' })
  })

  it('fetchOrders 按客户 ID 筛选', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchOrders({ customer_id: 'c1' })
    expect(mockGet).toHaveBeenCalledWith('/sales-orders', { customer_id: 'c1' })
  })

  it('fetchOrders 支持分页参数', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 3, page_size: 10, total: 25 }))
    const res = await fetchOrders({ page: 3, page_size: 10 })
    expect(mockGet).toHaveBeenCalledWith('/sales-orders', { page: 3, page_size: 10 })
    expect(res.data.page).toBe(3)
  })

  it('fetchOrders 无参数调用', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchOrders()
    expect(mockGet).toHaveBeenCalledWith('/sales-orders', undefined)
  })

  it('fetchOrder 调用 GET /sales-orders/:id', async () => {
    mockGet.mockResolvedValueOnce(ok({ id: 'o1', order_no: 'ORD-001', items: [], payments: [] }))
    const res = await fetchOrder('o1')
    expect(mockGet).toHaveBeenCalledWith('/sales-orders/o1')
    expect(res.data.order_no).toBe('ORD-001')
  })

  it('fetchOrder 返回完整订单含明细和收款', async () => {
    const detail = {
      id: 'o1', order_no: 'ORD-001', customer_id: 'c1', sales_user_id: 'u1',
      status: 'confirmed', status_label: '已确认', total_amount: '500.00',
      total_cost: '300.00', gross_profit: '200.00', gross_margin: '40.00',
      paid_amount: '0.00', remark: null, created_at: '2026-05-01T10:00:00Z',
      updated_at: '2026-05-01T10:00:00Z',
      items: [{
        id: 'i1', product_id: 'p1', product_sku_snapshot: 'SKU-001',
        product_name_snapshot: '测试商品', product_image_url_snapshot: null,
        quantity: 2, unit_price: '250.00', discount_amount: '0.00',
        discount_rate: '0.00', cost_price_snapshot: '150.00',
        subtotal_amount: '500.00', subtotal_cost: '300.00',
      }],
      payments: [{
        id: 'pay1', amount: '200.00', payment_method: 'cash',
        paid_at: '2026-05-01T11:00:00Z', remark: null, created_at: '2026-05-01T11:00:00Z',
      }],
    }
    mockGet.mockResolvedValueOnce(ok(detail))
    const res = await fetchOrder('o1')
    expect(res.data.items).toHaveLength(1)
    expect(res.data.items[0].product_name_snapshot).toBe('测试商品')
    expect(res.data.payments).toHaveLength(1)
    expect(res.data.payments[0].amount).toBe('200.00')
  })

  it('createOrder 调用 POST /sales-orders', async () => {
    const payload = { customer_id: 'c1', items: [{ product_id: 'p1', quantity: 2 }] }
    mockPost.mockResolvedValueOnce(ok({ id: 'o2', order_no: 'ORD-002' }))
    await createOrder(payload)
    expect(mockPost).toHaveBeenCalledWith('/sales-orders', payload)
  })

  it('createOrder 多商品明细', async () => {
    const payload = {
      customer_id: 'c1',
      items: [
        { product_id: 'p1', quantity: 2 },
        { product_id: 'p2', quantity: 1, unit_price: '99.00' },
      ],
      remark: '含折扣',
    }
    mockPost.mockResolvedValueOnce(ok({ id: 'o3', order_no: 'ORD-003' }))
    const res = await createOrder(payload)
    expect(mockPost).toHaveBeenCalledWith('/sales-orders', payload)
    expect(res.data.order_no).toBe('ORD-003')
  })

  it('updateOrder 调用 PUT /sales-orders/:id', async () => {
    mockPut.mockResolvedValueOnce(ok({ id: 'o1', order_no: 'ORD-001' }))
    await updateOrder('o1', { remark: '备注' })
    expect(mockPut).toHaveBeenCalledWith('/sales-orders/o1', { remark: '备注' })
  })

  it('updateOrder 更新明细', async () => {
    const items = [{ product_id: 'p1', quantity: 5, unit_price: '80.00' }]
    mockPut.mockResolvedValueOnce(ok({ id: 'o1', order_no: 'ORD-001' }))
    await updateOrder('o1', { items })
    expect(mockPut).toHaveBeenCalledWith('/sales-orders/o1', { items })
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

  it('fetchOrderLogs 调用 GET /sales-orders/:id/logs', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 10, total: 0 }))
    await fetchOrderLogs('o1')
    expect(mockGet).toHaveBeenCalledWith('/sales-orders/o1/logs', undefined)
  })

  it('fetchOrderLogs 支持分页参数', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 2, page_size: 5, total: 12 }))
    const res = await fetchOrderLogs('o1', { page: 2, page_size: 5 })
    expect(mockGet).toHaveBeenCalledWith('/sales-orders/o1/logs', { page: 2, page_size: 5 })
    expect(res.data.total).toBe(12)
  })
})
