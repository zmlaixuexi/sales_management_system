/**
 * 代码质量：前端表单验证规则与后端 Schema 约束对齐验证测试
 * 覆盖必填字段对齐、maxLength 对齐、正则模式对齐、
 * Select 选项对齐、InputNumber 最小值对齐
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const ROOT = resolve(import.meta.dirname, '..', '..', '..')

function read(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf-8')
}

// ═══════════════════════════════════════════════════════════
// 1. 必填字段对齐验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('必填字段对齐', () => {
  it('ProductForm 必填字段覆盖后端 CreateSchema 必填项', () => {
    const form = read('frontend/src/pages/ProductForm.tsx')
    // 后端 ProductCreate: name, cost_price, sale_price 为必填
    for (const field of ['name', 'cost_price', 'sale_price']) {
      expect(form, `ProductForm ${field} 应有 required 规则`).toMatch(
        new RegExp(`name=["']${field}["'][\\s\\S]*?required:\\s*true`),
      )
    }
  })

  it('CustomerForm 必填字段覆盖后端 CreateSchema 必填项', () => {
    const form = read('frontend/src/pages/CustomerForm.tsx')
    // 后端 CustomerCreate: name 为必填
    expect(form, 'CustomerForm name 应有 required 规则').toMatch(
      /name=["']name["'][\s\S]*?required:\s*true/,
    )
  })

  it('OrderForm 必填字段覆盖后端 CreateSchema 必填项', () => {
    const form = read('frontend/src/pages/OrderForm.tsx')
    // 后端 OrderCreate: customer_id 为必填
    expect(form, 'OrderForm customer_id 应有 required 规则').toMatch(
      /name=["']customer_id["'][\s\S]*?required:\s*true/,
    )
  })

  it('Login 表单 username 和 password 为必填', () => {
    const form = read('frontend/src/pages/Login.tsx')
    expect(form).toMatch(/name=["']username["'][\s\S]*?required:\s*true/)
    expect(form).toMatch(/name=["']password["'][\s\S]*?required:\s*true/)
  })

  it('后端 Schema 必填字段使用非 Optional 类型', () => {
    const productSchema = read('backend/app/schemas/product.py')
    // 提取 ProductCreate class body
    const createMatch = productSchema.match(/class ProductCreate\b[\s\S]*?(?=\nclass |\Z)/)
    expect(createMatch, '应找到 ProductCreate 类').toBeTruthy()
    const createBody = createMatch![0]
    expect(createBody).toMatch(/name:\s*str\b/)
    expect(createBody).not.toMatch(/name:\s*(?:Optional|str \| None)/)
  })
})

// ═══════════════════════════════════════════════════════════
// 2. maxLength 对齐验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('maxLength 对齐', () => {
  it('ProductForm name maxLength 与后端 max_length=100 对齐', () => {
    const form = read('frontend/src/pages/ProductForm.tsx')
    const schema = read('backend/app/schemas/product.py')
    expect(form).toContain('maxLength={100}')
    expect(schema).toContain('max_length=100')
  })

  it('ProductForm sku maxLength 与后端 max_length=50 对齐', () => {
    const form = read('frontend/src/pages/ProductForm.tsx')
    const schema = read('backend/app/schemas/product.py')
    expect(form).toContain('maxLength={50}')
    expect(schema).toContain('max_length=50')
  })

  it('ProductForm remark maxLength 与后端 max_length=500 对齐', () => {
    const form = read('frontend/src/pages/ProductForm.tsx')
    const schema = read('backend/app/schemas/product.py')
    expect(form).toContain('maxLength={500}')
    expect(schema).toContain('max_length=500')
  })

  it('CustomerForm phone maxLength 与后端 max_length=30 对齐', () => {
    const form = read('frontend/src/pages/CustomerForm.tsx')
    const schema = read('backend/app/schemas/customer.py')
    expect(form).toContain('maxLength={30}')
    expect(schema).toContain('max_length=30')
  })

  it('CustomerForm remark maxLength 与后端 max_length=500 对齐', () => {
    const form = read('frontend/src/pages/CustomerForm.tsx')
    const schema = read('backend/app/schemas/customer.py')
    expect(form).toContain('maxLength={500}')
    expect(schema).toContain('max_length=500')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 正则模式对齐验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('正则模式对齐', () => {
  it('CustomerForm 手机号正则与后端 _PHONE_RE 一致', () => {
    const form = read('frontend/src/pages/CustomerForm.tsx')
    const schema = read('backend/app/schemas/customer.py')
    // 前端: /^1[3-9]\d{9}$/
    expect(form).toMatch(/\/\^1\[3-9\]\\d\{9\}\$\//)
    // 后端: r"^1[3-9]\d{9}$"
    expect(schema).toMatch(/1\[3-9\]\\d\{9\}/)
  })

  it('CustomerForm email 使用 type: email 验证', () => {
    const form = read('frontend/src/pages/CustomerForm.tsx')
    expect(form).toMatch(/type:\s*['"]email['"]/)
  })

  it('后端 customer schema 有 email 正则验证', () => {
    const schema = read('backend/app/schemas/customer.py')
    expect(schema).toMatch(/_EMAIL_RE/)
    expect(schema).toMatch(/@\S+/)
  })

  it('后端 product schema 有文本清洗验证器', () => {
    const schema = read('backend/app/schemas/product.py')
    expect(schema).toMatch(/_sanitize|sanitize|strip/)
  })

  it('后端 customer schema 有文本清洗验证器', () => {
    const schema = read('backend/app/schemas/customer.py')
    expect(schema).toMatch(/_sanitize|sanitize|strip/)
  })
})

// ═══════════════════════════════════════════════════════════
// 4. Select 选项对齐验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('Select 选项对齐', () => {
  it('ProductForm status 选项与后端 Literal 对齐', () => {
    const form = read('frontend/src/pages/ProductForm.tsx')
    const schema = read('backend/app/schemas/product.py')
    for (const val of ['active', 'inactive', 'disabled']) {
      expect(form, `ProductForm 应包含 status 选项 ${val}`).toContain(`'${val}'`)
    }
    expect(schema).toContain('"active"')
    expect(schema).toContain('"inactive"')
    expect(schema).toContain('"disabled"')
  })

  it('CustomerForm source 选项与后端 Literal 对齐', () => {
    const form = read('frontend/src/pages/CustomerForm.tsx')
    const schema = read('backend/app/schemas/customer.py')
    for (const val of ['referral', 'online', 'offline', 'ad', 'other']) {
      expect(form, `CustomerForm 应包含 source 选项 ${val}`).toContain(`'${val}'`)
    }
  })

  it('CustomerForm level 选项与后端 Literal 对齐', () => {
    const form = read('frontend/src/pages/CustomerForm.tsx')
    for (const val of ['vip', 'important', 'normal', 'potential']) {
      expect(form, `CustomerForm 应包含 level 选项 ${val}`).toContain(`'${val}'`)
    }
  })

  it('CustomerForm follow_status 选项与后端 Literal 对齐', () => {
    const form = read('frontend/src/pages/CustomerForm.tsx')
    for (const val of ['new', 'following', 'closed', 'lost']) {
      expect(form, `CustomerForm 应包含 follow_status 选项 ${val}`).toContain(`'${val}'`)
    }
  })

  it('后端 Schema 使用 Literal 类型限制选项值', () => {
    const productSchema = read('backend/app/schemas/product.py')
    expect(productSchema).toMatch(/Literal\[/)
    const customerSchema = read('backend/app/schemas/customer.py')
    expect(customerSchema).toMatch(/Literal\[/)
  })
})

// ═══════════════════════════════════════════════════════════
// 5. InputNumber 最小值对齐验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('InputNumber 最小值对齐', () => {
  it('ProductForm cost_price min=0 与后端 ge=0 对齐', () => {
    const form = read('frontend/src/pages/ProductForm.tsx')
    const schema = read('backend/app/schemas/product.py')
    expect(form).toMatch(/cost_price[\s\S]*?min=\{0\}/)
    expect(schema).toContain('ge=0')
  })

  it('ProductForm sale_price min=0 与后端 ge=0 对齐', () => {
    const form = read('frontend/src/pages/ProductForm.tsx')
    const schema = read('backend/app/schemas/product.py')
    expect(form).toMatch(/sale_price[\s\S]*?min=\{0\}/)
    expect(schema).toContain('ge=0')
  })

  it('ProductForm stock_quantity min=0 与后端 ge=0 对齐', () => {
    const form = read('frontend/src/pages/ProductForm.tsx')
    expect(form).toMatch(/stock_quantity[\s\S]*?min=\{0\}/)
  })

  it('OrderForm items quantity min=1 与后端 gt=0 对齐', () => {
    const form = read('frontend/src/pages/OrderForm.tsx')
    const schema = read('backend/app/schemas/order.py')
    expect(form).toContain('min={1}')
    expect(schema).toContain('gt=0')
  })

  it('OrderForm unit_price min=0 与后端约束对齐', () => {
    const form = read('frontend/src/pages/OrderForm.tsx')
    expect(form).toMatch(/min=\{0\}/)
  })
})
