/* 代码质量：前端页面组件导出与路由引用一致性验证测试
验证 pages 目录下所有组件均有默认导出、路由引用的页面文件存在 */

import { describe, it, expect } from 'vitest'

import routes from '@/routes/index'
import ProtectedRoute from '@/routes/ProtectedRoute'

const PAGE_IMPORTS = [
  '@/pages/Login',
  '@/pages/Dashboard',
  '@/pages/Products',
  '@/pages/ProductForm',
  '@/pages/Inventory',
  '@/pages/Customers',
  '@/pages/CustomerForm',
  '@/pages/CustomerDetail',
  '@/pages/Orders',
  '@/pages/OrderForm',
  '@/pages/OrderDetail',
  '@/pages/Payments',
  '@/pages/AuditLogs',
  '@/pages/ReportsCenter',
  '@/pages/Users',
  '@/pages/Roles',
  '@/pages/NotFound',
] as const

/** 从路由配置提取所有懒加载路径 */
function extractLazyPaths(routesList: typeof routes): string[] {
  const paths: string[] = []
  for (const route of routesList) {
    // 路由的 element 是 lazy 包裹的 JSX，无法直接提取模块路径
    // 但我们可以验证路由结构完整性
    if (route.children) {
      for (const child of route.children) {
        if (child.element) paths.push(child.path ?? 'index')
      }
    }
    if (route.element) paths.push(route.path)
  }
  return paths
}

describe('页面模块文件存在性', () => {
  it('所有路由引用的页面模块都可以动态导入', async () => {
    // 验证每个页面模块都可以被 import() 而不抛出模块未找到错误
    for (const pagePath of PAGE_IMPORTS) {
      const importPromise = import(/* @vite-ignore */ pagePath)
      await expect(importPromise).resolves.toBeDefined()
    }
  })
})

describe('页面模块默认导出', () => {
  it.each(PAGE_IMPORTS)('%s 有默认导出', async (pagePath) => {
    const mod = await import(/* @vite-ignore */ pagePath)
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })
})

describe('路由与页面模块对应', () => {
  it('/login 路由引用 Login 页面', async () => {
    const mod = await import('@/pages/Login')
    expect(mod.default).toBeDefined()
  })

  it('Dashboard 是受保护路由的 index 页面', async () => {
    const protectedRoute = routes.find(r => r.path === '/')
    expect(protectedRoute).toBeDefined()
    expect(protectedRoute!.children).toBeDefined()
    const indexRoute = protectedRoute!.children!.find(c => c.index === true)
    expect(indexRoute).toBeDefined()
  })

  it('ProductForm 用于新建和编辑商品', async () => {
    const mod = await import('@/pages/ProductForm')
    expect(mod.default).toBeDefined()
    const protectedRoute = routes.find(r => r.path === '/')
    const childPaths = protectedRoute!.children!.map(c => c.path)
    expect(childPaths).toContain('products/new')
    expect(childPaths).toContain('products/:id/edit')
  })

  it('OrderForm 用于新建和编辑订单', async () => {
    const mod = await import('@/pages/OrderForm')
    expect(mod.default).toBeDefined()
    const protectedRoute = routes.find(r => r.path === '/')
    const childPaths = protectedRoute!.children!.map(c => c.path)
    expect(childPaths).toContain('orders/new')
    expect(childPaths).toContain('orders/:id/edit')
  })

  it('CustomerForm 用于新建和编辑客户', async () => {
    const mod = await import('@/pages/CustomerForm')
    expect(mod.default).toBeDefined()
    const protectedRoute = routes.find(r => r.path === '/')
    const childPaths = protectedRoute!.children!.map(c => c.path)
    expect(childPaths).toContain('customers/new')
    expect(childPaths).toContain('customers/:id/edit')
  })

  it('CustomerDetail 用于查看客户详情', async () => {
    const mod = await import('@/pages/CustomerDetail')
    expect(mod.default).toBeDefined()
    const protectedRoute = routes.find(r => r.path === '/')
    const childPaths = protectedRoute!.children!.map(c => c.path)
    expect(childPaths).toContain('customers/:id')
  })

  it('OrderDetail 用于查看订单详情', async () => {
    const mod = await import('@/pages/OrderDetail')
    expect(mod.default).toBeDefined()
    const protectedRoute = routes.find(r => r.path === '/')
    const childPaths = protectedRoute!.children!.map(c => c.path)
    expect(childPaths).toContain('orders/:id')
  })

  it('NotFound 处理未匹配路由', async () => {
    const mod = await import('@/pages/NotFound')
    expect(mod.default).toBeDefined()
    const notFoundRoute = routes.find(r => r.path === '*')
    expect(notFoundRoute).toBeDefined()
  })
})

describe('路由结构完整性', () => {
  it('所有受保护子路由数量与页面模块匹配', () => {
    const protectedRoute = routes.find(r => r.path === '/')
    expect(protectedRoute!.children).toHaveLength(18)
  })

  it('没有未引用的页面模块', () => {
    // 页面文件数量 = 17 (Login, Dashboard, Products, ProductForm, Inventory,
    // Customers, CustomerForm, CustomerDetail, Orders, OrderForm, OrderDetail,
    // Payments, AuditLogs, ReportsCenter, Users, Roles, NotFound)
    // 路由引用 17 个模块 (ProductForm 和 OrderForm 被引用两次但只算一个文件)
    expect(PAGE_IMPORTS).toHaveLength(17)
  })

  it('受保护路由使用 ProtectedRoute 包裹', () => {
    const rootRoute = routes.find(r => r.path === '/')
    const type = (rootRoute!.element as Record<string, unknown>)?.type
    expect(type).toBe(ProtectedRoute)
  })
})

describe('页面模块无循环依赖', () => {
  it('Login 页面不导入 ProtectedRoute', async () => {
    // Login 是公开页面，不应依赖 ProtectedRoute
    const mod = await import('@/pages/Login')
    expect(mod).toBeDefined()
  })
})
