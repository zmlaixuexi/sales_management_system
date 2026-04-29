import apiClient from './client'
import type { ApiResponse } from '@/types'

// 封装 GET
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
  const res = await apiClient.get<ApiResponse<T>>(url, { params })
  return res.data
}

// 封装 POST
export async function post<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const res = await apiClient.post<ApiResponse<T>>(url, data)
  return res.data
}

// 封装 PUT
export async function put<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const res = await apiClient.put<ApiResponse<T>>(url, data)
  return res.data
}

// 封装 DELETE
export async function del<T>(url: string): Promise<ApiResponse<T>> {
  const res = await apiClient.delete<ApiResponse<T>>(url)
  return res.data
}

// 上传文件
export async function upload<T>(url: string, file: File): Promise<ApiResponse<T>> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await apiClient.post<ApiResponse<T>>(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
