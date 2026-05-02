import { describe, it, expect, vi, beforeEach } from 'vitest'

// mock apiClient
const mockGet = vi.fn()
vi.mock('@/api/client', () => ({
  default: { get: (...args: unknown[]) => mockGet(...args) },
}))

// mock URL.createObjectURL / revokeObjectURL
vi.stubGlobal('URL', {
  ...URL,
  createObjectURL: vi.fn(() => 'blob:mock-url'),
  revokeObjectURL: vi.fn(),
})

import { downloadCsv } from '../api/request'

describe('downloadCsv', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const mockAnchor = { href: '', download: '', click: vi.fn() }
    vi.spyOn(document, 'createElement').mockReturnValue(mockAnchor as unknown as HTMLAnchorElement)
  })

  it('成功下载 CSV 文件', async () => {
    const blob = new Blob(['csv data'], { type: 'text/csv' })
    mockGet.mockResolvedValueOnce({
      data: blob,
      headers: { 'content-disposition': 'filename=products.csv' },
    })

    await downloadCsv('/exports/products')

    expect(mockGet).toHaveBeenCalledWith('/exports/products', {
      params: {},
      responseType: 'blob',
    })
  })

  it('传递查询参数', async () => {
    mockGet.mockResolvedValueOnce({
      data: new Blob(),
      headers: {},
    })

    await downloadCsv('/exports/orders', { status: 'confirmed' })

    expect(mockGet).toHaveBeenCalledWith('/exports/orders', {
      params: { status: 'confirmed' },
      responseType: 'blob',
    })
  })

  it('忽略 undefined 和空字符串参数', async () => {
    mockGet.mockResolvedValueOnce({
      data: new Blob(),
      headers: {},
    })

    await downloadCsv('/exports/products', { keyword: undefined, status: '' })

    expect(mockGet).toHaveBeenCalledWith('/exports/products', {
      params: {},
      responseType: 'blob',
    })
  })

  it('响应失败时由拦截器处理错误', async () => {
    mockGet.mockRejectedValueOnce(new Error('Request failed'))

    await expect(downloadCsv('/exports/products')).rejects.toThrow()
  })

  it('从 Content-Disposition 提取文件名', async () => {
    mockGet.mockResolvedValueOnce({
      data: new Blob(),
      headers: { 'content-disposition': 'filename=customers_export.csv' },
    })

    await downloadCsv('/exports/customers')

    const anchor = document.createElement('a') as unknown as { download: string }
    expect(anchor.download).toBe('customers_export.csv')
  })

  it('无 Content-Disposition 时使用默认文件名', async () => {
    mockGet.mockResolvedValueOnce({
      data: new Blob(),
      headers: {},
    })

    await downloadCsv('/exports/orders')

    const anchor = document.createElement('a') as unknown as { download: string }
    expect(anchor.download).toBe('export.csv')
  })

  it('Content-Disposition 带 attachment 前缀时正确提取文件名', async () => {
    mockGet.mockResolvedValueOnce({
      data: new Blob(),
      headers: { 'content-disposition': 'attachment; filename=orders_20260502.csv' },
    })

    await downloadCsv('/exports/orders')

    const anchor = document.createElement('a') as unknown as { download: string }
    expect(anchor.download).toBe('orders_20260502.csv')
  })

  it('多个参数中过滤 undefined/null/空字符串后无参数仍正常请求', async () => {
    mockGet.mockResolvedValueOnce({
      data: new Blob(),
      headers: {},
    })

    await downloadCsv('/exports/products', { keyword: undefined, status: undefined, category_id: undefined })

    expect(mockGet).toHaveBeenCalledWith('/exports/products', {
      params: {},
      responseType: 'blob',
    })
  })

  it('所有有效参数均传递', async () => {
    mockGet.mockResolvedValueOnce({
      data: new Blob(),
      headers: {},
    })

    await downloadCsv('/exports/products', { keyword: '手机', status: 'active', category_id: 'cat-1' })

    expect(mockGet).toHaveBeenCalledWith('/exports/products', {
      params: { keyword: '手机', status: 'active', category_id: 'cat-1' },
      responseType: 'blob',
    })
  })

  it('blob 为 JSON 错误响应时抛出后端错误消息', async () => {
    const errorJson = JSON.stringify({ success: false, error: { code: 'AUTH_FORBIDDEN', message: '无导出权限' } })
    const blob = new Blob([errorJson], { type: 'application/json' })
    mockGet.mockResolvedValueOnce({
      data: blob,
      headers: {},
    })

    await expect(downloadCsv('/exports/products')).rejects.toThrow('无导出权限')
  })

  it('blob 为 JSON 但无 error.message 时使用默认消息', async () => {
    const errorJson = JSON.stringify({ success: false })
    const blob = new Blob([errorJson], { type: 'application/json' })
    mockGet.mockResolvedValueOnce({
      data: blob,
      headers: {},
    })

    await expect(downloadCsv('/exports/products')).rejects.toThrow('导出失败')
  })
})
