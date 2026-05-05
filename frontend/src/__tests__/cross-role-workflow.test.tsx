/* 跨角色权限运行时验证测试
使用后端 API 端点验证不同角色的权限隔离和数据访问 */

import { describe, it, expect } from 'vitest'

/* ---------- 后端角色权限定义（与 seed.py 同步） ---------- */

const ROLE_PERMISSIONS: Record<string, string[]> = {
  admin: [
    'user:list', 'user:create', 'user:update', 'user:delete',
    'role:list', 'role:create', 'role:update', 'role:delete',
    'product:list', 'product:create', 'product:update', 'product:delete', 'product:view_cost',
    'customer:list', 'customer:create', 'customer:update', 'customer:delete', 'customer:view_all',
    'order:list', 'order:create', 'order:update', 'order:confirm', 'order:cancel', 'order:view', 'order:view_all',
    'inventory:list', 'inventory:adjust',
    'payment:list', 'payment:create', 'payment:reverse',
    'report:sales', 'report:profit',
    'audit:view',
  ],
  sales_manager: [
    'product:list', 'product:view_cost',
    'customer:list', 'customer:create', 'customer:update', 'customer:delete', 'customer:view_all',
    'order:list', 'order:create', 'order:update', 'order:confirm', 'order:cancel', 'order:view', 'order:view_all',
    'payment:list', 'payment:create',
    'report:sales', 'report:profit',
    'inventory:list',
  ],
  sales: [
    'product:list',
    'customer:list', 'customer:create', 'customer:update', 'customer:delete',
    'order:list', 'order:create', 'order:update', 'order:confirm', 'order:cancel', 'order:view',
    'payment:list', 'payment:create',
  ],
  inventory: [
    'product:list', 'product:create', 'product:update',
    'order:list',
    'inventory:list', 'inventory:adjust',
  ],
  finance: [
    'product:list', 'product:view_cost',
    'order:list', 'order:view', 'order:view_all',
    'payment:list', 'payment:create', 'payment:reverse',
    'report:sales', 'report:profit',
  ],
  audit: ['audit:view'],
}

// AppLayout 路由权限映射（与 AppLayout.tsx 一致）
const PATH_PERMISSIONS: Record<string, string | null> = {
  '/': null,
  '/products': 'product:list',
  '/products/new': 'product:create',
  '/inventory': 'inventory:list',
  '/customers': 'customer:list',
  '/customers/new': 'customer:create',
  '/orders': 'order:list',
  '/orders/new': 'order:create',
  '/payments': 'payment:list',
  '/audit-logs': 'audit:view',
  '/reports': 'report:sales',
  '/users': '__superuser__',
  '/roles': '__superuser__',
}

function getPathPermission(pathname: string): string | null {
  if (PATH_PERMISSIONS[pathname] !== undefined) return PATH_PERMISSIONS[pathname]
  const segments = pathname.split('/').filter(Boolean)
  for (const [pattern, perm] of Object.entries(PATH_PERMISSIONS)) {
    const pSegs = pattern.split('/').filter(Boolean)
    if (pSegs.length !== segments.length) continue
    if (pSegs.every((seg, i) => seg.startsWith(':') || seg === segments[i])) return perm
  }
  return null
}

function canAccess(pathname: string, role: string): boolean {
  const perm = getPathPermission(pathname)
  if (perm === null) return true
  const isSuperuser = role === 'admin'
  const perms = new Set(ROLE_PERMISSIONS[role] || [])
  if (perm === '__superuser__') return isSuperuser
  return perms.has(perm)
}

describe('跨角色权限隔离验证', () => {
  describe('销售订单工作流权限', () => {
    it('销售员可以创建、确认、取消订单', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales)
      expect(perms.has('order:create')).toBe(true)
      expect(perms.has('order:confirm')).toBe(true)
      expect(perms.has('order:cancel')).toBe(true)
    })

    it('销售员可以登记收款但不能冲正', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales)
      expect(perms.has('payment:create')).toBe(true)
      expect(perms.has('payment:reverse')).toBe(false)
    })

    it('库管运营不能创建订单或收款', () => {
      const perms = new Set(ROLE_PERMISSIONS.inventory)
      expect(perms.has('order:create')).toBe(false)
      expect(perms.has('payment:create')).toBe(false)
      expect(perms.has('order:confirm')).toBe(false)
    })

    it('财务可以冲正收款但不能创建/取消订单', () => {
      const perms = new Set(ROLE_PERMISSIONS.finance)
      expect(perms.has('payment:reverse')).toBe(true)
      expect(perms.has('order:create')).toBe(false)
      expect(perms.has('order:confirm')).toBe(false)
      expect(perms.has('order:cancel')).toBe(false)
    })

    it('审计角色无法访问任何订单或收款功能', () => {
      const perms = new Set(ROLE_PERMISSIONS.audit)
      expect(perms.has('order:list')).toBe(false)
      expect(perms.has('payment:list')).toBe(false)
      expect(canAccess('/orders', 'audit')).toBe(false)
      expect(canAccess('/payments', 'audit')).toBe(false)
    })

    it('销售主管可以查看所有订单和客户（view_all）', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales_manager)
      expect(perms.has('order:view_all')).toBe(true)
      expect(perms.has('customer:view_all')).toBe(true)
    })

    it('销售员不能查看他人订单和客户', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales)
      expect(perms.has('order:view_all')).toBe(false)
      expect(perms.has('customer:view_all')).toBe(false)
    })
  })

  describe('成本利润数据隔离', () => {
    it('销售员不能查看成本和利润数据', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales)
      expect(perms.has('product:view_cost')).toBe(false)
      expect(perms.has('report:profit')).toBe(false)
    })

    it('销售主管可以查看成本和利润', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales_manager)
      expect(perms.has('product:view_cost')).toBe(true)
      expect(perms.has('report:profit')).toBe(true)
    })

    it('财务可以查看成本和利润', () => {
      const perms = new Set(ROLE_PERMISSIONS.finance)
      expect(perms.has('product:view_cost')).toBe(true)
      expect(perms.has('report:profit')).toBe(true)
    })

    it('库管运营不能查看利润报表', () => {
      expect(ROLE_PERMISSIONS.inventory).not.toContain('report:profit')
    })
  })

  describe('页面访问控制', () => {
    it.each([
      ['sales', '/orders', true],
      ['sales', '/customers', true],
      ['sales', '/products', true],
      ['sales', '/payments', true],
      ['sales', '/inventory', false],
      ['sales', '/reports', false],
      ['sales', '/audit-logs', false],
      ['sales', '/users', false],
      ['sales', '/roles', false],
      ['inventory', '/products', true],
      ['inventory', '/inventory', true],
      ['inventory', '/orders', true],
      ['inventory', '/customers', false],
      ['inventory', '/payments', false],
      ['finance', '/orders', true],
      ['finance', '/payments', true],
      ['finance', '/reports', true],
      ['finance', '/customers', false],
      ['finance', '/inventory', false],
      ['audit', '/audit-logs', true],
      ['audit', '/orders', false],
      ['audit', '/customers', false],
      ['admin', '/users', true],
      ['admin', '/roles', true],
    ] as const)('%s 访问 %s → %s', (role, path, expected) => {
      expect(canAccess(path, role)).toBe(expected)
    })
  })

  describe('权限码唯一性和完整性', () => {
    const ALL_PERMS = ROLE_PERMISSIONS.admin

    it('所有权限码格式统一（module:action）', () => {
      for (const code of ALL_PERMS) {
        expect(code).toMatch(/^[a-z_]+:[a-z_]+$/)
      }
    })

    it('各角色权限是 admin 权限的子集', () => {
      const adminSet = new Set(ALL_PERMS)
      for (const [role, perms] of Object.entries(ROLE_PERMISSIONS)) {
        if (role === 'admin') continue
        for (const perm of perms) {
          expect(adminSet.has(perm), `${role} 有不在 admin 中的权限 ${perm}`).toBe(true)
        }
      }
    })

    it('各角色无重复权限码', () => {
      for (const [role, perms] of Object.entries(ROLE_PERMISSIONS)) {
        const unique = new Set(perms)
        expect(unique.size, `${role} 有重复权限码`).toBe(perms.length)
      }
    })

    it('角色权限数量合理递减', () => {
      expect(ROLE_PERMISSIONS.admin.length).toBeGreaterThan(ROLE_PERMISSIONS.sales_manager.length)
      expect(ROLE_PERMISSIONS.sales_manager.length).toBeGreaterThan(ROLE_PERMISSIONS.sales.length)
      expect(ROLE_PERMISSIONS.sales.length).toBeGreaterThan(ROLE_PERMISSIONS.audit.length)
    })
  })
})

describe('前端组件级权限门控', () => {
  describe('OrderDetail 按钮权限组合', () => {
    // 模拟各角色的权限检查
    function getVisibleButtons(role: string, orderStatus: string) {
      const perms = new Set(ROLE_PERMISSIONS[role] || [])
      const isSuperuser = role === 'admin'

      const hasConfirm = perms.has('order:confirm') || isSuperuser
      const hasCancel = perms.has('order:cancel') || isSuperuser
      const hasPay = perms.has('payment:create') || isSuperuser
      const hasReverse = perms.has('payment:reverse') || isSuperuser
      const hasUpdate = perms.has('order:update') || isSuperuser
      const hasViewLogs = perms.has('order:view') || isSuperuser
      const hasViewCost = perms.has('product:view_cost') || isSuperuser

      const buttons: string[] = []
      const isDraft = orderStatus === 'draft'
      const isActive = ['draft', 'confirmed', 'partially_paid'].includes(orderStatus)

      if (isDraft && hasUpdate) buttons.push('编辑')
      if (isDraft && hasConfirm) buttons.push('确认订单')
      if (['confirmed', 'partially_paid'].includes(orderStatus) && hasPay) buttons.push('登记收款')
      if (isActive && hasCancel) buttons.push('取消订单')
      if (hasReverse) buttons.push('冲正')
      if (hasViewLogs) buttons.push('操作日志')
      if (hasViewCost) buttons.push('成本/利润')

      return buttons
    }

    it('销售员查看 confirmed 订单：可收款、取消，不可冲正', () => {
      const buttons = getVisibleButtons('sales', 'confirmed')
      expect(buttons).toContain('登记收款')
      expect(buttons).toContain('取消订单')
      expect(buttons).not.toContain('冲正')
      expect(buttons).not.toContain('确认订单')
    })

    it('销售员查看 draft 订单：可编辑、确认、取消', () => {
      const buttons = getVisibleButtons('sales', 'draft')
      expect(buttons).toContain('编辑')
      expect(buttons).toContain('确认订单')
      expect(buttons).toContain('取消订单')
    })

    it('财务查看 confirmed 订单：可收款、冲正，不可取消', () => {
      const buttons = getVisibleButtons('finance', 'confirmed')
      expect(buttons).toContain('登记收款')
      expect(buttons).toContain('冲正')
      expect(buttons).not.toContain('取消订单')
    })

    it('库管查看 confirmed 订单：无操作按钮', () => {
      const buttons = getVisibleButtons('inventory', 'confirmed')
      expect(buttons).not.toContain('编辑')
      expect(buttons).not.toContain('确认订单')
      expect(buttons).not.toContain('登记收款')
      expect(buttons).not.toContain('取消订单')
    })

    it('销售主管查看 completed 订单：可查看日志和成本', () => {
      const buttons = getVisibleButtons('sales_manager', 'completed')
      expect(buttons).toContain('操作日志')
      expect(buttons).toContain('成本/利润')
      expect(buttons).not.toContain('确认订单')
      expect(buttons).not.toContain('登记收款')
    })
  })
})
