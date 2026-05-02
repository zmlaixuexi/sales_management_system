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

// 下载 CSV 文件（使用 apiClient 统一拦截器覆盖：auth、429 重试、错误提示）
export async function downloadCsv(path: string, params: Record<string, string | undefined> = {}): Promise<void> {
  const filteredParams: Record<string, string> = {}
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '') filteredParams[k] = v
  })

  const resp = await apiClient.get(path, {
    params: filteredParams,
    responseType: 'blob',
  })

  const blob = resp.data as Blob

  // 后端返回 JSON 错误时 blob type 为 application/json，需解析错误消息
  if (blob.type && blob.type.includes('application/json')) {
    const text = await blob.text()
    const json = JSON.parse(text)
    const msg = json?.error?.message || json?.message || '导出失败'
    throw new Error(msg)
  }

  const disposition = resp.headers['content-disposition'] || ''
  const match = disposition.match(/filename=(.+)/)
  const filename = match ? match[1] : 'export.csv'

  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}
