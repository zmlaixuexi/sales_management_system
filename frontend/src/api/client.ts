import axios from 'axios'
import { message } from 'antd'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：自动附加 Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：401 刷新 + 429 重试 + 统一错误提示
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 429 速率限制：等待后自动重试一次
    if (error.response?.status === 429 && !originalRequest._retry429) {
      originalRequest._retry429 = true
      const retryAfter = parseInt(error.response.headers['retry-after'] || '5', 10) * 1000
      await new Promise((r) => setTimeout(r, Math.min(retryAfter, 5000)))
      return apiClient(originalRequest)
    }

    // 401 未授权：尝试刷新 Token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post(
            `${apiClient.defaults.baseURL}/auth/refresh`,
            { refresh_token: refreshToken },
          )
          localStorage.setItem('access_token', data.data.access_token)
          localStorage.setItem('refresh_token', data.data.refresh_token)
          originalRequest.headers.Authorization = `Bearer ${data.data.access_token}`
          return apiClient(originalRequest)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          return Promise.reject(error)
        }
      } else {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }

    // 统一错误提示（排除 401 已处理和登录接口的 401）
    let _displayed = false
    if (error.response?.status === 429) {
      message.error('请求过于频繁，请稍后再试')
      _displayed = true
    } else if (error.response?.status === 403) {
      message.error('没有操作权限')
      _displayed = true
    } else if (error.response?.status === 404) {
      message.error('请求的资源不存在')
      _displayed = true
    } else if (error.response?.status === 500) {
      message.error('服务器错误，请稍后重试')
      _displayed = true
    } else if (error.response?.data?.error?.message && error.response?.status !== 401) {
      message.error(error.response.data.error.message)
      _displayed = true
    } else if (error.response?.data?.message && error.response?.status !== 401) {
      message.error(error.response.data.message)
      _displayed = true
    } else if (!error.response) {
      message.error('网络连接失败，请检查网络')
      _displayed = true
    }

    if (_displayed) {
      ;(error as unknown as Record<string, boolean>)._toastDisplayed = true
    }
    return Promise.reject(error)
  },
)

export default apiClient
