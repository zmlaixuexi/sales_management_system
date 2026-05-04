/**
 * 代码质量：前端路由懒加载与代码拆分验证测试
 * 覆盖 lazy/dynamic import 使用、Suspense fallback 配置、
 * manualChunks 分包策略、ProtectedRoute 鉴权行为、路由结构完整性
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')

function frontendSrc(relPath: string): string {
  return readFileSync(resolve(root, 'frontend/src', relPath), 'utf-8')
}

function configSrc(relPath: string): string {
  return readFileSync(resolve(root, 'frontend', relPath), 'utf-8')
}

const routesCode = frontendSrc('routes/index.tsx')
const protectedCode = frontendSrc('routes/ProtectedRoute.tsx')
const layoutCode = frontendSrc('routes/AppLayout.tsx')
const viteConfig = configSrc('vite.config.ts')
const mainCode = frontendSrc('main.tsx')

// ═══════════════════════════════════════════════════════════
// 1. lazy/dynamic import 使用验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('lazy/dynamic import 使用', () => {
  it('路由文件从 react 导入 lazy 和 Suspense', () => {
    expect(routesCode).toContain('import { lazy, Suspense')
    expect(routesCode).toContain("type ComponentType")
  })

  it('lazyPage 辅助函数使用 lazy() 包装 dynamic import', () => {
    expect(routesCode).toContain('function lazyPage')
    expect(routesCode).toContain('const Component = lazy(load)')
    expect(routesCode).toContain('<Component />')
  })

  it('所有页面路由使用 lazyPage + dynamic import', () => {
    const dynamicImports = routesCode.match(/lazyPage\(\(\) => import\(/g) || []
    // 17 个页面路由 + 1 个 NotFound = 18
    expect(dynamicImports.length).toBeGreaterThanOrEqual(17)
  })

  it('每个路由使用独立的 import() 确保代码拆分', () => {
    const pageImports = routesCode.match(/import\(['"]@\/pages\/\w+['"]\)/g) || []
    const uniquePages = new Set(pageImports)
    expect(uniquePages.size).toBeGreaterThanOrEqual(10)
  })

  it('AppLayout 使用静态导入（布局不拆分）', () => {
    expect(routesCode).toContain("import AppLayout from '@/routes/AppLayout'")
    expect(routesCode).not.toMatch(/lazyPage.*AppLayout/)
  })
})

// ═══════════════════════════════════════════════════════════
// 2. Suspense fallback 配置验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('Suspense fallback 配置', () => {
  it('Loading 组件使用 Ant Design Spin', () => {
    expect(routesCode).toContain('const Loading = ()')
    expect(routesCode).toContain('<Spin')
    expect(routesCode).toContain('size="large"')
  })

  it('Loading 组件居中显示', () => {
    expect(routesCode).toContain('justifyContent: \'center\'')
    expect(routesCode).toContain('alignItems: \'center\'')
  })

  it('Suspense 包裹 lazy 组件', () => {
    expect(routesCode).toContain('<Suspense fallback={<Loading />}>')
  })

  it('ProtectedRoute 的 loading 状态也使用 Spin', () => {
    expect(protectedCode).toContain('<Spin size="large" />')
    expect(protectedCode).toContain('100vh')
  })

  it('main.tsx 使用 BrowserRouter 而非 HashRouter', () => {
    expect(mainCode).toContain('BrowserRouter')
    expect(mainCode).not.toContain('HashRouter')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. manualChunks 分包策略验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('manualChunks 分包策略', () => {
  it('Vite 配置定义了 manualChunks', () => {
    expect(viteConfig).toContain('manualChunks(id)')
  })

  it('React 相关库拆分为 vendor-react', () => {
    expect(viteConfig).toContain("'vendor-react'")
    expect(viteConfig).toContain('react-dom')
    expect(viteConfig).toContain('react/')
    expect(viteConfig).toContain('react-router')
  })

  it('Ant Design 拆分为 vendor-antd', () => {
    expect(viteConfig).toContain("'vendor-antd'")
    expect(viteConfig).toContain('antd')
    expect(viteConfig).toContain('@ant-design')
  })

  it('设置了 chunk 大小警告阈值', () => {
    expect(viteConfig).toContain('chunkSizeWarningLimit')
    expect(viteConfig).toContain('1500')
  })

  it('使用 rollupOptions 配置输出', () => {
    expect(viteConfig).toContain('rollupOptions')
    expect(viteConfig).toContain('output:')
  })
})

// ═══════════════════════════════════════════════════════════
// 4. ProtectedRoute 鉴权行为验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('ProtectedRoute 鉴权行为', () => {
  it('无 token 时重定向到 /login', () => {
    expect(protectedCode).toContain("Navigate to=\"/login\" replace")
    expect(protectedCode).toContain('!token')
  })

  it('有 token 但无 user 时调用 fetchUser', () => {
    expect(protectedCode).toContain('fetchUser()')
    expect(protectedCode).toContain('.finally')
  })

  it('loading 状态期间显示加载中', () => {
    expect(protectedCode).toContain('const [loading')
    expect(protectedCode).toContain('!!token && !user')
    expect(protectedCode).toContain('if (loading)')
  })

  it('fetchUser 失败后重定向到 /login', () => {
    expect(protectedCode).toContain('!user')
    // 第二个 Navigate 检查
    const navigateCount = (protectedCode.match(/Navigate to="\/login"/g) || []).length
    expect(navigateCount).toBeGreaterThanOrEqual(2)
  })

  it('使用 useAuthStore 获取认证状态', () => {
    expect(protectedCode).toContain("import { useAuthStore } from '@/stores/auth'")
    expect(protectedCode).toContain('useAuthStore()')
    expect(protectedCode).toContain('token')
    expect(protectedCode).toContain('user')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 路由结构完整性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('路由结构完整性', () => {
  it('根路径 "/" 使用 ProtectedRoute + AppLayout', () => {
    expect(routesCode).toContain("<ProtectedRoute><AppLayout /></ProtectedRoute>")
  })

  it('包含所有业务模块路由', () => {
    const expectedPaths = [
      "'/login'", "'products'", "'inventory'", "'customers'",
      "'orders'", "'payments'", "'audit-logs'", "'reports'",
      "'users'", "'roles'",
    ]
    for (const p of expectedPaths) {
      expect(routesCode).toContain(p)
    }
  })

  it('包含新建/编辑/详情子路由', () => {
    expect(routesCode).toContain("'products/new'")
    expect(routesCode).toContain("'products/:id/edit'")
    expect(routesCode).toContain("'customers/new'")
    expect(routesCode).toContain("'customers/:id'")
    expect(routesCode).toContain("'orders/new'")
    expect(routesCode).toContain("'orders/:id'")
  })

  it('通配符路由使用 NotFound 页面', () => {
    expect(routesCode).toContain("path: '*'")
    expect(routesCode).toContain("import('@/pages/NotFound')")
  })

  it('AppLayout 使用 Outlet 渲染子路由', () => {
    expect(layoutCode).toContain("import { Outlet")
    expect(layoutCode).toContain('<Outlet />')
  })
})
