import { lazy, Suspense, type ComponentType } from 'react'
import { Spin } from 'antd'
import type { RouteObject } from 'react-router-dom'
import AppLayout from '@/routes/AppLayout'
import ProtectedRoute from '@/routes/ProtectedRoute'

const Loading = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
    <Spin size="large" />
  </div>
)

function lazyPage(load: () => Promise<{ default: ComponentType }>) {
  const Component = lazy(load)
  return (
    <Suspense fallback={<Loading />}>
      <Component />
    </Suspense>
  )
}

const routes: RouteObject[] = [
  {
    path: '/login',
    element: lazyPage(() => import('@/pages/Login')),
  },
  {
    path: '/',
    element: <ProtectedRoute><AppLayout /></ProtectedRoute>,
    children: [
      { index: true, element: lazyPage(() => import('@/pages/Dashboard')) },
      { path: 'products', element: lazyPage(() => import('@/pages/Products')) },
      { path: 'products/new', element: lazyPage(() => import('@/pages/ProductForm')) },
      { path: 'products/:id/edit', element: lazyPage(() => import('@/pages/ProductForm')) },
      { path: 'inventory', element: lazyPage(() => import('@/pages/Inventory')) },
      { path: 'customers', element: lazyPage(() => import('@/pages/Customers')) },
      { path: 'customers/new', element: lazyPage(() => import('@/pages/CustomerForm')) },
      { path: 'customers/:id', element: lazyPage(() => import('@/pages/CustomerDetail')) },
      { path: 'customers/:id/edit', element: lazyPage(() => import('@/pages/CustomerForm')) },
      { path: 'orders', element: lazyPage(() => import('@/pages/Orders')) },
      { path: 'orders/new', element: lazyPage(() => import('@/pages/OrderForm')) },
      { path: 'orders/:id', element: lazyPage(() => import('@/pages/OrderDetail')) },
      { path: 'orders/:id/edit', element: lazyPage(() => import('@/pages/OrderForm')) },
      { path: 'payments', element: lazyPage(() => import('@/pages/Payments')) },
      { path: 'audit-logs', element: lazyPage(() => import('@/pages/AuditLogs')) },
      { path: 'reports', element: lazyPage(() => import('@/pages/ReportsCenter')) },
      { path: 'users', element: lazyPage(() => import('@/pages/Users')) },
      { path: 'roles', element: lazyPage(() => import('@/pages/Roles')) },
    ],
  },
  {
    path: '*',
    element: lazyPage(() => import('@/pages/NotFound')),
  },
]

export default routes
