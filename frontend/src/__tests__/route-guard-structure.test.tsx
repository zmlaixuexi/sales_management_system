/* 代码质量：前端路由守卫与路由配置验证测试
验证路由结构完整性、ProtectedRoute 包裹范围、公开/受保护路由区分 */

import { describe, it, expect } from 'vitest'

import routes from '@/routes/index'
import ProtectedRoute from '@/routes/ProtectedRoute'

/** 检查元素是否为 ProtectedRoute */
function isProtectedRoute(element: unknown): boolean {
  if (!element || typeof element !== 'object') return false
  const type = (element as Record<string, unknown>).type
  return type === ProtectedRoute
}

describe('路由配置结构', () => {
  it('共有 3 个顶级路由', () => {
    expect(routes).toHaveLength(3)
  })

  it('包含 /login 公开路由', () => {
    const loginRoute = routes.find(r => r.path === '/login')
    expect(loginRoute).toBeDefined()
    expect(loginRoute!.element).toBeDefined()
  })

  it('包含 * 通配符路由', () => {
    const notFound = routes.find(r => r.path === '*')
    expect(notFound).toBeDefined()
    expect(notFound!.element).toBeDefined()
  })

  it('包含 / 受保护路由', () => {
    const protectedRoute = routes.find(r => r.path === '/')
    expect(protectedRoute).toBeDefined()
    expect(protectedRoute!.element).toBeDefined()
  })
})

describe('ProtectedRoute 包裹验证', () => {
  it('/ 路由使用 ProtectedRoute 包裹', () => {
    const rootRoute = routes.find(r => r.path === '/')
    expect(rootRoute).toBeDefined()
    expect(isProtectedRoute(rootRoute!.element)).toBe(true)
  })

  it('/login 不使用 ProtectedRoute', () => {
    const loginRoute = routes.find(r => r.path === '/login')
    expect(loginRoute).toBeDefined()
    expect(isProtectedRoute(loginRoute!.element)).toBe(false)
  })

  it('* 通配符不使用 ProtectedRoute', () => {
    const notFound = routes.find(r => r.path === '*')
    expect(notFound).toBeDefined()
    expect(isProtectedRoute(notFound!.element)).toBe(false)
  })
})

describe('受保护路由子路由', () => {
  const protectedRoute = routes.find(r => r.path === '/')

  it('受保护路由有 18 个子路由', () => {
    expect(protectedRoute!.children).toHaveLength(18)
  })

  it('所有子路由都有 element', () => {
    for (const child of protectedRoute!.children!) {
      expect(child.element).toBeDefined()
    }
  })

  it('包含关键业务路由', () => {
    const childPaths = protectedRoute!.children!.map(c => c.path)
    const expectedPaths = [
      undefined, // index route
      'products',
      'customers',
      'orders',
      'payments',
      'inventory',
      'audit-logs',
      'reports',
      'users',
      'roles',
    ]
    for (const p of expectedPaths) {
      if (p) {
        expect(childPaths).toContain(p)
      } else {
        expect(childPaths).toContain(undefined)
      }
    }
  })

  it('商品路由包含新建和编辑', () => {
    const childPaths = protectedRoute!.children!.map(c => c.path)
    expect(childPaths).toContain('products/new')
    expect(childPaths).toContain('products/:id/edit')
  })

  it('客户端由包含新建、详情和编辑', () => {
    const childPaths = protectedRoute!.children!.map(c => c.path)
    expect(childPaths).toContain('customers/new')
    expect(childPaths).toContain('customers/:id')
    expect(childPaths).toContain('customers/:id/edit')
  })

  it('订单路由包含新建、详情和编辑', () => {
    const childPaths = protectedRoute!.children!.map(c => c.path)
    expect(childPaths).toContain('orders/new')
    expect(childPaths).toContain('orders/:id')
    expect(childPaths).toContain('orders/:id/edit')
  })

  it('没有子路由重复定义', () => {
    const childPaths = protectedRoute!.children!.map(c => c.path)
    const uniquePaths = new Set(childPaths)
    expect(uniquePaths.size).toBe(childPaths.length)
  })

  it('没有子路由使用绝对路径（以 / 开头）', () => {
    for (const child of protectedRoute!.children!) {
      if (child.path) {
        expect(child.path.startsWith('/')).toBe(false)
      }
    }
  })
})

describe('公开路由验证', () => {
  it('/login 路由无子路由', () => {
    const loginRoute = routes.find(r => r.path === '/login')
    expect(loginRoute!.children).toBeUndefined()
  })

  it('* 路由无子路由', () => {
    const notFound = routes.find(r => r.path === '*')
    expect(notFound!.children).toBeUndefined()
  })
})

describe('ProtectedRoute 组件类型', () => {
  it('ProtectedRoute 是函数组件', () => {
    expect(typeof ProtectedRoute).toBe('function')
  })

  it('ProtectedRoute 有 displayName 或 name', () => {
    const name = ProtectedRoute.displayName || ProtectedRoute.name
    expect(name.length).toBeGreaterThan(0)
  })
})
