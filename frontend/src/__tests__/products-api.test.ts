import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchProducts, fetchProduct, createProduct,
  updateProduct, deleteProduct, disableProduct, fetchPriceHistory, uploadImage,
} from '@/api/products'

vi.mock('@/api/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
  upload: vi.fn(),
}))

import { get, post, put, del, upload } from '@/api/request'

const mockGet = get as ReturnType<typeof vi.fn>
const mockPost = post as ReturnType<typeof vi.fn>
const mockPut = put as ReturnType<typeof vi.fn>
const mockDel = del as ReturnType<typeof vi.fn>
const mockUpload = upload as ReturnType<typeof vi.fn>

const ok = (data: unknown) => Promise.resolve({ success: true, data, message: 'ok' })

describe('商品 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchProducts 调用 GET /products', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchProducts({ keyword: '测试', status: 'active' })
    expect(mockGet).toHaveBeenCalledWith('/products', { keyword: '测试', status: 'active' })
  })

  it('fetchProduct 调用 GET /products/:id', async () => {
    mockGet.mockResolvedValueOnce(ok({ id: 'p1', name: '商品A', images: [] }))
    const res = await fetchProduct('p1')
    expect(mockGet).toHaveBeenCalledWith('/products/p1')
    expect(res.data.name).toBe('商品A')
  })

  it('createProduct 调用 POST /products', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'p2', sku: 'SPU-001' }))
    await createProduct({ name: '新商品', sale_price: '100', cost_price: '50' })
    expect(mockPost).toHaveBeenCalledWith('/products', { name: '新商品', sale_price: '100', cost_price: '50' })
  })

  it('updateProduct 调用 PUT /products/:id', async () => {
    mockPut.mockResolvedValueOnce(ok({ id: 'p1', name: '更新' }))
    await updateProduct('p1', { name: '更新' })
    expect(mockPut).toHaveBeenCalledWith('/products/p1', { name: '更新' })
  })

  it('deleteProduct 调用 DELETE /products/:id', async () => {
    mockDel.mockResolvedValueOnce(ok(null))
    await deleteProduct('p1')
    expect(mockDel).toHaveBeenCalledWith('/products/p1')
  })

  it('disableProduct 调用 POST /products/:id/disable', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'p1', status: 'disabled' }))
    await disableProduct('p1')
    expect(mockPost).toHaveBeenCalledWith('/products/p1/disable')
  })

  it('fetchPriceHistory 调用 GET /products/:id/price-history', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [] }))
    await fetchPriceHistory('p1')
    expect(mockGet).toHaveBeenCalledWith('/products/p1/price-history')
  })

  it('uploadImage 调用 upload /files/images', async () => {
    const file = new File(['test'], 'img.png', { type: 'image/png' })
    mockUpload.mockResolvedValueOnce(ok({ id: 'f1', url: '/uploads/img.png' }))
    await uploadImage(file)
    expect(mockUpload).toHaveBeenCalledWith('/files/images', file)
  })
})
