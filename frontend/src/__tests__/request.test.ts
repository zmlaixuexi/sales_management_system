import { describe, it, expect, vi } from 'vitest'
import { get, post, put, del, upload } from '@/api/request'

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
