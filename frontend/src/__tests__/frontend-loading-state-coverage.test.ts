/**
 * 可观测性：前端组件 loading 状态覆盖验证测试
 * 覆盖列表页 loading 绑定、表单页 loading/submitting、
 * 详情页加载态、操作按钮 loading、路由级 Suspense fallback
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const ROOT = resolve(import.meta.dirname, '..', '..', '..')

function read(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf-8')
}

const pages = [
  'frontend/src/pages/Customers.tsx',
  'frontend/src/pages/Products.tsx',
  'frontend/src/pages/Orders.tsx',
  'frontend/src/pages/Payments.tsx',
  'frontend/src/pages/Inventory.tsx',
  'frontend/src/pages/AuditLogs.tsx',
  'frontend/src/pages/Users.tsx',
] as const

const formPages = [
  'frontend/src/pages/CustomerForm.tsx',
  'frontend/src/pages/ProductForm.tsx',
  'frontend/src/pages/OrderForm.tsx',
] as const

// ═══════════════════════════════════════════════════════════
// 1. 列表页 usePaginatedList loading 绑定验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('列表页 usePaginatedList loading 绑定', () => {
  it('所有列表页使用 usePaginatedList 获取 loading', () => {
    for (const p of pages) {
      const src = read(p)
      expect(src, `${p} 应使用 usePaginatedList`).toContain('usePaginatedList')
      expect(src, `${p} 应解构 loading`).toMatch(/const\s*\{[^}]*loading/)
    }
  })

  it('所有列表页将 loading 绑定到 Table 组件', () => {
    for (const p of pages) {
      const src = read(p)
      expect(src, `${p} 应将 loading 传递给 Table`).toMatch(
        /<Table[\s\S]*?loading=\{loading\}/,
      )
    }
  })

  it('usePaginatedList 内部管理 loading 状态', () => {
    const src = read('frontend/src/hooks/usePaginatedList.ts')
    expect(src).toContain('const [loading, setLoading] = useState(false)')
    expect(src).toContain('setLoading(true)')
    expect(src).toContain('setLoading(false)')
  })

  it('usePaginatedList 返回 loading 和 error', () => {
    const src = read('frontend/src/hooks/usePaginatedList.ts')
    expect(src).toMatch(/return\s*\{[^}]*loading/)
    expect(src).toMatch(/return\s*\{[^}]*error/)
  })

  it('usePaginatedList 请求失败时设置 error 为 true', () => {
    const src = read('frontend/src/hooks/usePaginatedList.ts')
    expect(src).toContain('setError(true)')
    expect(src).toContain('setError(false)')
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 表单页 loading + submitting 双重状态验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('表单页 loading + submitting 双重状态', () => {
  it('所有表单页使用 useState 管理初始加载 loading', () => {
    for (const p of formPages) {
      const src = read(p)
      expect(src, `${p} 应有 loading useState`).toMatch(
        /const\s*\[\s*loading\s*,\s*setLoading\s*\]\s*=\s*useState\(false\)/,
      )
    }
  })

  it('所有表单页使用 useSubmit 获取 submitting', () => {
    for (const p of formPages) {
      const src = read(p)
      expect(src, `${p} 应使用 useSubmit`).toContain('useSubmit')
      expect(src, `${p} 应解构 submitting`).toMatch(/submitting/)
    }
  })

  it('所有表单页将 loading || submitting 绑定到 Card', () => {
    for (const p of formPages) {
      const src = read(p)
      expect(src, `${p} 应将 loading||submitting 绑到 Card`).toMatch(
        /<Card[\s\S]*?loading=\{loading\s*\|\|\s*submitting\}/,
      )
    }
  })

  it('所有表单页提交按钮使用 loading || submitting', () => {
    for (const p of formPages) {
      const src = read(p)
      expect(src, `${p} 提交按钮应有 loading 状态`).toMatch(
        /<Button[\s\S]*?loading=\{loading\s*\|\|\s*submitting\}/,
      )
    }
  })

  it('useSubmit 内部实现防重复提交', () => {
    const src = read('frontend/src/hooks/useSubmit.ts')
    expect(src).toContain('locked')
    expect(src).toContain('locked.current = true')
    expect(src).toContain('if (locked.current) return')
    expect(src).toContain('locked.current = false')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 详情页加载态验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('详情页加载态', () => {
  const detailPages = [
    'frontend/src/pages/CustomerDetail.tsx',
    'frontend/src/pages/OrderDetail.tsx',
  ]

  it('详情页使用 useState 管理 loading 状态', () => {
    for (const p of detailPages) {
      const src = read(p)
      expect(src, `${p} 应有 loading useState`).toMatch(
        /const\s*\[\s*loading\s*,\s*setLoading\s*\]\s*=\s*useState\(false\)/,
      )
    }
  })

  it('详情页将 loading 绑定到 Card 组件', () => {
    for (const p of detailPages) {
      const src = read(p)
      expect(src, `${p} 应将 loading 传给 Card`).toMatch(
        /<Card[\s\S]*?loading=\{loading\}/,
      )
    }
  })

  it('详情页数据加载前 setLoading(true)、完成后 setLoading(false)', () => {
    for (const p of detailPages) {
      const src = read(p)
      expect(src, `${p} 应设置 setLoading(true)`).toContain('setLoading(true)')
      expect(src, `${p} 应设置 setLoading(false)`).toContain('setLoading(false)')
    }
  })

  it('Dashboard 页面使用 Spin 包裹加载态', () => {
    const src = read('frontend/src/pages/Dashboard.tsx')
    expect(src).toContain('useState(false)')
    expect(src).toMatch(/<Spin[\s\S]*?spinning=\{loading\}/)
  })

  it('ReportsCenter 页面使用 string-keyed loading 管理多个区域', () => {
    const src = read('frontend/src/pages/ReportsCenter.tsx')
    expect(src).toMatch(/useState<string\s*\|\s*null>\(null\)/)
    // 至少 4 个区域使用 loading 判断
    const matches = src.match(/loading\s*===\s*['"]/g)
    expect(matches, 'ReportsCenter 应有多个 loading 区域判断').toBeTruthy()
    expect(matches!.length).toBeGreaterThanOrEqual(4)
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 操作按钮 loading 状态验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('操作按钮 loading 状态', () => {
  it('Login 页面登录按钮绑定 loading', () => {
    const src = read('frontend/src/pages/Login.tsx')
    expect(src).toMatch(/const\s*\[\s*loading\s*,\s*setLoading\s*\]\s*=\s*useState\(false\)/)
    expect(src).toMatch(/<Button[\s\S]*?loading=\{loading\}/)
    expect(src).toContain('setLoading(true)')
    expect(src).toContain('setLoading(false)')
  })

  it('CustomerDetail 删除按钮有独立 deleting 状态', () => {
    const src = read('frontend/src/pages/CustomerDetail.tsx')
    expect(src).toMatch(/const\s*\[\s*deleting\s*,\s*setDeleting\s*\]/)
    expect(src).toMatch(/<Button[\s\S]*?loading=\{deleting\}/)
  })

  it('OrderDetail 操作按钮使用 actionLoading 字符串键', () => {
    const src = read('frontend/src/pages/OrderDetail.tsx')
    expect(src).toMatch(/actionLoading/)
    expect(src).toMatch(/loading=\{actionLoading\s*===\s*['"]/)
  })

  it('Users 页面 Modal 确认按钮使用 saving 状态', () => {
    const src = read('frontend/src/pages/Users.tsx')
    expect(src).toMatch(/const\s*\[\s*saving\s*,\s*setSaving\s*\]/)
    expect(src).toMatch(/confirmLoading=\{saving\}/)
  })

  it('Roles 页面 Modal 确认按钮使用 saving 状态', () => {
    const src = read('frontend/src/pages/Roles.tsx')
    expect(src).toMatch(/const\s*\[\s*saving\s*,\s*setSaving\s*\]/)
    expect(src).toMatch(/confirmLoading=\{saving\}/)
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 路由级 Suspense fallback 验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('路由级 Suspense fallback', () => {
  const routesFile = 'frontend/src/routes/index.tsx'

  it('路由配置定义了 Loading 组件', () => {
    const src = read(routesFile)
    expect(src).toMatch(/const\s+Loading\s*=/)
    expect(src).toContain('<Spin size="large" />')
  })

  it('lazyPage 函数包裹 Suspense + Loading fallback', () => {
    const src = read(routesFile)
    expect(src).toContain('function lazyPage')
    expect(src).toMatch(/<Suspense\s+fallback=\{<Loading\s*\/>\}>/)
  })

  it('所有路由使用 lazyPage 加载页面组件', () => {
    const src = read(routesFile)
    const lazyCount = (src.match(/lazyPage\(/g) || []).length
    expect(lazyCount, '应有至少 17 个 lazyPage 调用').toBeGreaterThanOrEqual(17)
  })

  it('Loading 组件居中显示并占据合理高度', () => {
    const src = read(routesFile)
    expect(src).toContain('justifyContent')
    expect(src).toContain('alignItems')
    expect(src).toMatch(/height:\s*['"]?\d+vh['"]?/)
  })

  it('ErrorBoundary 包裹路由作为全局兜底', () => {
    const src = read('frontend/src/main.tsx')
    expect(src).toContain('ErrorBoundary')
    expect(src).toContain('react-router-dom')
  })
})
