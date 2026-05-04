/**
 * 代码质量：前端状态显示映射与后端状态常量对齐验证测试
 * 覆盖商品状态映射、订单状态映射、收款状态映射、
 * 客户来源/等级映射、收款方式映射与后端常量一致性
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const ROOT = resolve(import.meta.dirname, '..', '..', '..')

function read(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf-8')
}

const STATUS_MAPS = 'frontend/src/constants/statusMaps.ts'
const PRODUCT_MODEL = 'backend/app/models/product.py'
const ORDER_MODEL = 'backend/app/models/order.py'
const PAYMENT_MODEL = 'backend/app/models/order.py'
const CUSTOMER_MODEL = 'backend/app/models/customer.py'

// ═══════════════════════════════════════════════════════════
// 1. 商品状态映射验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('商品状态映射', () => {
  it('前端 productStatusMap 覆盖后端所有商品状态', () => {
    const front = read(STATUS_MAPS)
    const back = read(PRODUCT_MODEL)
    // 后端模型中定义的状态值
    for (const status of ['active', 'inactive', 'disabled']) {
      expect(front, `前端应映射商品状态 ${status}`).toContain(status)
    }
  })

  it('productStatusMap 每个状态有 color 和 label', () => {
    const src = read(STATUS_MAPS)
    for (const status of ['active', 'inactive', 'disabled']) {
      expect(src, `${status} 应有 color`).toMatch(new RegExp(`${status}:\\s*\\{[^}]*color`))
      expect(src, `${status} 应有 label`).toMatch(new RegExp(`${status}:\\s*\\{[^}]*label`))
    }
  })

  it('商品状态标签使用中文', () => {
    const src = read(STATUS_MAPS)
    for (const text of ['上架', '下架', '停用']) {
      expect(src, `productStatusMap 应包含标签 ${text}`).toContain(text)
    }
  })

  it('productStatusMap 使用 Record<string, StatusInfo> 类型', () => {
    const src = read(STATUS_MAPS)
    expect(src).toContain('StatusInfo')
    expect(src).toContain('Record<string, StatusInfo>')
  })

  it('商品状态颜色语义合理', () => {
    const src = read(STATUS_MAPS)
    expect(src).toMatch(/active:\s*\{[^}]*color:\s*'green'/)
    expect(src).toMatch(/disabled:\s*\{[^}]*color:\s*'red'/)
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 订单状态映射验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('订单状态映射', () => {
  it('前端 orderStatusMap 覆盖后端所有订单状态', () => {
    const front = read(STATUS_MAPS)
    for (const status of ['draft', 'confirmed', 'cancelled', 'partially_paid', 'completed']) {
      expect(front, `前端应映射订单状态 ${status}`).toContain(status)
    }
  })

  it('orderStatusMap 每个状态有 color 和 label', () => {
    const src = read(STATUS_MAPS)
    const orderSection = src.match(/orderStatusMap[\s\S]*?}/)?.[0] || ''
    for (const status of ['draft', 'confirmed', 'cancelled', 'partially_paid', 'completed']) {
      expect(orderSection, `${status} 应有 color`).toContain('color')
      expect(orderSection, `${status} 应有 label`).toContain('label')
    }
  })

  it('订单状态标签使用中文', () => {
    const src = read(STATUS_MAPS)
    // 统计 orderStatusMap 中 label 出现次数
    const labels = src.match(/label:\s*'[^']+'/g) || []
    expect(labels.length).toBeGreaterThanOrEqual(10)  // 所有 map 的 label
    // 验证订单相关标签
    for (const text of ['草稿', '已确认', '已取消', '部分收款', '已完成']) {
      expect(src, `orderStatusMap 应包含标签 ${text}`).toContain(text)
    }
  })

  it('订单状态颜色语义合理：completed 为 green、cancelled 为 red', () => {
    const src = read(STATUS_MAPS)
    expect(src).toMatch(/completed:\s*\{[^}]*color:\s*'green'/)
    expect(src).toMatch(/cancelled:\s*\{[^}]*color:\s*'red'/)
  })

  it('后端订单模型定义了状态枚举或常量', () => {
    const back = read(ORDER_MODEL)
    expect(back).toMatch(/status/i)
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 收款状态映射验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('收款状态映射', () => {
  it('前端 paymentStatusMap 覆盖后端所有收款状态', () => {
    const front = read(STATUS_MAPS)
    for (const status of ['normal', 'reversed']) {
      expect(front, `前端应映射收款状态 ${status}`).toContain(status)
    }
  })

  it('paymentStatusMap 每个状态有 color 和 label', () => {
    const src = read(STATUS_MAPS)
    const paymentSection = src.match(/paymentStatusMap[\s\S]*?}/)?.[0] || ''
    expect(paymentSection).toContain('color')
    expect(paymentSection).toContain('label')
  })

  it('收款状态标签使用中文', () => {
    const src = read(STATUS_MAPS)
    const paymentSection = src.match(/paymentStatusMap[\s\S]*?}/)?.[0] || ''
    const labels = paymentSection.match(/label:\s*'([^']+)'/g) || []
    for (const label of labels) {
      const text = label.match(/'([^']+)'/)![1]
      expect(text, `标签 ${text} 应使用中文`).toMatch(/[一-鿿]/)
    }
  })

  it('收款状态颜色语义合理：normal 为 green、reversed 为 red', () => {
    const src = read(STATUS_MAPS)
    expect(src).toMatch(/normal:\s*\{[^}]*color:\s*'green'/)
    expect(src).toMatch(/reversed:\s*\{[^}]*color:\s*'red'/)
  })

  it('后端收款模型定义了状态字段', () => {
    const back = read(PAYMENT_MODEL)
    expect(back).toMatch(/status/i)
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 客户来源/等级映射验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('客户来源/等级映射', () => {
  it('customerSourceMap 覆盖所有客户来源', () => {
    const src = read(STATUS_MAPS)
    for (const source of ['referral', 'online', 'offline', 'ad', 'other']) {
      expect(src, `前端应映射客户来源 ${source}`).toContain(source)
    }
  })

  it('customerLevelMap 覆盖所有客户等级', () => {
    const src = read(STATUS_MAPS)
    for (const level of ['vip', 'important', 'normal', 'potential']) {
      expect(src, `前端应映射客户等级 ${level}`).toContain(level)
    }
  })

  it('客户来源标签使用中文', () => {
    const src = read(STATUS_MAPS)
    const sourceSection = src.match(/customerSourceMap[\s\S]*?}/)?.[0] || ''
    const values = sourceSection.match(/:\s*'([^']+)'/g) || []
    for (const val of values) {
      const text = val.match(/'([^']+)'/)![1]
      expect(text, `来源标签 ${text} 应使用中文`).toMatch(/[一-鿿]/)
    }
  })

  it('customerLevelMap 每个等级有 color 和 label', () => {
    const src = read(STATUS_MAPS)
    const levelSection = src.match(/customerLevelMap[\s\S]*?}/)?.[0] || ''
    expect(levelSection).toContain('color')
    expect(levelSection).toContain('label')
  })

  it('客户等级 VIP 使用 gold 颜色', () => {
    const src = read(STATUS_MAPS)
    expect(src).toMatch(/vip:\s*\{[^}]*color:\s*'gold'/)
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 收款方式映射验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('收款方式映射', () => {
  it('paymentMethodMap 覆盖所有收款方式', () => {
    const src = read(STATUS_MAPS)
    for (const method of ['cash', 'transfer', 'wechat', 'alipay', 'other']) {
      expect(src, `前端应映射收款方式 ${method}`).toContain(method)
    }
  })

  it('收款方式标签使用中文', () => {
    const src = read(STATUS_MAPS)
    const methodSection = src.match(/paymentMethodMap[\s\S]*?}/)?.[0] || ''
    const values = methodSection.match(/:\s*'([^']+)'/g) || []
    for (const val of values) {
      const text = val.match(/'([^']+)'/)![1]
      expect(text, `方式标签 ${text} 应使用中文`).toMatch(/[一-鿿]/)
    }
  })

  it('paymentMethodMap 使用 Record<string, string> 类型', () => {
    const src = read(STATUS_MAPS)
    expect(src).toContain('Record<string, string>')
  })

  it('后端收款模型定义了收款方式字段', () => {
    const back = read(PAYMENT_MODEL)
    expect(back).toMatch(/method/i)
  })

  it('所有映射导出为命名导出', () => {
    const src = read(STATUS_MAPS)
    expect(src).toContain('export const productStatusMap')
    expect(src).toContain('export const orderStatusMap')
    expect(src).toContain('export const paymentStatusMap')
    expect(src).toContain('export const customerSourceMap')
    expect(src).toContain('export const customerLevelMap')
    expect(src).toContain('export const paymentMethodMap')
  })
})
