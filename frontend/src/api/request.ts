import axios from 'axios'
import type { ApiResponse } from '@/types'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截：自动附加 Token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一错误处理
request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// 封装 GET
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
  const res = await request.get<ApiResponse<T>>(url, { params })
  return res.data
}

// 封装 POST
export async function post<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const res = await request.post<ApiResponse<T>>(url, data)
  return res.data
}

// 封装 PUT
export async function put<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const res = await request.put<ApiResponse<T>>(url, data)
  return res.data
}

// 封装 DELETE
export async function del<T>(url: string): Promise<ApiResponse<T>> {
  const res = await request.delete<ApiResponse<T>>(url)
  return res.data
}

// 上传文件
export async function upload<T>(url: string, file: File): Promise<ApiResponse<T>> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await request.post<ApiResponse<T>>(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export default request
