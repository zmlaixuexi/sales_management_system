/**
 * 代码质量：前端路由守卫与菜单配置一致性验证测试
 * 覆盖 ProtectedRoute 鉴权逻辑、路由结构与菜单项对齐、
 * 公开路由无需认证、菜单图标与路由路径匹配、路由守卫边界
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const ROOT = resolve(import.meta.dirname, '..', '..', '..')

function read(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf-8')
}

const ROUTES = 'frontend/src/routes/index.tsx'
const PROTECTED = 'frontend/src/routes/ProtectedRoute.tsx'
const LAYOUT = 'frontend/src/routes/AppLayout.tsx'
const MAIN = 'frontend/src/main.tsx'

// ═══════════════════════════════════════════════════════════
// 1. ProtectedRoute 鉴权逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('ProtectedRoute 鉴权逻辑', () => {
  it('无 token 时重定向到 /login', () => {
    const src = read(PROTECTED)
    expect(src).toContain('!token')
    expect(src).toMatch(/Navigate\s+to="\/login"/)
  })

  it('有 token 但无 user 时加载用户信息', () => {
    const src = read(PROTECTED)
    expect(src).toContain('fetchUser')
    expect(src).toContain('token && !user')
  })

  it('加载中显示 Spin 组件', () => {
    const src = read(PROTECTED)
    expect(src).toContain('Spin')
    expect(src).toContain('loading')
  })

  it('使用 useAuthStore 获取认证状态', () => {
    const src = read(PROTECTED)
    expect(src).toContain('useAuthStore')
    expect(src).toContain('token')
    expect(src).toContain('user')
  })

  it('user 为 null 时重定向到 /login', () => {
    const src = read(PROTECTED)
    expect(src).toContain('!user')
    expect(src).toMatch(/Navigate\s+to="\/login"/)
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 路由结构与菜单项对齐验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('路由结构与菜单项对齐', () => {
  it('AppLayout 菜单项数量与路由子路由数量合理', () => {
    const layout = read(LAYOUT)
    const routes = read(ROUTES)
    // 菜单项
    const menuKeys = layout.match(/key:\s*['"]([^'"]+)['"]/g) || []
    // 路由路径
    const routePaths = routes.match(/path:\s*['"]([^'"]+)['"]/g) || []
    // 菜单项数应 <= 路由数（含表单/详情等非菜单路由）
    expect(menuKeys.length).toBeGreaterThanOrEqual(8)
    expect(routePaths.length).toBeGreaterThanOrEqual(menuKeys.length)
  })

  it('菜单关键路径与路由定义完全匹配', () => {
    const layout = read(LAYOUT)
    const routes = read(ROUTES)
    const menuKeys = (layout.match(/key:\s*['"]([^'"]+)['"]/g) || [])
      .map((k: string) => k.match(/['"]([^'"]+)['"]/)![1])
    for (const key of menuKeys) {
      // 菜单 key 如 '/products' 对应路由 path 'products'
      const routePath = key === '/' ? 'index' : key.replace(/^\//, '')
      const searchPattern = key === '/' ? 'index: true' : `'${routePath}'`
      expect(routes, `路由中应包含菜单路径 ${key} (查找 ${searchPattern})`).toContain(searchPattern)
    }
  })

  it('Dashboard 首页路由使用 index 路由', () => {
    const routes = read(ROUTES)
    expect(routes).toContain("index: true")
  })

  it('AppLayout 菜单项包含所有核心业务模块', () => {
    const layout = read(LAYOUT)
    for (const key of ['/products', '/customers', '/orders', '/payments', '/inventory', '/reports', '/users', '/roles']) {
      expect(layout, `菜单应包含 ${key}`).toContain(key)
    }
  })

  it('菜单使用 antd Menu 组件渲染', () => {
    const layout = read(LAYOUT)
    expect(layout).toContain('<Menu')
    expect(layout).toContain('menuItems')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 公开路由无需认证验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('公开路由无需认证', () => {
  it('/login 路由不包裹 ProtectedRoute', () => {
    const routes = read(ROUTES)
    const loginBlock = routes.match(/path:\s*['"]\/login['"][\s\S]*?element:\s*\S+/)
    expect(loginBlock).toBeTruthy()
    expect(loginBlock![0]).not.toContain('ProtectedRoute')
  })

  it('NotFound 路由不包裹 ProtectedRoute', () => {
    const routes = read(ROUTES)
    const notFoundBlock = routes.match(/path:\s*['"]\*['"][\s\S]*?element:\s*\S+/)
    expect(notFoundBlock).toBeTruthy()
    expect(notFoundBlock![0]).not.toContain('ProtectedRoute')
  })

  it('业务路由包裹 ProtectedRoute', () => {
    const routes = read(ROUTES)
    expect(routes).toContain('<ProtectedRoute>')
  })

  it('业务路由嵌套在 ProtectedRoute 内作为子路由', () => {
    const routes = read(ROUTES)
    // 应有 children: [...] 在 ProtectedRoute 内
    expect(routes).toContain('children:')
  })

  it('ProtectedRoute 使用 Navigate 组件实现重定向', () => {
    const src = read(PROTECTED)
    expect(src).toContain('Navigate')
    expect(src).toContain("replace")
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 菜单图标与路由路径匹配验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('菜单图标与路由路径匹配', () => {
  it('每个菜单项都有 icon 属性', () => {
    const layout = read(LAYOUT)
    const menuItems = layout.match(/\{[^}]*key:\s*['"][^'"]+['"][^}]*\}/g) || []
    for (const item of menuItems) {
      if (item.includes('label')) {
        expect(item, `菜单项 ${item.slice(0, 40)} 应有 icon`).toContain('icon:')
      }
    }
  })

  it('每个菜单项都有 label 属性', () => {
    const layout = read(LAYOUT)
    const menuItems = layout.match(/\{[^}]*key:\s*['"][^'"]+['"][^}]*\}/g) || []
    for (const item of menuItems) {
      if (item.includes('icon')) {
        expect(item, `菜单项应有 label`).toContain('label:')
      }
    }
  })

  it('菜单标签使用中文', () => {
    const layout = read(LAYOUT)
    const labels = layout.match(/label:\s*'([^']+)'/g) || []
    for (const label of labels) {
      const text = label.match(/'([^']+)'/)![1]
      expect(text, `标签 ${text} 应包含中文`).toMatch(/[一-鿿]/)
    }
  })

  it('使用 antd 图标组件', () => {
    const layout = read(LAYOUT)
    expect(layout).toContain('@ant-design/icons')
    expect(layout).toContain('Outlined')
  })

  it('AppLayout 使用 useLocation 实现菜单高亮', () => {
    const layout = read(LAYOUT)
    expect(layout).toContain('useLocation')
    expect(layout).toContain('selectedKeys')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 路由守卫边界验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('路由守卫边界', () => {
  it('所有路由使用 lazyPage 动态加载', () => {
    const routes = read(ROUTES)
    const lazyCount = (routes.match(/lazyPage\(/g) || []).length
    expect(lazyCount).toBeGreaterThanOrEqual(17)
  })

  it('路由配置使用 React Router RouteObject 类型', () => {
    const routes = read(ROUTES)
    expect(routes).toContain('RouteObject')
  })

  it('AppLayout 退出登录清除 token 并导航', () => {
    const layout = read(LAYOUT)
    expect(layout).toContain("localStorage.removeItem('access_token')")
    expect(layout).toContain("localStorage.removeItem('refresh_token')")
    expect(layout).toContain("navigate('/login')")
  })

  it('路由配置导出为数组', () => {
    const routes = read(ROUTES)
    expect(routes).toContain('export default routes')
  })

  it('应用入口使用 ErrorBoundary 包裹路由', () => {
    const main = read(MAIN)
    expect(main).toContain('ErrorBoundary')
  })
})
