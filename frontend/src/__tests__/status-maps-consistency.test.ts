/**
 * 需求符合性：前端状态映射与后端状态常量一致性测试
 * 验证 statusMaps.ts 中的状态值与后端 model/schema 定义一致
 */

import { describe, it, expect } from 'vitest'
import {
  productStatusMap,
  orderStatusMap,
  paymentStatusMap,
  paymentMethodMap,
} from '../constants/statusMaps'

// 后端定义的状态值（从代码审查确认）
const BACKEND_ORDER_STATUSES = ['draft', 'confirmed', 'cancelled', 'partially_paid', 'completed'] as const
const BACKEND_PRODUCT_STATUSES = ['active', 'inactive', 'disabled'] as const
const BACKEND_PAYMENT_STATUSES = ['normal', 'reversed'] as const
const BACKEND_PAYMENT_METHODS = ['cash', 'transfer', 'wechat', 'alipay', 'other'] as const

describe('前端状态映射与后端常量一致性', () => {
  // ═══════════════════════════════════════════════════════
  // 1. 订单状态映射
  // ═══════════════════════════════════════════════════════

  it('前端包含所有后端订单状态', () => {
    for (const status of BACKEND_ORDER_STATUSES) {
      expect(orderStatusMap[status], `缺少订单状态: ${status}`).toBeDefined()
    }
  })

  it('前端订单状态不含多余状态', () => {
    const frontendStatuses = Object.keys(orderStatusMap)
    for (const s of frontendStatuses) {
      expect(BACKEND_ORDER_STATUSES, `多余订单状态: ${s}`).toContain(s)
    }
  })

  it('前端订单状态数量与后端一致', () => {
    expect(Object.keys(orderStatusMap)).toHaveLength(BACKEND_ORDER_STATUSES.length)
  })

  it('每个订单状态有 color 和 label', () => {
    for (const [, info] of Object.entries(orderStatusMap)) {
      expect(info.color).toBeTruthy()
      expect(info.label).toBeTruthy()
    }
  })

  // ═══════════════════════════════════════════════════════
  // 2. 商品状态映射
  // ═══════════════════════════════════════════════════════

  it('前端包含所有后端商品状态', () => {
    for (const status of BACKEND_PRODUCT_STATUSES) {
      expect(productStatusMap[status], `缺少商品状态: ${status}`).toBeDefined()
    }
  })

  it('前端商品状态不含多余状态', () => {
    const frontendStatuses = Object.keys(productStatusMap)
    for (const s of frontendStatuses) {
      expect(BACKEND_PRODUCT_STATUSES, `多余商品状态: ${s}`).toContain(s)
    }
  })

  it('前端商品状态数量与后端一致', () => {
    expect(Object.keys(productStatusMap)).toHaveLength(BACKEND_PRODUCT_STATUSES.length)
  })

  // ═══════════════════════════════════════════════════════
  // 3. 收款状态映射
  // ═══════════════════════════════════════════════════════

  it('前端包含所有后端收款状态', () => {
    for (const status of BACKEND_PAYMENT_STATUSES) {
      expect(paymentStatusMap[status], `缺少收款状态: ${status}`).toBeDefined()
    }
  })

  it('前端收款状态不含多余状态', () => {
    const frontendStatuses = Object.keys(paymentStatusMap)
    for (const s of frontendStatuses) {
      expect(BACKEND_PAYMENT_STATUSES, `多余收款状态: ${s}`).toContain(s)
    }
  })

  it('前端收款状态数量与后端一致', () => {
    expect(Object.keys(paymentStatusMap)).toHaveLength(BACKEND_PAYMENT_STATUSES.length)
  })

  // ═══════════════════════════════════════════════════════
  // 4. 收款方式映射
  // ═══════════════════════════════════════════════════════

  it('前端包含所有后端收款方式', () => {
    for (const method of BACKEND_PAYMENT_METHODS) {
      expect(paymentMethodMap[method], `缺少收款方式: ${method}`).toBeDefined()
    }
  })

  it('前端收款方式不含多余方式', () => {
    const frontendMethods = Object.keys(paymentMethodMap)
    for (const m of frontendMethods) {
      expect(BACKEND_PAYMENT_METHODS, `多余收款方式: ${m}`).toContain(m)
    }
  })

  it('前端收款方式数量与后端一致', () => {
    expect(Object.keys(paymentMethodMap)).toHaveLength(BACKEND_PAYMENT_METHODS.length)
  })

  // ═══════════════════════════════════════════════════════
  // 5. 状态映射 label 非空验证
  // ═══════════════════════════════════════════════════════

  it('所有收款方式 label 非空', () => {
    for (const [, label] of Object.entries(paymentMethodMap)) {
      expect(label).toBeTruthy()
    }
  })

  // ═══════════════════════════════════════════════════════
  // 6. 后端常量值正确性
  // ═══════════════════════════════════════════════════════

  it('后端订单状态列表完整', () => {
    expect(BACKEND_ORDER_STATUSES).toHaveLength(5)
    expect(BACKEND_ORDER_STATUSES).toContain('draft')
    expect(BACKEND_ORDER_STATUSES).toContain('confirmed')
    expect(BACKEND_ORDER_STATUSES).toContain('cancelled')
    expect(BACKEND_ORDER_STATUSES).toContain('partially_paid')
    expect(BACKEND_ORDER_STATUSES).toContain('completed')
  })

  it('后端收款方式列表完整', () => {
    expect(BACKEND_PAYMENT_METHODS).toHaveLength(5)
    expect(BACKEND_PAYMENT_METHODS).toContain('cash')
    expect(BACKEND_PAYMENT_METHODS).toContain('transfer')
    expect(BACKEND_PAYMENT_METHODS).toContain('wechat')
    expect(BACKEND_PAYMENT_METHODS).toContain('alipay')
    expect(BACKEND_PAYMENT_METHODS).toContain('other')
  })
})
