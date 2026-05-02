import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchInventoryMovements, adjustInventory } from '@/api/inventory'

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

describe('库存 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchInventoryMovements 调用 GET /inventory/movements', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchInventoryMovements({ page: 1 })
    expect(mockGet).toHaveBeenCalledWith('/inventory/movements', { page: 1 })
  })

  it('fetchInventoryMovements 按 product_id 筛选', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchInventoryMovements({ product_id: 'p1' })
    expect(mockGet).toHaveBeenCalledWith('/inventory/movements', { product_id: 'p1' })
  })

  it('fetchInventoryMovements 按 movement_type 筛选', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchInventoryMovements({ movement_type: 'manual_adjust' })
    expect(mockGet).toHaveBeenCalledWith('/inventory/movements', { movement_type: 'manual_adjust' })
  })

  it('fetchInventoryMovements 支持分页', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 3, page_size: 10, total: 30 }))
    const res = await fetchInventoryMovements({ page: 3, page_size: 10 })
    expect(mockGet).toHaveBeenCalledWith('/inventory/movements', { page: 3, page_size: 10 })
    expect(res.data.page).toBe(3)
  })

  it('fetchInventoryMovements 返回完整流水记录', async () => {
    const items = [{
      id: 'm1', product_id: 'p1', movement_type: 'order_deduct',
      quantity_before: 100, quantity_change: -5, quantity_after: 95,
      related_type: 'sales_order', related_id: 'o1',
      remark: '订单确认扣减', created_at: '2026-05-01T10:00:00Z',
    }]
    mockGet.mockResolvedValueOnce(ok({ items, page: 1, page_size: 20, total: 1 }))
    const res = await fetchInventoryMovements({ page: 1 })
    expect(res.data.items).toHaveLength(1)
    expect(res.data.items[0].movement_type).toBe('order_deduct')
    expect(res.data.items[0].quantity_change).toBe(-5)
  })

  it('adjustInventory 调用 POST /inventory/adjustments', async () => {
    mockPost.mockResolvedValueOnce(ok({
      product_id: 'p1', quantity_before: 10, quantity_change: 5, quantity_after: 15,
    }))
    const res = await adjustInventory({ product_id: 'p1', quantity_change: 5 })
    expect(mockPost).toHaveBeenCalledWith('/inventory/adjustments', { product_id: 'p1', quantity_change: 5 })
    expect(res.data.quantity_after).toBe(15)
  })

  it('adjustInventory 带备注', async () => {
    mockPost.mockResolvedValueOnce(ok({
      product_id: 'p1', quantity_before: 10, quantity_change: -3, quantity_after: 7,
    }))
    await adjustInventory({ product_id: 'p1', quantity_change: -3, remark: '盘亏' })
    expect(mockPost).toHaveBeenCalledWith('/inventory/adjustments', {
      product_id: 'p1', quantity_change: -3, remark: '盘亏',
    })
  })

  it('adjustInventory 正数调整增加库存', async () => {
    mockPost.mockResolvedValueOnce(ok({
      product_id: 'p2', quantity_before: 20, quantity_change: 10, quantity_after: 30,
    }))
    const res = await adjustInventory({ product_id: 'p2', quantity_change: 10, remark: '采购入库' })
    expect(res.data.quantity_before).toBe(20)
    expect(res.data.quantity_after).toBe(30)
  })

  it('fetchInventoryMovements 无参数调用', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchInventoryMovements()
    expect(mockGet).toHaveBeenCalledWith('/inventory/movements', undefined)
  })
})
