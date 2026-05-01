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
})
