// API 统一响应格式
export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  message: string
  request_id?: string
}

// API 错误响应
export interface ApiError {
  success: false
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
  request_id?: string
}

// 分页响应
export interface PaginatedData<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}
