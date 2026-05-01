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
})
