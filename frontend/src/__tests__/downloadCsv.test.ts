import { describe, it, expect, vi, beforeEach } from 'vitest'
import { downloadCsv } from '../utils'

// mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// mock URL.createObjectURL / revokeObjectURL
vi.stubGlobal('URL', {
  ...URL,
  createObjectURL: vi.fn(() => 'blob:mock-url'),
  revokeObjectURL: vi.fn(),
})

describe('downloadCsv', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    // mock createElement to track <a> click
    const mockAnchor = { href: '', download: '', click: vi.fn() }
    vi.spyOn(document, 'createElement').mockReturnValue(mockAnchor as unknown as HTMLAnchorElement)
  })

  it('成功下载 CSV 文件', async () => {
    localStorage.setItem('access_token', 'test-token')
    const blob = new Blob(['csv data'], { type: 'text/csv' })
    mockFetch.mockResolvedValueOnce({
      ok: true,
      blob: () => Promise.resolve(blob),
      headers: new Headers({ 'Content-Disposition': 'filename=products.csv' }),
    })

    await downloadCsv('/exports/products')

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/exports/products'),
      expect.objectContaining({
        headers: { Authorization: 'Bearer test-token' },
      }),
    )
  })

  it('传递查询参数', async () => {
    localStorage.setItem('access_token', 'tok')
    mockFetch.mockResolvedValueOnce({
      ok: true,
      blob: () => Promise.resolve(new Blob()),
      headers: new Headers(),
    })

    await downloadCsv('/exports/orders', { status: 'confirmed' })

    const calledUrl = mockFetch.mock.calls[0][0] as string
    expect(calledUrl).toContain('status=confirmed')
  })

  it('忽略 undefined 和空字符串参数', async () => {
    localStorage.setItem('access_token', 'tok')
    mockFetch.mockResolvedValueOnce({
      ok: true,
      blob: () => Promise.resolve(new Blob()),
      headers: new Headers(),
    })

    await downloadCsv('/exports/products', { keyword: undefined, status: '' })

    const calledUrl = mockFetch.mock.calls[0][0] as string
    expect(calledUrl).not.toContain('keyword')
    expect(calledUrl).not.toContain('status')
  })

  it('响应失败时抛出错误', async () => {
    localStorage.setItem('access_token', 'tok')
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401 })

    await expect(downloadCsv('/exports/products')).rejects.toThrow('导出失败')
  })

  it('从 Content-Disposition 提取文件名', async () => {
    localStorage.setItem('access_token', 'tok')
    mockFetch.mockResolvedValueOnce({
      ok: true,
      blob: () => Promise.resolve(new Blob()),
      headers: new Headers({ 'Content-Disposition': 'filename=customers_export.csv' }),
    })

    await downloadCsv('/exports/customers')

    const anchor = document.createElement('a') as unknown as { download: string }
    expect(anchor.download).toBe('customers_export.csv')
  })

  it('无 Content-Disposition 时使用默认文件名', async () => {
    localStorage.setItem('access_token', 'tok')
    mockFetch.mockResolvedValueOnce({
      ok: true,
      blob: () => Promise.resolve(new Blob()),
      headers: new Headers(),
    })

    await downloadCsv('/exports/orders')

    const anchor = document.createElement('a') as unknown as { download: string }
    expect(anchor.download).toBe('export.csv')
  })
})
