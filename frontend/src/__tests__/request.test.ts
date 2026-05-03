import { describe, it, expect, vi } from 'vitest'
import { get, post, put, del, upload, downloadCsv } from '@/api/request'

// 模拟 apiClient
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import apiClient from '@/api/client'

const mockClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  put: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}

describe('request 封装函数', () => {
  it('get 发起 GET 请求并返回 data', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: { success: true, data: { items: [] }, message: 'ok' },
    })
    const result = await get('/products', { page: 1 })
    expect(mockClient.get).toHaveBeenCalledWith('/products', { params: { page: 1 } })
    expect(result.success).toBe(true)
  })

  it('post 发起 POST 请求', async () => {
    mockClient.post.mockResolvedValueOnce({
      data: { success: true, data: { id: '123' }, message: 'ok' },
    })
    const result = await post('/products', { name: '测试' })
    expect(mockClient.post).toHaveBeenCalledWith('/products', { name: '测试' })
    expect(result.data.id).toBe('123')
  })

  it('put 发起 PUT 请求', async () => {
    mockClient.put.mockResolvedValueOnce({
      data: { success: true, data: { id: '123' }, message: 'ok' },
    })
    const result = await put('/products/123', { name: '更新' })
    expect(mockClient.put).toHaveBeenCalledWith('/products/123', { name: '更新' })
    expect(result.success).toBe(true)
  })

  it('del 发起 DELETE 请求', async () => {
    mockClient.delete.mockResolvedValueOnce({
      data: { success: true, data: null, message: 'ok' },
    })
    const result = await del('/products/123')
    expect(mockClient.delete).toHaveBeenCalledWith('/products/123')
    expect(result.success).toBe(true)
  })

  it('upload 发起 FormData POST 请求', async () => {
    mockClient.post.mockResolvedValueOnce({
      data: { success: true, data: { id: 'file1', url: '/uploads/1.png' }, message: 'ok' },
    })
    const file = new File(['content'], 'test.png', { type: 'image/png' })
    const result = await upload('/files/images', file)
    expect(mockClient.post).toHaveBeenCalledWith(
      '/files/images',
      expect.any(FormData),
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    expect(result.data.id).toBe('file1')
  })

  it('get 无参数调用', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: { success: true, data: [], message: 'ok' },
    })
    const result = await get('/products')
    expect(mockClient.get).toHaveBeenCalledWith('/products', { params: undefined })
    expect(result.data).toEqual([])
  })

  it('post 无 body 调用', async () => {
    mockClient.post.mockResolvedValueOnce({
      data: { success: true, data: null, message: 'ok' },
    })
    const result = await post('/auth/logout')
    expect(mockClient.post).toHaveBeenCalledWith('/auth/logout', undefined)
    expect(result.success).toBe(true)
  })

  it('put 无 body 调用', async () => {
    mockClient.put.mockResolvedValueOnce({
      data: { success: true, data: null, message: 'ok' },
    })
    const result = await put('/products/123')
    expect(mockClient.put).toHaveBeenCalledWith('/products/123', undefined)
    expect(result.success).toBe(true)
  })
})

describe('downloadCsv', () => {
  beforeEach(() => {
    // jsdom 未实现 URL.createObjectURL/revokeObjectURL
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue('blob:http://test/fake')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('过滤 undefined 和空字符串参数', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: new Blob(['a'], { type: 'text/csv' }),
      headers: { 'content-disposition': 'filename=out.csv' },
    })
    await downloadCsv('/exports/products', { a: '1', b: '', c: undefined })
    expect(mockClient.get).toHaveBeenCalledWith('/exports/products', {
      params: { a: '1' },
      responseType: 'blob',
    })
  })

  it('无参数时传空对象', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: new Blob(['a'], { type: 'text/csv' }),
      headers: { 'content-disposition': 'filename=out.csv' },
    })
    await downloadCsv('/exports/products')
    expect(mockClient.get).toHaveBeenCalledWith('/exports/products', {
      params: {},
      responseType: 'blob',
    })
  })

  it('检测 JSON 错误 blob 抛出 error.message', async () => {
    const errorJson = JSON.stringify({ error: { message: '导出权限不足' } })
    mockClient.get.mockResolvedValueOnce({
      data: new Blob([errorJson], { type: 'application/json' }),
      headers: {},
    })
    await expect(downloadCsv('/exports/products')).rejects.toThrow('导出权限不足')
  })

  it('JSON 错误 fallback 到 message 字段', async () => {
    const errorJson = JSON.stringify({ message: '服务器内部错误' })
    mockClient.get.mockResolvedValueOnce({
      data: new Blob([errorJson], { type: 'application/json' }),
      headers: {},
    })
    await expect(downloadCsv('/exports/products')).rejects.toThrow('服务器内部错误')
  })

  it('JSON 错误无消息字段使用默认文案', async () => {
    const errorJson = JSON.stringify({ code: 'UNKNOWN' })
    mockClient.get.mockResolvedValueOnce({
      data: new Blob([errorJson], { type: 'application/json' }),
      headers: {},
    })
    await expect(downloadCsv('/exports/products')).rejects.toThrow('导出失败')
  })

  it('成功下载调用 createObjectURL 和 revokeObjectURL', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: new Blob(['x'], { type: 'text/csv' }),
      headers: { 'content-disposition': 'filename=data.csv' },
    })
    await downloadCsv('/exports/products')
    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(URL.revokeObjectURL).toHaveBeenCalled()
  })
})
