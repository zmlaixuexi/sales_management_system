import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchAuditLogs, fetchAuditActions } from '@/api/auditLogs'

vi.mock('@/api/request', () => ({
  get: vi.fn(),
}))

import { get } from '@/api/request'

const mockGet = get as ReturnType<typeof vi.fn>

const apiOk = (data: unknown) =>
  Promise.resolve({ success: true, data, message: 'ok' })

describe('审计日志 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchAuditLogs 调用 GET /audit-logs', async () => {
    mockGet.mockResolvedValueOnce(apiOk({
      items: [], page: 1, page_size: 20, total: 0,
    }))
    const data = await fetchAuditLogs({})
    expect(mockGet).toHaveBeenCalledWith('/audit-logs', {})
    expect(data.total).toBe(0)
  })

  it('fetchAuditLogs 传递筛选参数', async () => {
    mockGet.mockResolvedValueOnce(apiOk({
      items: [], page: 1, page_size: 20, total: 0,
    }))
    await fetchAuditLogs({ action: 'product_create', resource_type: 'product', page: 2 })
    expect(mockGet).toHaveBeenCalledWith('/audit-logs', {
      action: 'product_create', resource_type: 'product', page: 2,
    })
  })

  it('fetchAuditLogs 传递日期范围', async () => {
    mockGet.mockResolvedValueOnce(apiOk({
      items: [], page: 1, page_size: 20, total: 0,
    }))
    await fetchAuditLogs({ start_date: '2026-04-01', end_date: '2026-04-30' })
    expect(mockGet).toHaveBeenCalledWith('/audit-logs', {
      start_date: '2026-04-01', end_date: '2026-04-30',
    })
  })

  it('fetchAuditLogs 返回解析后的数据', async () => {
    const items = [{
      id: '1', actor_name: '管理员', action: 'login_success',
      resource_type: 'user', after_data: { name: 'test' },
    }]
    mockGet.mockResolvedValueOnce(apiOk({ items, page: 1, page_size: 20, total: 1 }))
    const data = await fetchAuditLogs({})
    expect(data.total).toBe(1)
    expect(data.items[0].action).toBe('login_success')
  })

  it('fetchAuditLogs 按 actor_id 筛选', async () => {
    mockGet.mockResolvedValueOnce(apiOk({
      items: [], page: 1, page_size: 20, total: 0,
    }))
    await fetchAuditLogs({ actor_id: 'user-uuid-123' })
    expect(mockGet).toHaveBeenCalledWith('/audit-logs', {
      actor_id: 'user-uuid-123',
    })
  })

  it('fetchAuditLogs 返回完整审计条目含请求元数据', async () => {
    const items = [{
      id: 'a1', actor_id: 'u1', actor_name: '管理员',
      action: 'order_create', resource_type: 'sales_order', resource_id: 'o1',
      before_data: null, after_data: { order_no: 'ORD-001' },
      ip_address: '192.168.1.100', user_agent: 'Mozilla/5.0',
      request_id: 'req-abc', created_at: '2026-05-01T10:00:00Z',
    }]
    mockGet.mockResolvedValueOnce(apiOk({ items, page: 1, page_size: 20, total: 1 }))
    const data = await fetchAuditLogs({})
    expect(data.items[0].ip_address).toBe('192.168.1.100')
    expect(data.items[0].request_id).toBe('req-abc')
    expect(data.items[0].after_data.order_no).toBe('ORD-001')
  })

  it('fetchAuditLogs 支持分页', async () => {
    mockGet.mockResolvedValueOnce(apiOk({
      items: [], page: 5, page_size: 10, total: 50,
    }))
    const data = await fetchAuditLogs({ page: 5, page_size: 10 })
    expect(mockGet).toHaveBeenCalledWith('/audit-logs', { page: 5, page_size: 10 })
    expect(data.total).toBe(50)
  })

  it('fetchAuditLogs 按关键词搜索', async () => {
    mockGet.mockResolvedValueOnce(apiOk({
      items: [], page: 1, page_size: 20, total: 0,
    }))
    await fetchAuditLogs({ keyword: '管理员' })
    expect(mockGet).toHaveBeenCalledWith('/audit-logs', { keyword: '管理员' })
  })

  it('fetchAuditActions 调用 GET /audit-logs/actions', async () => {
    mockGet.mockResolvedValueOnce(apiOk({
      actions: ['login_success', 'product_create'],
      resource_types: ['user', 'product'],
    }))
    const data = await fetchAuditActions()
    expect(mockGet).toHaveBeenCalledWith('/audit-logs/actions')
    expect(data.actions).toContain('product_create')
    expect(data.resource_types).toContain('user')
  })

  it('fetchAuditActions 返回空列表', async () => {
    mockGet.mockResolvedValueOnce(apiOk({ actions: [], resource_types: [] }))
    const data = await fetchAuditActions()
    expect(data.actions).toHaveLength(0)
    expect(data.resource_types).toHaveLength(0)
  })
})
