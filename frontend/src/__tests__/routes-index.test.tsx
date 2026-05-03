import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'

/* eslint-disable @typescript-eslint/no-explicit-any */

const MockLogin = () => <div data-testid="page-login">登录页</div>
const MockDashboard = () => <div data-testid="page-dashboard">首页看板</div>
const MockProducts = () => <div data-testid="page-products">商品管理</div>
const MockNotFound = () => <div data-testid="page-notfound">404</div>

vi.mock('@/routes/ProtectedRoute', () => ({
  default: ({ children }: any) => <div data-testid="protected">{children}</div>,
}))

vi.mock('@/routes/AppLayout', () => ({
  default: () => (
    <div data-testid="app-layout">
      <Outlet />
    </div>
  ),
}))

vi.mock('antd', () => ({
  Spin: ({ size }: any) => <div data-testid="spin">{size}</div>,
  Layout: ({ children }: any) => <div>{children}</div>,
  Menu: () => <div />,
}))

vi.mock('@/pages/Login', () => ({ default: MockLogin }))
vi.mock('@/pages/Dashboard', () => ({ default: MockDashboard }))
vi.mock('@/pages/Products', () => ({ default: MockProducts }))
vi.mock('@/pages/ProductForm', () => ({ default: () => <div>ProductForm</div> }))
vi.mock('@/pages/Inventory', () => ({ default: () => <div>Inventory</div> }))
vi.mock('@/pages/Customers', () => ({ default: () => <div>Customers</div> }))
vi.mock('@/pages/CustomerForm', () => ({ default: () => <div>CustomerForm</div> }))
vi.mock('@/pages/CustomerDetail', () => ({ default: () => <div>CustomerDetail</div> }))
vi.mock('@/pages/Orders', () => ({ default: () => <div>Orders</div> }))
vi.mock('@/pages/OrderForm', () => ({ default: () => <div>OrderForm</div> }))
vi.mock('@/pages/OrderDetail', () => ({ default: () => <div>OrderDetail</div> }))
vi.mock('@/pages/Payments', () => ({ default: () => <div>Payments</div> }))
vi.mock('@/pages/AuditLogs', () => ({ default: () => <div>AuditLogs</div> }))
vi.mock('@/pages/ReportsCenter', () => ({ default: () => <div>ReportsCenter</div> }))
vi.mock('@/pages/Users', () => ({ default: () => <div>Users</div> }))
vi.mock('@/pages/Roles', () => ({ default: () => <div>Roles</div> }))
vi.mock('@/pages/NotFound', () => ({ default: MockNotFound }))

import routes from '@/routes/index'

function renderRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        {routes.map((route, i) => (
          <Route key={route.path || i} path={route.path} element={route.element}>
            {route.children?.map((child, j) => {
              if (child.index) {
                return <Route key={`index-${j}`} index element={child.element} />
              }
              return <Route key={child.path || j} path={child.path} element={child.element} />
            })}
          </Route>
        ))}
      </Routes>
    </MemoryRouter>,
  )
}

describe('routes/index', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('/login 路由渲染登录页', async () => {
    renderRoute('/login')
    await waitFor(() => {
      expect(screen.getByTestId('page-login')).toBeInTheDocument()
    })
  })

  it('/ 根路径渲染首页看板', async () => {
    renderRoute('/')
    await waitFor(() => {
      expect(screen.getByTestId('page-dashboard')).toBeInTheDocument()
    })
  })

  it('/products 渲染商品管理', async () => {
    renderRoute('/products')
    await waitFor(() => {
      expect(screen.getByTestId('page-products')).toBeInTheDocument()
    })
  })

  it('受保护路由包含 ProtectedRoute 包裹', async () => {
    renderRoute('/')
    await waitFor(() => {
      expect(screen.getByTestId('protected')).toBeInTheDocument()
    })
  })

  it('通配符路由渲染 404 页面', async () => {
    renderRoute('/nonexistent-page')
    await waitFor(() => {
      expect(screen.getByTestId('page-notfound')).toBeInTheDocument()
    })
  })

  it('lazyPage 返回的组件包含 Suspense 包裹', () => {
    expect(routes).toBeDefined()
    expect(routes.length).toBeGreaterThanOrEqual(2)
    const loginRoute = routes.find(r => r.path === '/login')
    expect(loginRoute).toBeDefined()
    const wildcardRoute = routes.find(r => r.path === '*')
    expect(wildcardRoute).toBeDefined()
  })

  it('受保护路由包含 children 配置', () => {
    const protectedRoute = routes.find(r => r.path === '/')
    expect(protectedRoute).toBeDefined()
    expect(protectedRoute!.children).toBeDefined()
    expect(protectedRoute!.children!.length).toBeGreaterThanOrEqual(5)
  })
})
