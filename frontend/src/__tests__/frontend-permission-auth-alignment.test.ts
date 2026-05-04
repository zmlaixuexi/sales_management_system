/**
 * 代码质量：前端权限码与后端权限定义对齐验证测试
 * 覆盖前端 hasPermission 调用码在后端存在、
 * CurrentUser 接口与后端 /auth/me 响应对齐、
 * auth store 逻辑正确性、ProtectedRoute 鉴权行为
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')

function backendSrc(module: string): string {
  return readFileSync(resolve(root, 'backend', 'app', module), 'utf-8')
}

function frontendSrc(module: string): string {
  return readFileSync(resolve(root, 'frontend/src', module), 'utf-8')
}

/** 从后端源码中提取所有 require_permission("xxx") 和 has_permission(..., "xxx") 中的权限码 */
function extractBackendPermissions(): Set<string> {
  const modules = [
    'api/v1/products.py', 'api/v1/customers.py', 'api/v1/orders.py',
    'api/v1/payments.py', 'api/v1/inventory.py', 'api/v1/audit_logs.py',
    'api/v1/reports.py', 'api/v1/exports.py', 'api/v1/files.py',
    'api/v1/users.py', 'api/v1/roles.py', 'db/seed.py',
  ]
  const perms = new Set<string>()
  for (const mod of modules) {
    const source = backendSrc(mod)
    for (const m of source.matchAll(/require_permission\("([^"]+)"\)/g)) perms.add(m[1])
    for (const m of source.matchAll(/has_permission\([^,]+,\s*"([^"]+)"\)/g)) perms.add(m[1])
  }
  return perms
}

/** 从前端页面源码中提取所有 hasPermission('xxx') 中的权限码 */
function extractFrontendPermissionUsages(): Map<string, string[]> {
  const pages = [
    'pages/Products.tsx', 'pages/Orders.tsx', 'pages/OrderDetail.tsx',
    'pages/Dashboard.tsx', 'pages/Customers.tsx', 'pages/Payments.tsx',
    'pages/Inventory.tsx', 'pages/Users.tsx', 'pages/Roles.tsx',
    'pages/AuditLogs.tsx', 'pages/ReportsCenter.tsx',
    'pages/CustomerDetail.tsx', 'pages/CustomerForm.tsx',
    'pages/OrderForm.tsx', 'pages/ProductForm.tsx',
  ]
  const usages = new Map<string, string[]>()
  for (const page of pages) {
    try {
      const source = frontendSrc(page)
      const matches = [...source.matchAll(/hasPermission\(['"]([^'"]+)['"]\)/g)]
      for (const m of matches) {
        const code = m[1]
        if (!usages.has(code)) usages.set(code, [])
        usages.get(code)!.push(page.replace('pages/', ''))
      }
    } catch {
      // 页面不存在时跳过
    }
  }
  return usages
}

// ═══════════════════════════════════════════════════════════
// 1. 前端权限码在后端存在验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('前端权限码在后端存在', () => {
  const backendPerms = extractBackendPermissions()
  const frontendUsages = extractFrontendPermissionUsages()

  it('后端至少定义 20 个权限码', () => {
    expect(backendPerms.size).toBeGreaterThanOrEqual(20)
  })

  it('product:view_cost 在后端权限中存在', () => {
    expect(backendPerms.has('product:view_cost')).toBe(true)
  })

  it('report:profit 在后端权限中存在', () => {
    expect(backendPerms.has('report:profit')).toBe(true)
  })

  it('所有前端使用的权限码在后端均有定义', () => {
    for (const [code, pages] of frontendUsages) {
      expect(backendPerms.has(code), `前端权限码 "${code}"（用于 ${pages.join(', ')}）在后端未找到`).toBe(true)
    }
  })

  it('前端权限码数量不超过后端定义数量', () => {
    expect(frontendUsages.size).toBeLessThanOrEqual(backendPerms.size)
  })
})

// ═══════════════════════════════════════════════════════════
// 2. CurrentUser 接口与后端响应对齐验证（6 项）
// ═══════════════════════════════════════════════════════════

describe('CurrentUser 接口与后端 /auth/me 响应对齐', () => {
  const authApiCode = frontendSrc('api/auth.ts')
  const backendAuthCode = backendSrc('api/v1/auth.py')
  const backendSchemaCode = backendSrc('schemas/auth.py')

  it('CurrentUser 包含 id/username/display_name/is_active/is_superuser/roles/permissions', () => {
    expect(authApiCode).toContain('id:')
    expect(authApiCode).toContain('username:')
    expect(authApiCode).toContain('display_name:')
    expect(authApiCode).toContain('is_active:')
    expect(authApiCode).toContain('is_superuser:')
    expect(authApiCode).toContain('roles:')
    expect(authApiCode).toContain('permissions:')
  })

  it('CurrentUser.roles 是对象数组包含 id/name/display_name', () => {
    expect(authApiCode).toMatch(/roles:\s*\{\s*id:\s*string/)
    expect(authApiCode).toMatch(/name:\s*string/)
    expect(authApiCode).toMatch(/display_name:\s*string/)
  })

  it('CurrentUser.permissions 是 string 数组', () => {
    expect(authApiCode).toContain('permissions: string[]')
  })

  it('后端 /auth/me 端点存在', () => {
    expect(backendAuthCode).toContain('def get_me(')
    expect(backendAuthCode).toContain('/me')
  })

  it('后端 /auth/me 返回 is_superuser 和 permissions', () => {
    expect(backendAuthCode).toContain('is_superuser')
    expect(backendAuthCode).toContain('permissions')
    expect(backendAuthCode).toContain('roles')
  })

  it('后端 login 返回 access_token 和 refresh_token', () => {
    expect(backendAuthCode).toContain('access_token')
    expect(backendAuthCode).toContain('refresh_token')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. auth store 逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('auth store 逻辑正确性', () => {
  const storeCode = frontendSrc('stores/auth.ts')

  it('hasPermission 对 is_superuser 返回 true', () => {
    expect(storeCode).toContain('is_superuser')
    expect(storeCode).toMatch(/is_superuser.*return true/)
  })

  it('hasPermission 检查 permissions.includes', () => {
    expect(storeCode).toContain('permissions.includes(code)')
  })

  it('logout 清除 token 和 user', () => {
    expect(storeCode).toMatch(/set\(\s*\{\s*token:\s*null/)
    expect(storeCode).toContain('user: null')
  })

  it('login 存储 access_token 和 refresh_token', () => {
    expect(storeCode).toContain("localStorage.setItem('access_token'")
    expect(storeCode).toContain("localStorage.setItem('refresh_token'")
  })

  it('fetchUser 失败时清除状态', () => {
    expect(storeCode).toMatch(/catch.*\{[^}]*token:\s*null/s)
  })
})

// ═══════════════════════════════════════════════════════════
// 4. ProtectedRoute 鉴权行为验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('ProtectedRoute 鉴权行为', () => {
  const prCode = frontendSrc('routes/ProtectedRoute.tsx')

  it('使用 useAuthStore 获取认证状态', () => {
    expect(prCode).toContain('useAuthStore')
  })

  it('检查 token 存在性', () => {
    expect(prCode).toMatch(/token/)
  })

  it('无 token 时重定向到 /login', () => {
    expect(prCode).toContain('/login')
    expect(prCode).toContain('Navigate')
  })

  it('有 token 但无 user 时调用 fetchUser', () => {
    expect(prCode).toContain('fetchUser')
  })

  it('加载中显示 Spin', () => {
    expect(prCode).toContain('Spin')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 后端权限码覆盖完整性验证（4 项）
// ═══════════════════════════════════════════════════════════

describe('后端权限码覆盖完整性', () => {
  const backendPerms = extractBackendPermissions()

  it('覆盖商品 CRUD 权限', () => {
    expect(backendPerms.has('product:list')).toBe(true)
    expect(backendPerms.has('product:create')).toBe(true)
    expect(backendPerms.has('product:update')).toBe(true)
    expect(backendPerms.has('product:delete')).toBe(true)
  })

  it('覆盖订单 CRUD + 确认/取消权限', () => {
    expect(backendPerms.has('order:list')).toBe(true)
    expect(backendPerms.has('order:create')).toBe(true)
    expect(backendPerms.has('order:update')).toBe(true)
    expect(backendPerms.has('order:confirm')).toBe(true)
    expect(backendPerms.has('order:cancel')).toBe(true)
    expect(backendPerms.has('order:view')).toBe(true)
  })

  it('覆盖收款和客户权限', () => {
    expect(backendPerms.has('payment:list')).toBe(true)
    expect(backendPerms.has('payment:create')).toBe(true)
    expect(backendPerms.has('payment:reverse')).toBe(true)
    expect(backendPerms.has('customer:list')).toBe(true)
    expect(backendPerms.has('customer:create')).toBe(true)
    expect(backendPerms.has('customer:update')).toBe(true)
    expect(backendPerms.has('customer:delete')).toBe(true)
  })

  it('覆盖报表、库存、审计权限', () => {
    expect(backendPerms.has('report:sales')).toBe(true)
    expect(backendPerms.has('report:profit')).toBe(true)
    expect(backendPerms.has('inventory:list')).toBe(true)
    expect(backendPerms.has('inventory:adjust')).toBe(true)
    expect(backendPerms.has('audit:view')).toBe(true)
  })
})
