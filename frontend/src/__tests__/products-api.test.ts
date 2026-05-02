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

  it('fetchProducts 按分类筛选', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchProducts({ category_id: 'cat-1' })
    expect(mockGet).toHaveBeenCalledWith('/products', { category_id: 'cat-1' })
  })

  it('fetchProducts 支持排序', async () => {
    mockGet.mockResolvedValueOnce(ok({ items: [], page: 1, page_size: 20, total: 0 }))
    await fetchProducts({ sort_by: 'sale_price', sort_order: 'desc' })
    expect(mockGet).toHaveBeenCalledWith('/products', { sort_by: 'sale_price', sort_order: 'desc' })
  })

  it('fetchProducts 返回带派生字段的商品', async () => {
    const items = [{
      id: 'p1', sku: 'SKU-001', name: '商品A',
      main_image_url: '/uploads/a.png', category_id: 'c1', category_name: '默认',
      sale_price: '100.00', cost_price: '60.00', unit_profit: '40.00', gross_margin: '40.00',
      stock_quantity: 50, status: 'active', sort_weight: 0,
      remark: null, created_at: '2026-05-01T10:00:00Z', updated_at: '2026-05-01T10:00:00Z',
    }]
    mockGet.mockResolvedValueOnce(ok({ items, page: 1, page_size: 20, total: 1 }))
    const res = await fetchProducts({ page: 1 })
    expect(res.data.items[0].unit_profit).toBe('40.00')
    expect(res.data.items[0].gross_margin).toBe('40.00')
  })

  it('fetchProduct 调用 GET /products/:id', async () => {
    mockGet.mockResolvedValueOnce(ok({ id: 'p1', name: '商品A', images: [] }))
    const res = await fetchProduct('p1')
    expect(mockGet).toHaveBeenCalledWith('/products/p1')
    expect(res.data.name).toBe('商品A')
  })

  it('fetchProduct 返回完整详情含图片列表', async () => {
    const detail = {
      id: 'p1', sku: 'SKU-001', name: '商品A',
      main_image_url: '/uploads/a.png', category_id: null, category_name: null,
      sale_price: '100.00', stock_quantity: 10, status: 'active', sort_weight: 0,
      remark: null, created_at: '2026-05-01T10:00:00Z', updated_at: null,
      images: [
        { id: 'img1', file_id: 'f1', url: '/uploads/a.png', is_primary: true, sort_order: 0 },
        { id: 'img2', file_id: 'f2', url: '/uploads/b.png', is_primary: false, sort_order: 1 },
      ],
    }
    mockGet.mockResolvedValueOnce(ok(detail))
    const res = await fetchProduct('p1')
    expect(res.data.images).toHaveLength(2)
    expect(res.data.images[0].is_primary).toBe(true)
  })

  it('createProduct 调用 POST /products', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'p2', sku: 'SPU-001' }))
    await createProduct({ name: '新商品', sale_price: '100', cost_price: '50' })
    expect(mockPost).toHaveBeenCalledWith('/products', { name: '新商品', sale_price: '100', cost_price: '50' })
  })

  it('createProduct 含可选字段', async () => {
    mockPost.mockResolvedValueOnce(ok({ id: 'p3', sku: 'SPU-002' }))
    await createProduct({
      name: '完整商品', sale_price: '200', cost_price: '100',
      category_id: 'c1', stock_quantity: 50, remark: '新品上架',
    })
    expect(mockPost).toHaveBeenCalledWith('/products', {
      name: '完整商品', sale_price: '200', cost_price: '100',
      category_id: 'c1', stock_quantity: 50, remark: '新品上架',
    })
  })

  it('updateProduct 调用 PUT /products/:id', async () => {
    mockPut.mockResolvedValueOnce(ok({ id: 'p1', name: '更新' }))
    await updateProduct('p1', { name: '更新' })
    expect(mockPut).toHaveBeenCalledWith('/products/p1', { name: '更新' })
  })

  it('updateProduct 更新价格', async () => {
    mockPut.mockResolvedValueOnce(ok({ id: 'p1', sale_price: '120' }))
    await updateProduct('p1', { sale_price: '120' })
    expect(mockPut).toHaveBeenCalledWith('/products/p1', { sale_price: '120' })
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

  it('uploadImage 返回文件信息', async () => {
    const file = new File(['test'], 'photo.jpg', { type: 'image/jpeg' })
    mockUpload.mockResolvedValueOnce(ok({
      id: 'f2', url: '/uploads/photo.jpg',
      original_name: 'photo.jpg', content_type: 'image/jpeg', size_bytes: 1024,
    }))
    const res = await uploadImage(file)
    expect(res.data.content_type).toBe('image/jpeg')
    expect(res.data.size_bytes).toBe(1024)
  })
})
