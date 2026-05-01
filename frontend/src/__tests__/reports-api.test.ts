import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchSalesSummary, fetchSalesTrend, fetchProductRanking, fetchInventoryWarning,
  fetchCustomerRanking, fetchSalespersonRanking,
} from '@/api/reports'

vi.mock('@/api/request', () => ({
  get: vi.fn(),
}))

import { get } from '@/api/request'

const mockGet = get as ReturnType<typeof vi.fn>

const ok = (data: unknown) => Promise.resolve({ success: true, data, message: 'ok' })

describe('报表 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchSalesSummary 调用 GET /reports/sales-summary', async () => {
    mockGet.mockResolvedValueOnce(ok({ total_amount: '10000', order_count: 5 }))
    await fetchSalesSummary('7d')
    expect(mockGet).toHaveBeenCalledWith('/reports/sales-summary', { period: '7d' })
  })

  it('fetchSalesSummary 无参数时 period 为 undefined', async () => {
    mockGet.mockResolvedValueOnce(ok({ total_amount: '0', order_count: 0 }))
    await fetchSalesSummary()
    expect(mockGet).toHaveBeenCalledWith('/reports/sales-summary', { period: undefined })
  })

  it('fetchSalesTrend 调用 GET /reports/sales-trend', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [{ date: '2026-04-30', amount: '500', order_count: 1 }], period: '7d' }))
    const res = await fetchSalesTrend('7d')
    expect(mockGet).toHaveBeenCalledWith('/reports/sales-trend', { period: '7d' })
    expect(res.data.items).toHaveLength(1)
  })

  it('fetchProductRanking 调用 GET /reports/product-ranking', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], period: '30d' }))
    await fetchProductRanking({ period: '30d', limit: 10 })
    expect(mockGet).toHaveBeenCalledWith('/reports/product-ranking', { period: '30d', limit: 10 })
  })

  it('fetchInventoryWarning 调用 GET /reports/inventory-warning', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], threshold: 10, total: 0 }))
    await fetchInventoryWarning(10)
    expect(mockGet).toHaveBeenCalledWith('/reports/inventory-warning', { threshold: 10 })
  })

  it('fetchInventoryWarning 无阈值时不传参数', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], threshold: 10, total: 0 }))
    await fetchInventoryWarning()
    expect(mockGet).toHaveBeenCalledWith('/reports/inventory-warning', {})
  })

  it('fetchCustomerRanking 调用 GET /reports/customer-ranking', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], period: '30d' }))
    await fetchCustomerRanking({ period: '30d', limit: 5 })
    expect(mockGet).toHaveBeenCalledWith('/reports/customer-ranking', { period: '30d', limit: 5 })
  })

  it('fetchSalespersonRanking 调用 GET /reports/salesperson-ranking', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], period: '7d' }))
    await fetchSalespersonRanking({ period: '7d' })
    expect(mockGet).toHaveBeenCalledWith('/reports/salesperson-ranking', { period: '7d' })
  })
})
