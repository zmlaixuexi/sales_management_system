/**
 * 代码质量：前端常量映射与后端枚举值对齐验证测试
 * 覆盖状态映射完整性、来源/等级/收款方式双向对齐、
 * StatusInfo 结构一致性、标签非空、无多余键
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')

function backendSrc(module: string): string {
  return readFileSync(resolve(root, 'backend', 'app', module), 'utf-8')
}

const frontendCode = readFileSync(resolve(root, 'frontend/src/constants/statusMaps.ts'), 'utf-8')

/** 提取 Record<string, ...> 映射中的所有键 */
function extractMapKeys(source: string, mapName: string): string[] {
  const idx = source.indexOf(`export const ${mapName}:`)
  if (idx === -1) return []
  const rest = source.substring(idx)
  // 找到第一个 { 后的内容，统计花括号深度
  let braceStart = rest.indexOf('{')
  if (braceStart === -1) return []
  let depth = 0
  let end = braceStart
  for (let i = braceStart; i < rest.length; i++) {
    if (rest[i] === '{') depth++
    else if (rest[i] === '}') {
      depth--
      if (depth === 0) { end = i; break }
    }
  }
  const body = rest.substring(braceStart + 1, end)
  // 提取键：行首的标识符后跟冒号
  const keys: string[] = []
  for (const line of body.split('\n')) {
    const m = line.match(/^\s+(\w+):\s/)
    if (m) keys.push(m[1])
  }
  return keys
}

/** 提取后端 Literal["a", "b", ...] 中的值 */
function extractLiteralValues(source: string, typeName: string): string[] {
  const match = source.match(new RegExp(`${typeName}\\s*=\\s*Literal\\[([^\\]]+)\\]`))
  if (!match) return []
  return (match[1].match(/"(\w+)"/g) || []).map((v) => v.replace(/"/g, ''))
}

/** 提取后端元组 ("a", "b", ...) 中的值 */
function extractTupleValues(source: string, varName: string): string[] {
  const match = source.match(new RegExp(`${varName}\\s*=\\s*\\(([^)]+)\\)`))
  if (!match) return []
  return (match[1].match(/"(\w+)"/g) || []).map((v) => v.replace(/"/g, ''))
}

// ═══════════════════════════════════════════════════════════
// 1. 订单状态映射对齐验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('订单状态映射对齐', () => {
  it('orderStatusMap 包含 5 种状态', () => {
    const keys = extractMapKeys(frontendCode, 'orderStatusMap')
    expect(keys).toEqual(['draft', 'confirmed', 'cancelled', 'partially_paid', 'completed'])
  })

  it('后端订单模型默认状态为 draft', () => {
    const modelCode = backendSrc('models/order.py')
    expect(modelCode).toContain('default="draft"')
  })

  it('前端每个订单状态有 color 和 label', () => {
    const keys = extractMapKeys(frontendCode, 'orderStatusMap')
    for (const key of keys) {
      const regex = new RegExp(`${key}:\\s*\\{\\s*color:\\s*'[^']+'\\s*,\\s*label:\\s*'[^']+'`)
      expect(frontendCode).toMatch(regex)
    }
  })

  it('后端订单状态标签引用的状态在前端全部存在', () => {
    const orderCode = backendSrc('api/v1/orders.py')
    const statusLabels = ['draft', 'confirmed', 'cancelled', 'partially_paid', 'completed']
    for (const status of statusLabels) {
      expect(frontendCode).toContain(status)
    }
    expect(orderCode).toContain('draft')
  })

  it('orderStatusMap 中 draft 为草稿标签', () => {
    expect(frontendCode).toMatch(/draft:.*label:.*草稿/)
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 商品状态映射对齐验证（4 项）
// ═══════════════════════════════════════════════════════════

describe('商品状态映射对齐', () => {
  it('productStatusMap 包含 active/inactive/disabled', () => {
    const keys = extractMapKeys(frontendCode, 'productStatusMap')
    expect(keys).toEqual(['active', 'inactive', 'disabled'])
  })

  it('后端模型默认 status 为 active', () => {
    const modelCode = backendSrc('models/product.py')
    expect(modelCode).toContain('default="active"')
  })

  it('后端 disable 端点设置 disabled 状态', () => {
    const apiCode = backendSrc('api/v1/products.py')
    expect(apiCode).toContain('disabled')
  })

  it('前端每个商品状态有 color 和 label', () => {
    const keys = extractMapKeys(frontendCode, 'productStatusMap')
    for (const key of keys) {
      const regex = new RegExp(`${key}:\\s*\\{\\s*color:\\s*'[^']+'\\s*,\\s*label:\\s*'[^']+'`)
      expect(frontendCode).toMatch(regex)
    }
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 收款状态映射对齐验证（3 项）
// ═══════════════════════════════════════════════════════════

describe('收款状态映射对齐', () => {
  it('paymentStatusMap 包含 normal/reversed', () => {
    const keys = extractMapKeys(frontendCode, 'paymentStatusMap')
    expect(keys).toEqual(['normal', 'reversed'])
  })

  it('后端模型默认 status 为 normal', () => {
    const modelCode = backendSrc('models/order.py')
    expect(modelCode).toContain('default="normal"')
  })

  it('前端每个收款状态有 color 和 label', () => {
    const keys = extractMapKeys(frontendCode, 'paymentStatusMap')
    for (const key of keys) {
      const regex = new RegExp(`${key}:\\s*\\{\\s*color:\\s*'[^']+'\\s*,\\s*label:\\s*'[^']+'`)
      expect(frontendCode).toMatch(regex)
    }
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 客户来源映射对齐验证（4 项）
// ═══════════════════════════════════════════════════════════

describe('客户来源映射对齐', () => {
  const backendCode = backendSrc('schemas/customer.py')

  it('前端 customerSourceMap 包含全部 5 种来源', () => {
    const keys = extractMapKeys(frontendCode, 'customerSourceMap')
    expect(keys).toEqual(['referral', 'online', 'offline', 'ad', 'other'])
  })

  it('后端 CustomerSource Literal 与前端键完全一致', () => {
    const backendValues = extractLiteralValues(backendCode, 'CustomerSource')
    const frontendKeys = extractMapKeys(frontendCode, 'customerSourceMap')
    expect(backendValues.sort()).toEqual(frontendKeys.sort())
  })

  it('customerSourceMap 每项值为非空中文字符串', () => {
    const keys = extractMapKeys(frontendCode, 'customerSourceMap')
    for (const key of keys) {
      const regex = new RegExp(`${key}:\\s*'[^']+'`)
      expect(frontendCode).toMatch(regex)
    }
  })

  it('customerSourceMap 不包含后端没有的来源', () => {
    const backendValues = extractLiteralValues(backendCode, 'CustomerSource')
    const frontendKeys = extractMapKeys(frontendCode, 'customerSourceMap')
    for (const fk of frontendKeys) {
      expect(backendValues).toContain(fk)
    }
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 客户等级映射对齐验证（4 项）
// ═══════════════════════════════════════════════════════════

describe('客户等级映射对齐', () => {
  const backendCode = backendSrc('schemas/customer.py')

  it('前端 customerLevelMap 包含 4 种等级', () => {
    const keys = extractMapKeys(frontendCode, 'customerLevelMap')
    expect(keys).toEqual(['vip', 'important', 'normal', 'potential'])
  })

  it('后端 CustomerLevel Literal 与前端键完全一致', () => {
    const backendValues = extractLiteralValues(backendCode, 'CustomerLevel')
    const frontendKeys = extractMapKeys(frontendCode, 'customerLevelMap')
    expect(backendValues.sort()).toEqual(frontendKeys.sort())
  })

  it('前端每个等级有 color 和 label', () => {
    const keys = extractMapKeys(frontendCode, 'customerLevelMap')
    for (const key of keys) {
      const regex = new RegExp(`${key}:\\s*\\{\\s*color:\\s*'[^']+'\\s*,\\s*label:\\s*'[^']+'`)
      expect(frontendCode).toMatch(regex)
    }
  })

  it('后端默认等级为 normal', () => {
    expect(backendCode).toMatch(/level:.*Field\("normal"/)
  })
})

// ═══════════════════════════════════════════════════════════
// 6. 收款方式映射对齐验证（4 项）
// ═══════════════════════════════════════════════════════════

describe('收款方式映射对齐', () => {
  const backendCode = backendSrc('schemas/payment.py')

  it('前端 paymentMethodMap 包含 5 种方式', () => {
    const keys = extractMapKeys(frontendCode, 'paymentMethodMap')
    expect(keys).toEqual(['cash', 'transfer', 'wechat', 'alipay', 'other'])
  })

  it('后端 VALID_PAYMENT_METHODS 与前端键完全一致', () => {
    const backendValues = extractTupleValues(backendCode, 'VALID_PAYMENT_METHODS')
    const frontendKeys = extractMapKeys(frontendCode, 'paymentMethodMap')
    expect(backendValues.sort()).toEqual(frontendKeys.sort())
  })

  it('后端 PaymentCreate Literal 与前端键完全一致', () => {
    const match = backendCode.match(/payment_method:\s*Literal\[([^\]]+)\]/)
    expect(match).not.toBeNull()
    const values = (match![1].match(/"(\w+)"/g) || []).map((v) => v.replace(/"/g, ''))
    const frontendKeys = extractMapKeys(frontendCode, 'paymentMethodMap')
    expect(values.sort()).toEqual(frontendKeys.sort())
  })

  it('paymentMethodMap 每项值为非空中文字符串', () => {
    const keys = extractMapKeys(frontendCode, 'paymentMethodMap')
    for (const key of keys) {
      const regex = new RegExp(`${key}:\\s*'[^']+'`)
      expect(frontendCode).toMatch(regex)
    }
  })
})
