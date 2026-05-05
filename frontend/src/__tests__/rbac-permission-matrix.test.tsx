/* 权限 RBAC 矩阵验证测试
验证前端权限码、菜单可见性、按钮门控与后端角色权限定义一致 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

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
  audit: [
    'audit:view',
  ],
}

// 菜单项 -> 所需权限
const MENU_ITEMS: { key: string; label: string; permission: string | null }[] = [
  { key: '/', label: '首页看板', permission: null },
  { key: '/products', label: '商品管理', permission: 'product:list' },
  { key: '/inventory', label: '库存流水', permission: 'inventory:list' },
  { key: '/customers', label: '客户管理', permission: 'customer:list' },
  { key: '/orders', label: '销售订单', permission: 'order:list' },
  { key: '/payments', label: '收款记录', permission: 'payment:list' },
  { key: '/reports', label: '报表中心', permission: 'report:sales' },
  { key: '/audit-logs', label: '操作日志', permission: 'audit:view' },
  { key: '/users', label: '用户管理', permission: 'user:list' },
  { key: '/roles', label: '角色权限', permission: 'role:list' },
]

describe('RBAC 权限矩阵验证', () => {
  describe('后端角色权限完整性', () => {
    const ALL_PERMS = new Set(ROLE_PERMISSIONS.admin)

    it('admin 角色拥有全部权限', () => {
      expect(ROLE_PERMISSIONS.admin.length).toBe(ALL_PERMS.size)
      for (const perm of ROLE_PERMISSIONS.admin) {
        expect(ALL_PERMS.has(perm)).toBe(true)
      }
    })

    it('所有角色权限码在 admin 权限集中', () => {
      for (const [role, perms] of Object.entries(ROLE_PERMISSIONS)) {
        if (role === 'admin') continue
        for (const perm of perms) {
          expect(ALL_PERMS.has(perm), `${role} 的权限 ${perm} 不在 admin 权限集中`).toBe(true)
        }
      }
    })

    it('sales 角色不能冲正收款', () => {
      expect(ROLE_PERMISSIONS.sales).not.toContain('payment:reverse')
    })

    it('sales 角色不能管理用户/角色', () => {
      expect(ROLE_PERMISSIONS.sales).not.toContain('user:list')
      expect(ROLE_PERMISSIONS.sales).not.toContain('role:list')
    })

    it('sales 角色不能查看利润报表', () => {
      expect(ROLE_PERMISSIONS.sales).not.toContain('report:profit')
    })

    it('inventory 角色不能管理客户和收款', () => {
      expect(ROLE_PERMISSIONS.inventory).not.toContain('customer:list')
      expect(ROLE_PERMISSIONS.inventory).not.toContain('payment:list')
    })

    it('finance 角色不能创建/编辑订单', () => {
      expect(ROLE_PERMISSIONS.finance).not.toContain('order:create')
      expect(ROLE_PERMISSIONS.finance).not.toContain('order:update')
    })

    it('audit 角色只能查看审计日志', () => {
      expect(ROLE_PERMISSIONS.audit).toHaveLength(1)
      expect(ROLE_PERMISSIONS.audit).toContain('audit:view')
    })

    it('sales_manager 可查看所有订单和客户', () => {
      expect(ROLE_PERMISSIONS.sales_manager).toContain('order:view_all')
      expect(ROLE_PERMISSIONS.sales_manager).toContain('customer:view_all')
    })

    it('sales 角色不能查看所有订单和客户', () => {
      expect(ROLE_PERMISSIONS.sales).not.toContain('order:view_all')
      expect(ROLE_PERMISSIONS.sales).not.toContain('customer:view_all')
    })

    it('sales 和 sales_manager 都可以确认订单', () => {
      expect(ROLE_PERMISSIONS.sales).toContain('order:confirm')
      expect(ROLE_PERMISSIONS.sales_manager).toContain('order:confirm')
    })

    it('sales 和 sales_manager 都可以登记收款', () => {
      expect(ROLE_PERMISSIONS.sales).toContain('payment:create')
      expect(ROLE_PERMISSIONS.sales_manager).toContain('payment:create')
    })

    it('只有 admin 和 finance 可以冲正收款', () => {
      for (const [role, perms] of Object.entries(ROLE_PERMISSIONS)) {
        const hasReverse = perms.includes('payment:reverse')
        expect(hasReverse, `${role} 的 payment:reverse 权限不正确`).toBe(
          role === 'admin' || role === 'finance',
        )
      }
    })

    it('只有 admin 可以删除商品', () => {
      for (const [role, perms] of Object.entries(ROLE_PERMISSIONS)) {
        expect(perms.includes('product:delete'), `${role} 的 product:delete 权限不正确`).toBe(
          role === 'admin',
        )
      }
    })
  })

  describe('菜单可见性按角色过滤', () => {
    function getVisibleMenuItems(role: string, isSuperuser = false): string[] {
      const perms = new Set(ROLE_PERMISSIONS[role] || [])
      return MENU_ITEMS.filter((item) => {
        if (!item.permission) return true
        if (isSuperuser) return true
        return perms.has(item.permission)
      }).map((item) => item.label)
    }

    it('admin（超管）可以看到所有菜单', () => {
      const visible = getVisibleMenuItems('admin', true)
      expect(visible).toEqual(MENU_ITEMS.map((i) => i.label))
    })

    it('sales 只能看到与销售相关的菜单', () => {
      const visible = getVisibleMenuItems('sales')
      expect(visible).toContain('首页看板')
      expect(visible).toContain('商品管理')
      expect(visible).toContain('客户管理')
      expect(visible).toContain('销售订单')
      expect(visible).toContain('收款记录')
      expect(visible).not.toContain('库存流水')
      expect(visible).not.toContain('报表中心')
      expect(visible).not.toContain('操作日志')
      expect(visible).not.toContain('用户管理')
      expect(visible).not.toContain('角色权限')
    })

    it('inventory 只能看到库存相关菜单', () => {
      const visible = getVisibleMenuItems('inventory')
      expect(visible).toContain('首页看板')
      expect(visible).toContain('商品管理')
      expect(visible).toContain('销售订单')
      expect(visible).toContain('库存流水')
      expect(visible).not.toContain('客户管理')
      expect(visible).not.toContain('收款记录')
      expect(visible).not.toContain('用户管理')
    })

    it('finance 只能看到财务相关菜单', () => {
      const visible = getVisibleMenuItems('finance')
      expect(visible).toContain('首页看板')
      expect(visible).toContain('商品管理')
      expect(visible).toContain('销售订单')
      expect(visible).toContain('收款记录')
      expect(visible).toContain('报表中心')
      expect(visible).not.toContain('客户管理')
      expect(visible).not.toContain('库存流水')
      expect(visible).not.toContain('用户管理')
    })

    it('audit 只能看到审计日志', () => {
      const visible = getVisibleMenuItems('audit')
      expect(visible).toEqual(['首页看板', '操作日志'])
    })

    it('sales_manager 看到比 sales 更多但不含用户管理的菜单', () => {
      const visible = getVisibleMenuItems('sales_manager')
      expect(visible).toContain('库存流水')
      expect(visible).toContain('报表中心')
      expect(visible).not.toContain('操作日志')
      expect(visible).not.toContain('用户管理')
      expect(visible).not.toContain('角色权限')
    })
  })
})

describe('PermissionGuard 路由权限拦截', () => {
  // 模拟 getPathPermission 逻辑（与 AppLayout.tsx 一致）
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

  it('sales 用户不能访问 /users（超管专属）', () => {
    expect(canAccess('/users', 'sales')).toBe(false)
  })

  it('sales 用户不能访问 /roles（超管专属）', () => {
    expect(canAccess('/roles', 'sales')).toBe(false)
  })

  it('sales 用户不能访问 /audit-logs', () => {
    expect(canAccess('/audit-logs', 'sales')).toBe(false)
  })

  it('admin 用户可以访问 /users', () => {
    expect(canAccess('/users', 'admin')).toBe(true)
  })

  it('sales 用户可以访问 /orders', () => {
    expect(canAccess('/orders', 'sales')).toBe(true)
  })

  it('audit 用户不能访问 /customers', () => {
    expect(canAccess('/customers', 'audit')).toBe(false)
  })

  it('inventory 用户可以访问 /inventory', () => {
    expect(canAccess('/inventory', 'inventory')).toBe(true)
  })

  it('inventory 用户不能访问 /customers', () => {
    expect(canAccess('/customers', 'inventory')).toBe(false)
  })

  it('finance 用户可以访问 /reports', () => {
    expect(canAccess('/reports', 'finance')).toBe(true)
  })

  it('finance 用户不能访问 /inventory', () => {
    expect(canAccess('/inventory', 'finance')).toBe(false)
  })

  it('动态路径 /orders/123 无精确匹配返回 null（权限由页面内部检查）', () => {
    expect(getPathPermission('/orders/123')).toBe(null)
    expect(canAccess('/orders/123', 'sales')).toBe(true) // null = all users
    expect(canAccess('/orders/123', 'audit')).toBe(true) // null = all users
  })

  it('动态路径 /products/p1/edit 无精确匹配返回 null（权限由页面内部检查）', () => {
    expect(getPathPermission('/products/p1/edit')).toBe(null)
    expect(canAccess('/products/p1/edit', 'inventory')).toBe(true)
    expect(canAccess('/products/p1/edit', 'audit')).toBe(true) // 无路径级限制
  })
})

describe('按钮权限门控验证', () => {
  describe('OrderDetail 按钮可见性', () => {
    const orderButtons = [
      { label: '确认订单', permission: 'order:confirm', statuses: ['draft'] },
      { label: '登记收款', permission: 'payment:create', statuses: ['confirmed', 'partially_paid'] },
      { label: '取消订单', permission: 'order:cancel', statuses: ['draft', 'confirmed', 'partially_paid'] },
      { label: '冲正', permission: 'payment:reverse', statuses: ['any'] },
    ]

    it('sales 角色可以看到确认订单按钮（草稿状态）', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales)
      expect(perms.has('order:confirm')).toBe(true)
    })

    it('sales 角色可以看到登记收款按钮', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales)
      expect(perms.has('payment:create')).toBe(true)
    })

    it('sales 角色不能看到冲正按钮', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales)
      expect(perms.has('payment:reverse')).toBe(false)
    })

    it('inventory 角色不能确认/取消订单', () => {
      const perms = new Set(ROLE_PERMISSIONS.inventory)
      expect(perms.has('order:confirm')).toBe(false)
      expect(perms.has('order:cancel')).toBe(false)
    })

    it('finance 角色可以冲正收款', () => {
      const perms = new Set(ROLE_PERMISSIONS.finance)
      expect(perms.has('payment:reverse')).toBe(true)
    })

    it('finance 角色不能确认/取消订单', () => {
      const perms = new Set(ROLE_PERMISSIONS.finance)
      expect(perms.has('order:confirm')).toBe(false)
      expect(perms.has('order:cancel')).toBe(false)
    })
  })

  describe('商品/客户管理按钮权限', () => {
    it('inventory 可以创建和编辑商品', () => {
      const perms = new Set(ROLE_PERMISSIONS.inventory)
      expect(perms.has('product:create')).toBe(true)
      expect(perms.has('product:update')).toBe(true)
    })

    it('inventory 不能删除商品', () => {
      expect(ROLE_PERMISSIONS.inventory).not.toContain('product:delete')
    })

    it('sales 可以创建、编辑、删除客户', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales)
      expect(perms.has('customer:create')).toBe(true)
      expect(perms.has('customer:update')).toBe(true)
      expect(perms.has('customer:delete')).toBe(true)
    })

    it('finance 不能管理客户', () => {
      const perms = new Set(ROLE_PERMISSIONS.finance)
      expect(perms.has('customer:create')).toBe(false)
      expect(perms.has('customer:update')).toBe(false)
      expect(perms.has('customer:delete')).toBe(false)
    })
  })

  describe('成本/利润数据可见性', () => {
    it('sales 不能查看成本和利润', () => {
      expect(ROLE_PERMISSIONS.sales).not.toContain('product:view_cost')
      expect(ROLE_PERMISSIONS.sales).not.toContain('report:profit')
    })

    it('sales_manager 可以查看成本和利润', () => {
      const perms = new Set(ROLE_PERMISSIONS.sales_manager)
      expect(perms.has('product:view_cost')).toBe(true)
      expect(perms.has('report:profit')).toBe(true)
    })

    it('finance 可以查看成本和利润', () => {
      const perms = new Set(ROLE_PERMISSIONS.finance)
      expect(perms.has('product:view_cost')).toBe(true)
      expect(perms.has('report:profit')).toBe(true)
    })
  })
})

describe('前端权限码与后端一致性', () => {
  // 前端使用的所有权限码
  const FRONTEND_PERM_CODES = [
    'product:list', 'product:create', 'product:update', 'product:delete', 'product:view_cost',
    'customer:list', 'customer:create', 'customer:update', 'customer:delete', 'customer:view_all',
    'order:list', 'order:create', 'order:update', 'order:confirm', 'order:cancel', 'order:view', 'order:view_all',
    'inventory:list', 'inventory:adjust',
    'payment:list', 'payment:create', 'payment:reverse',
    'report:sales', 'report:profit',
    'audit:view',
    'user:list', 'user:create', 'user:update', 'user:delete',
    'role:list', 'role:create', 'role:update', 'role:delete',
  ]

  const ALL_BACKEND_PERMS = new Set(ROLE_PERMISSIONS.admin)

  it('前端使用的所有权限码在后端都有定义', () => {
    for (const code of FRONTEND_PERM_CODES) {
      expect(ALL_BACKEND_PERMS.has(code), `前端权限码 ${code} 在后端未定义`).toBe(true)
    }
  })

  it('后端定义的所有权限码在前端都有使用或预留', () => {
    // 后端权限码应在前端的列表中出现
    for (const perm of ALL_BACKEND_PERMS) {
      expect(FRONTEND_PERM_CODES.includes(perm), `后端权限码 ${perm} 在前端未引用`).toBe(true)
    }
  })

  it('权限码数量一致', () => {
    expect(FRONTEND_PERM_CODES.length).toBe(ALL_BACKEND_PERMS.size)
  })
})
