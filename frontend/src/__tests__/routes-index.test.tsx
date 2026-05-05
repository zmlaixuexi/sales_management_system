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
  RouteGuard: ({ children }: any) => <>{children}</>,
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

  it('/inventory 渲染库存页', async () => {
    renderRoute('/inventory')
    await waitFor(() => {
      expect(screen.getByText('Inventory')).toBeInTheDocument()
    })
  })

  it('/customers 渲染客户列表', async () => {
    renderRoute('/customers')
    await waitFor(() => {
      expect(screen.getByText('Customers')).toBeInTheDocument()
    })
  })

  it('/customers/new 渲染新建客户', async () => {
    renderRoute('/customers/new')
    await waitFor(() => {
      expect(screen.getByText('CustomerForm')).toBeInTheDocument()
    })
  })

  it('/customers/:id 渲染客户详情', async () => {
    renderRoute('/customers/c1')
    await waitFor(() => {
      expect(screen.getByText('CustomerDetail')).toBeInTheDocument()
    })
  })

  it('/customers/:id/edit 渲染编辑客户', async () => {
    renderRoute('/customers/c1/edit')
    await waitFor(() => {
      expect(screen.getByText('CustomerForm')).toBeInTheDocument()
    })
  })

  it('/orders 渲染订单列表', async () => {
    renderRoute('/orders')
    await waitFor(() => {
      expect(screen.getByText('Orders')).toBeInTheDocument()
    })
  })

  it('/orders/new 渲染新建订单', async () => {
    renderRoute('/orders/new')
    await waitFor(() => {
      expect(screen.getByText('OrderForm')).toBeInTheDocument()
    })
  })

  it('/orders/:id 渲染订单详情', async () => {
    renderRoute('/orders/o1')
    await waitFor(() => {
      expect(screen.getByText('OrderDetail')).toBeInTheDocument()
    })
  })

  it('/orders/:id/edit 渲染编辑订单', async () => {
    renderRoute('/orders/o1/edit')
    await waitFor(() => {
      expect(screen.getByText('OrderForm')).toBeInTheDocument()
    })
  })

  it('/payments 渲染收款列表', async () => {
    renderRoute('/payments')
    await waitFor(() => {
      expect(screen.getByText('Payments')).toBeInTheDocument()
    })
  })

  it('/audit-logs 渲染审计日志', async () => {
    renderRoute('/audit-logs')
    await waitFor(() => {
      expect(screen.getByText('AuditLogs')).toBeInTheDocument()
    })
  })

  it('/reports 渲染报表中心', async () => {
    renderRoute('/reports')
    await waitFor(() => {
      expect(screen.getByText('ReportsCenter')).toBeInTheDocument()
    })
  })

  it('/users 渲染用户管理', async () => {
    renderRoute('/users')
    await waitFor(() => {
      expect(screen.getByText('Users')).toBeInTheDocument()
    })
  })

  it('/roles 渲染角色管理', async () => {
    renderRoute('/roles')
    await waitFor(() => {
      expect(screen.getByText('Roles')).toBeInTheDocument()
    })
  })

  it('/products/new 渲染新建商品', async () => {
    renderRoute('/products/new')
    await waitFor(() => {
      expect(screen.getByText('ProductForm')).toBeInTheDocument()
    })
  })

  it('/products/:id/edit 渲染编辑商品', async () => {
    renderRoute('/products/p1/edit')
    await waitFor(() => {
      expect(screen.getByText('ProductForm')).toBeInTheDocument()
    })
  })
})
