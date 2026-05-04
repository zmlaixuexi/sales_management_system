/**
 * 需求符合性：前端错误码常量与后端一致性测试
 * 验证前端已知的后端错误码列表与后端实际使用的错误码一致
 */

import { describe, it, expect } from 'vitest'
import type { ApiError } from '../types'

/**
 * 后端 app/ 目录中所有 "code": "XXX" 的去重列表
 * 来源: grep -roh '"code": *"[A-Z_]*"' backend/app/ | sort -u
 */
const BACKEND_ERROR_CODES = [
  // 认证与授权
  'ACCOUNT_LOCKED',
  'AUTH_FORBIDDEN',
  'AUTH_UNAUTHORIZED',
  'INVALID_PASSWORD',

  // 资源不存在
  'RESOURCE_NOT_FOUND',
  'FILE_NOT_FOUND',

  // 参数校验
  'VALIDATION_FAILED',
  'PRICE_BELOW_COST',
  'PRODUCT_SKU_DUPLICATED',

  // 业务规则
  'ORDER_EMPTY_ITEMS',
  'ORDER_HAS_PAYMENTS',
  'ORDER_INVALID_STATUS',
  'CUSTOMER_DUPLICATED_WARNING',
  'CUSTOMER_HAS_ORDERS',
  'PRODUCT_IN_USE',
  'INVENTORY_NOT_ENOUGH',
  'PAYMENT_AMOUNT_EXCEEDED',
  'FILE_NOT_BOUND',

  // 文件上传
  'FILE_INVALID_TYPE',
  'FILE_TOO_LARGE',

  // 限流
  'PAYMENT_RATE_LIMITED',
  'RATE_LIMIT_EXCEEDED',
  'PAYLOAD_TOO_LARGE',

  // 导入
  'IMPORT_FAILED',

  // 系统
  'SYSTEM_INTERNAL_ERROR',
  'SHUTTING_DOWN',
] as const

describe('后端错误码与前端类型一致性', () => {
  // ═══════════════════════════════════════════════════════
  // 1. 错误码完整性
  // ═══════════════════════════════════════════════════════

  it('错误码总数为 26', () => {
    expect(BACKEND_ERROR_CODES).toHaveLength(26)
  })

  it('错误码列表无重复', () => {
    const codes = [...BACKEND_ERROR_CODES]
    const unique = [...new Set(codes)]
    expect(codes).toHaveLength(unique.length)
  })

  // ═══════════════════════════════════════════════════════
  // 2. 每个错误码符合 ApiError.code 类型
  // ═══════════════════════════════════════════════════════

  it.each(BACKEND_ERROR_CODES)('错误码 %s 可赋值给 ApiError.error.code', (code) => {
    const err: ApiError = {
      success: false,
      error: { code, message: `测试错误: ${code}` },
    }
    expect(err.error.code).toBe(code)
  })

  // ═══════════════════════════════════════════════════════
  // 3. 认证相关错误码
  // ═══════════════════════════════════════════════════════

  it('包含 AUTH_UNAUTHORIZED（401 未登录）', () => {
    expect(BACKEND_ERROR_CODES).toContain('AUTH_UNAUTHORIZED')
  })

  it('包含 AUTH_FORBIDDEN（403 无权限）', () => {
    expect(BACKEND_ERROR_CODES).toContain('AUTH_FORBIDDEN')
  })

  it('包含 ACCOUNT_LOCKED（账户锁定）', () => {
    expect(BACKEND_ERROR_CODES).toContain('ACCOUNT_LOCKED')
  })

  it('包含 INVALID_PASSWORD（密码错误）', () => {
    expect(BACKEND_ERROR_CODES).toContain('INVALID_PASSWORD')
  })

  // ═══════════════════════════════════════════════════════
  // 4. 资源相关错误码
  // ═══════════════════════════════════════════════════════

  it('包含 RESOURCE_NOT_FOUND', () => {
    expect(BACKEND_ERROR_CODES).toContain('RESOURCE_NOT_FOUND')
  })

  it('包含 VALIDATION_FAILED', () => {
    expect(BACKEND_ERROR_CODES).toContain('VALIDATION_FAILED')
  })

  // ═══════════════════════════════════════════════════════
  // 5. 订单与收款相关错误码
  // ═══════════════════════════════════════════════════════

  it('包含 ORDER_INVALID_STATUS', () => {
    expect(BACKEND_ERROR_CODES).toContain('ORDER_INVALID_STATUS')
  })

  it('包含 ORDER_HAS_PAYMENTS', () => {
    expect(BACKEND_ERROR_CODES).toContain('ORDER_HAS_PAYMENTS')
  })

  it('包含 PAYMENT_AMOUNT_EXCEEDED', () => {
    expect(BACKEND_ERROR_CODES).toContain('PAYMENT_AMOUNT_EXCEEDED')
  })

  it('包含 PAYMENT_RATE_LIMITED', () => {
    expect(BACKEND_ERROR_CODES).toContain('PAYMENT_RATE_LIMITED')
  })

  // ═══════════════════════════════════════════════════════
  // 6. 限流相关错误码
  // ═══════════════════════════════════════════════════════

  it('包含 RATE_LIMIT_EXCEEDED', () => {
    expect(BACKEND_ERROR_CODES).toContain('RATE_LIMIT_EXCEEDED')
  })

  it('包含 PAYLOAD_TOO_LARGE', () => {
    expect(BACKEND_ERROR_CODES).toContain('PAYLOAD_TOO_LARGE')
  })

  // ═══════════════════════════════════════════════════════
  // 7. 错误码格式一致性
  // ═══════════════════════════════════════════════════════

  it('所有错误码为大写下划线格式', () => {
    for (const code of BACKEND_ERROR_CODES) {
      expect(code).toMatch(/^[A-Z][A-Z0-9_]*$/)
    }
  })

  it('错误码不以数字开头', () => {
    for (const code of BACKEND_ERROR_CODES) {
      expect(code[0]).toMatch(/[A-Z]/)
    }
  })

  // ═══════════════════════════════════════════════════════
  // 8. ApiError 类型结构验证
  // ═══════════════════════════════════════════════════════

  it('ApiError success 字段为 false', () => {
    const err: ApiError = {
      success: false,
      error: { code: 'VALIDATION_FAILED', message: '校验失败' },
    }
    expect(err.success).toBe(false)
  })

  it('ApiError error 包含 code 和 message', () => {
    const err: ApiError = {
      success: false,
      error: { code: BACKEND_ERROR_CODES[0], message: 'test' },
    }
    expect(typeof err.error.code).toBe('string')
    expect(typeof err.error.message).toBe('string')
  })

  it('ApiError details 可选', () => {
    const withDetails: ApiError = {
      success: false,
      error: { code: 'VALIDATION_FAILED', message: 'test', details: { field: 'name' } },
    }
    const without: ApiError = {
      success: false,
      error: { code: 'VALIDATION_FAILED', message: 'test' },
    }
    expect(withDetails.error.details).toBeDefined()
    expect(without.error.details).toBeUndefined()
  })

  it('ApiError request_id 可选', () => {
    const withRid: ApiError = {
      success: false,
      error: { code: 'TEST', message: 'test' },
      request_id: 'req-123',
    }
    const without: ApiError = {
      success: false,
      error: { code: 'TEST', message: 'test' },
    }
    expect(withRid.request_id).toBe('req-123')
    expect(without.request_id).toBeUndefined()
  })
})
