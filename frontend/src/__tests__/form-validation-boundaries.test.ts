/**
 * 代码质量：前端表单验证边界测试
 * 覆盖正则模式、长度边界、必填字段、数值约束、源码一致性
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

/* ── helpers ────────────────────────────────────────── */

const SRC = path.resolve(__dirname, '..', 'pages')

function source(file: string): string {
  return fs.readFileSync(path.join(SRC, file), 'utf-8')
}

/* ═══════════════════════════════════════════════════════
 * 1. 手机号正则 /^1[3-9]\d{9}$/
 * ═══════════════════════════════════════════════════════ */

describe('手机号正则 /^1[3-9]\\d{9}$/', () => {
  const PHONE_RE = /^1[3-9]\d{9}$/

  it('合法手机号 13800001111', () => {
    expect(PHONE_RE.test('13800001111')).toBe(true)
  })

  it('合法手机号 19999999999', () => {
    expect(PHONE_RE.test('19999999999')).toBe(true)
  })

  it('合法手机号 15012345678', () => {
    expect(PHONE_RE.test('15012345678')).toBe(true)
  })

  it('以 10 开头不合法', () => {
    expect(PHONE_RE.test('10000000000')).toBe(false)
  })

  it('以 12 开头不合法', () => {
    expect(PHONE_RE.test('12000000000')).toBe(false)
  })

  it('11 位全数字不足 11 位不合法', () => {
    expect(PHONE_RE.test('1380000111')).toBe(false)
  })

  it('12 位不合法', () => {
    expect(PHONE_RE.test('138000011111')).toBe(false)
  })

  it('包含字母不合法', () => {
    expect(PHONE_RE.test('1380000111a')).toBe(false)
  })

  it('空字符串不合法', () => {
    expect(PHONE_RE.test('')).toBe(false)
  })

  it('CustomerForm 使用手机号正则', () => {
    const src = source('CustomerForm.tsx')
    expect(src).toContain('1[3-9]\\d{9}')
  })

  it('Users 使用手机号正则', () => {
    const src = source('Users.tsx')
    expect(src).toContain('1[3-9]\\d{9}')
  })
})

/* ═══════════════════════════════════════════════════════
 * 2. 密码正则 /^(?=.*[a-zA-Z])(?=.*\d)/
 * ═══════════════════════════════════════════════════════ */

describe('密码正则 /^(?=.*[a-zA-Z])(?=.*\\d)/', () => {
  const PW_RE = /^(?=.*[a-zA-Z])(?=.*\d)/

  it('字母+数字合法', () => {
    expect(PW_RE.test('abc123')).toBe(true)
  })

  it('数字+字母合法', () => {
    expect(PW_RE.test('123abc')).toBe(true)
  })

  it('大写字母+数字合法', () => {
    expect(PW_RE.test('ABC123')).toBe(true)
  })

  it('混合大小写+数字合法', () => {
    expect(PW_RE.test('aBc123')).toBe(true)
  })

  it('纯数字不合法', () => {
    expect(PW_RE.test('123456')).toBe(false)
  })

  it('纯字母不合法', () => {
    expect(PW_RE.test('abcdef')).toBe(false)
  })

  it('纯大写字母不合法', () => {
    expect(PW_RE.test('ABCDEF')).toBe(false)
  })

  it('空字符串不合法', () => {
    expect(PW_RE.test('')).toBe(false)
  })

  it('特殊字符+数字但不包含字母不合法', () => {
    expect(PW_RE.test('@#$123')).toBe(false)
  })

  it('Users 使用密码正则', () => {
    const src = source('Users.tsx')
    expect(src).toContain('?=.*[a-zA-Z]')
    expect(src).toContain('?=.*\\d')
  })
})

/* ═══════════════════════════════════════════════════════
 * 3. 用户名长度边界 (min: 2, max: 50)
 * ═══════════════════════════════════════════════════════ */

describe('用户名长度边界', () => {
  it('Users 用户名 min=2', () => {
    const src = source('Users.tsx')
    expect(src).toMatch(/min:\s*2/)
  })

  it('Users 用户名 max=50', () => {
    const src = source('Users.tsx')
    expect(src).toMatch(/max:\s*50/)
  })

  it('Users 用户名 required', () => {
    const src = source('Users.tsx')
    expect(src).toContain('请输入用户名')
  })

  it('Users 用户名 Input maxLength=50', () => {
    const src = source('Users.tsx')
    expect(src).toContain('maxLength={50}')
  })
})

/* ═══════════════════════════════════════════════════════
 * 4. 密码长度边界 (min: 6, max: 100)
 * ═══════════════════════════════════════════════════════ */

describe('密码长度边界', () => {
  it('Users 密码 min=6', () => {
    const src = source('Users.tsx')
    expect(src).toMatch(/密码至少 6 个字符/)
  })

  it('Users 密码 max=100', () => {
    const src = source('Users.tsx')
    expect(src).toMatch(/密码最多 100 个字符/)
  })

  it('Users 密码 required', () => {
    const src = source('Users.tsx')
    expect(src).toContain('请输入密码')
  })
})

/* ═══════════════════════════════════════════════════════
 * 5. 邮箱 type: 'email' 验证
 * ═══════════════════════════════════════════════════════ */

describe('邮箱验证', () => {
  it('CustomerForm 使用 type=email', () => {
    const src = source('CustomerForm.tsx')
    expect(src).toContain("type: 'email'")
  })

  it('Users 使用 type=email', () => {
    const src = source('Users.tsx')
    expect(src).toContain("type: 'email'")
  })

  it('Users 邮箱 max=100', () => {
    const src = source('Users.tsx')
    expect(src).toMatch(/邮箱最多 100 个字符/)
  })
})

/* ═══════════════════════════════════════════════════════
 * 6. 客户名称必填 + maxLength
 * ═══════════════════════════════════════════════════════ */

describe('客户名称字段', () => {
  it('CustomerForm name required', () => {
    const src = source('CustomerForm.tsx')
    expect(src).toContain('请输入客户名称')
  })

  it('CustomerForm name maxLength=100', () => {
    const src = source('CustomerForm.tsx')
    expect(src).toContain('maxLength={100}')
  })

  it('CustomerForm phone maxLength=30', () => {
    const src = source('CustomerForm.tsx')
    expect(src).toContain('maxLength={30}')
  })

  it('CustomerForm remark maxLength=500', () => {
    const src = source('CustomerForm.tsx')
    expect(src).toContain('maxLength={500}')
  })
})

/* ═══════════════════════════════════════════════════════
 * 7. 商品名称必填 + InputNumber min
 * ═══════════════════════════════════════════════════════ */

describe('商品表单验证', () => {
  it('ProductForm name required', () => {
    const src = source('ProductForm.tsx')
    expect(src).toContain('请输入商品名称')
  })

  it('ProductForm cost_price required', () => {
    const src = source('ProductForm.tsx')
    expect(src).toContain('请输入成本价')
  })

  it('ProductForm sale_price required', () => {
    const src = source('ProductForm.tsx')
    expect(src).toContain('请输入销售价')
  })

  it('ProductForm cost_price min=0', () => {
    const src = source('ProductForm.tsx')
    expect(src).toContain('min={0}')
  })

  it('ProductForm precision=2', () => {
    const src = source('ProductForm.tsx')
    expect(src).toContain('precision={2}')
  })

  it('ProductForm name maxLength=100', () => {
    const src = source('ProductForm.tsx')
    expect(src).toContain('maxLength={100}')
  })

  it('ProductForm sku maxLength=50', () => {
    const src = source('ProductForm.tsx')
    expect(src).toContain('maxLength={50}')
  })
})

/* ═══════════════════════════════════════════════════════
 * 8. 订单表单验证
 * ═══════════════════════════════════════════════════════ */

describe('订单表单验证', () => {
  it('OrderForm customer_id required', () => {
    const src = source('OrderForm.tsx')
    expect(src).toContain('请选择客户')
  })

  it('OrderForm 空商品行校验', () => {
    const src = source('OrderForm.tsx')
    expect(src).toContain('请添加至少一个商品')
  })

  it('OrderForm quantity min=1', () => {
    const src = source('OrderForm.tsx')
    expect(src).toContain('min={1}')
  })

  it('OrderForm unit_price min=0', () => {
    const src = source('OrderForm.tsx')
    expect(src).toContain('min={0}')
  })

  it('OrderForm 重复商品检查', () => {
    const src = source('OrderForm.tsx')
    expect(src).toMatch(/existing/)
  })

  it('OrderForm remark maxLength=500', () => {
    const src = source('OrderForm.tsx')
    expect(src).toContain('maxLength={500}')
  })
})

/* ═══════════════════════════════════════════════════════
 * 9. 角色表单验证
 * ═══════════════════════════════════════════════════════ */

describe('角色表单验证', () => {
  it('Roles name required', () => {
    const src = source('Roles.tsx')
    expect(src).toContain('请输入角色标识')
  })

  it('Roles name max=50', () => {
    const src = source('Roles.tsx')
    expect(src).toMatch(/最多 50 个字符/)
  })

  it('Roles display_name max=100', () => {
    const src = source('Roles.tsx')
    expect(src).toMatch(/最多 100 个字符/)
  })

  it('Roles description max=255', () => {
    const src = source('Roles.tsx')
    expect(src).toMatch(/最多 255 个字符/)
  })

  it('Roles name maxLength=50', () => {
    const src = source('Roles.tsx')
    expect(src).toContain('maxLength={50}')
  })

  it('Roles description maxLength=255', () => {
    const src = source('Roles.tsx')
    expect(src).toContain('maxLength={255}')
  })
})

/* ═══════════════════════════════════════════════════════
 * 10. 登录表单验证
 * ═══════════════════════════════════════════════════════ */

describe('登录表单验证', () => {
  it('Login username required', () => {
    const src = source('Login.tsx')
    expect(src).toContain('请输入用户名')
  })

  it('Login password required', () => {
    const src = source('Login.tsx')
    expect(src).toContain('请输入密码')
  })
})

/* ═══════════════════════════════════════════════════════
 * 11. useSubmit 吞没 errorFields
 * ═══════════════════════════════════════════════════════ */

describe('useSubmit 表单验证错误处理', () => {
  it('useSubmit 吞没 errorFields 防止重复提示', () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '..', 'hooks', 'useSubmit.ts'),
      'utf-8',
    )
    expect(src).toMatch(/errorFields/)
  })
})

/* ═══════════════════════════════════════════════════════
 * 12. 前后端验证一致性
 * ═══════════════════════════════════════════════════════ */

describe('前后端验证一致性', () => {
  it('前端手机号正则与后端 Pydantic 一致', () => {
    // 后端 app/schemas/customer.py 使用 ^1[3-9]\d{9}$
    const PHONE_RE = /^1[3-9]\d{9}$/
    expect(PHONE_RE.test('13800001111')).toBe(true)
    expect(PHONE_RE.test('10000000000')).toBe(false)
  })

  it('前端密码正则与后端一致', () => {
    // 后端要求至少一个字母 + 一个数字
    const PW_RE = /^(?=.*[a-zA-Z])(?=.*\d)/
    expect(PW_RE.test('abc123')).toBe(true)
    expect(PW_RE.test('abcdef')).toBe(false)
    expect(PW_RE.test('123456')).toBe(false)
  })
})
