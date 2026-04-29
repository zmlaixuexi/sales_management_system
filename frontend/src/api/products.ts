import { get, post, put, del, upload } from './request'
import type { PaginatedData } from '@/types'

export interface Product {
  id: string
  sku: string
  name: string
  main_image_url: string | null
  category_id: string | null
  category_name: string | null
  sale_price: string
  cost_price: string
  unit_profit: string
  gross_margin: string
  stock_quantity: number
  status: string
  sort_weight: number
  remark: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ProductDetail extends Product {
  images: Array<{
    id: string
    file_id: string
    url: string | null
    is_primary: boolean
    sort_order: number
  }>
}

export interface ProductFormValues {
  name: string
  cost_price: string
  sale_price: string
  main_image_url?: string
  sku?: string
  category_id?: string
  stock_quantity?: number
  status?: string
  sort_weight?: number
  remark?: string
}

export interface ProductListParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  category_id?: string
  sort_by?: string
  sort_order?: string
}

export async function fetchProducts(params: ProductListParams) {
  return get<PaginatedData<Product>>('/products', params as Record<string, unknown>)
}

export async function fetchProduct(id: string) {
  return get<ProductDetail>(`/products/${id}`)
}

export async function createProduct(data: ProductFormValues) {
  return post<Product>('/products', data)
}

export async function updateProduct(id: string, data: Partial<ProductFormValues>) {
  return put<Product>(`/products/${id}`, data)
}

export async function deleteProduct(id: string) {
  return del(`/products/${id}`)
}

export async function disableProduct(id: string) {
  return post<{ id: string; status: string }>(`/products/${id}/disable`)
}

export async function fetchPriceHistory(productId: string) {
  return get<{ items: Array<Record<string, unknown>> }>(`/products/${productId}/price-history`)
}

export interface UploadedFile {
  id: string
  url: string
  original_name: string
  content_type: string
  size_bytes: number
}

export async function uploadImage(file: File) {
  return upload<UploadedFile>('/files/images', file)
}
