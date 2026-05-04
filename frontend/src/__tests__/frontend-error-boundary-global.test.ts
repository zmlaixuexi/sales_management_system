/**
 * 可观测性：前端错误边界与全局异常处理验证测试
 * 覆盖 ErrorBoundary 组件逻辑、路由感知重置、
 * 全局 HTTP 错误拦截、401 刷新重试逻辑、应用顶层包裹结构
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')

function frontendSrc(relPath: string): string {
  return readFileSync(resolve(root, 'frontend/src', relPath), 'utf-8')
}

const boundaryCode = frontendSrc('components/ErrorBoundary.tsx')
const clientCode = frontendSrc('api/client.ts')
const mainCode = frontendSrc('main.tsx')
const requestCode = frontendSrc('api/request.ts')

// ═══════════════════════════════════════════════════════════
// 1. ErrorBoundary 组件逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('ErrorBoundary 组件逻辑', () => {
  it('使用 class 组件实现 getDerivedStateFromError', () => {
    expect(boundaryCode).toContain('class ErrorBoundaryInner extends Component')
    expect(boundaryCode).toContain('static getDerivedStateFromError')
  })

  it('State 接口包含 hasError 和 error', () => {
    expect(boundaryCode).toContain('interface State')
    expect(boundaryCode).toContain('hasError: boolean')
    expect(boundaryCode).toContain('error: Error | null')
  })

  it('错误状态显示 Result 组件和重试/返回首页按钮', () => {
    expect(boundaryCode).toContain('<Result')
    expect(boundaryCode).toContain('status="error"')
    expect(boundaryCode).toContain('title="页面出错了"')
    expect(boundaryCode).toContain('key="retry"')
    expect(boundaryCode).toContain('key="home"')
  })

  it('handleReload 重置错误状态', () => {
    expect(boundaryCode).toContain('handleReload')
    expect(boundaryCode).toContain('hasError: false')
    expect(boundaryCode).toContain('error: null')
  })

  it('Props 接口接受 children 和 resetKey', () => {
    expect(boundaryCode).toContain('interface Props')
    expect(boundaryCode).toContain('children: ReactNode')
    expect(boundaryCode).toContain('resetKey?: string')
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 路由感知重置验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('路由感知重置', () => {
  it('使用 useLocation 获取当前路径作为 resetKey', () => {
    expect(boundaryCode).toContain('useLocation')
    expect(boundaryCode).toContain('resetKey={location.pathname}')
  })

  it('componentDidUpdate 检测 resetKey 变化时重置', () => {
    expect(boundaryCode).toContain('componentDidUpdate')
    expect(boundaryCode).toContain('prevProps.resetKey !== this.props.resetKey')
  })

  it('外部 ErrorBoundary 是函数组件包装器', () => {
    expect(boundaryCode).toContain('export default function ErrorBoundary')
  })

  it('内部 class 组件接收 resetKey prop', () => {
    expect(boundaryCode).toContain('<ErrorBoundaryInner resetKey=')
    expect(boundaryCode).toContain('{children}')
  })

  it('错误信息展示 error.message 或默认文案', () => {
    expect(boundaryCode).toContain('this.state.error?.message')
    expect(boundaryCode).toContain('发生了未知错误')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 全局 HTTP 错误拦截验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('全局 HTTP 错误拦截', () => {
  it('响应拦截器覆盖全部常见错误码', () => {
    expect(clientCode).toContain('429')
    expect(clientCode).toContain('403')
    expect(clientCode).toContain('404')
    expect(clientCode).toContain('500')
  })

  it('每个错误码有对应的中文提示', () => {
    expect(clientCode).toContain('请求过于频繁')
    expect(clientCode).toContain('没有操作权限')
    expect(clientCode).toContain('请求的资源不存在')
    expect(clientCode).toContain('服务器错误')
  })

  it('网络错误有独立提示', () => {
    expect(clientCode).toContain('!error.response')
    expect(clientCode).toContain('网络连接失败')
  })

  it('使用 _toastDisplayed 标记已提示的错误', () => {
    expect(clientCode).toContain('_toastDisplayed')
    expect(clientCode).toContain('_displayed = true')
  })

  it('后端 error.message 和 message 字段都能被提取', () => {
    expect(clientCode).toContain('error.response?.data?.error?.message')
    expect(clientCode).toContain('error.response?.data?.message')
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 401 刷新重试逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('401 刷新重试逻辑', () => {
  it('401 时尝试使用 refresh_token 刷新', () => {
    expect(clientCode).toContain('401')
    expect(clientCode).toContain('refresh_token')
    expect(clientCode).toContain('/auth/refresh')
  })

  it('刷新成功后更新 localStorage 并重试原请求', () => {
    expect(clientCode).toContain("localStorage.setItem('access_token'")
    expect(clientCode).toContain("localStorage.setItem('refresh_token'")
    expect(clientCode).toContain('return apiClient(originalRequest)')
  })

  it('刷新失败后清除 token 并跳转 /login', () => {
    expect(clientCode).toContain("localStorage.removeItem('access_token')")
    expect(clientCode).toContain("localStorage.removeItem('refresh_token')")
    expect(clientCode).toContain("window.location.href = '/login'")
  })

  it('429 速率限制自动重试一次', () => {
    expect(clientCode).toContain('_retry429')
    expect(clientCode).toContain('retry-after')
    expect(clientCode).toContain('Math.min(retryAfter, 5000)')
  })

  it('使用 _retry 防止无限重试循环', () => {
    expect(clientCode).toContain('originalRequest._retry = true')
    expect(clientCode).toContain('!originalRequest._retry')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 应用顶层包裹结构验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('应用顶层包裹结构', () => {
  it('main.tsx 使用 StrictMode 包裹', () => {
    expect(mainCode).toContain('<StrictMode>')
    expect(mainCode).toContain('</StrictMode>')
  })

  it('main.tsx 使用 ConfigProvider 配置中文', () => {
    expect(mainCode).toContain('ConfigProvider')
    expect(mainCode).toContain("zhCN")
    expect(mainCode).toContain("import zhCN from 'antd/locale/zh_CN'")
  })

  it('ErrorBoundary 包裹在路由最顶层', () => {
    expect(mainCode).toContain('<ErrorBoundary>')
    expect(mainCode).toContain('<Outlet />')
    expect(mainCode).toContain('children: routes')
  })

  it('使用 createBrowserRouter 而非旧版路由', () => {
    expect(mainCode).toContain('createBrowserRouter')
    expect(mainCode).toContain('RouterProvider')
  })

  it('request.ts 的 downloadCsv 处理 blob 类型错误', () => {
    expect(requestCode).toContain('application/json')
    expect(requestCode).toContain('blob.type')
    expect(requestCode).toContain('throw new Error')
  })
})
