/**
 * 代码质量：前端类型与后端 API 响应结构一致性测试
 * 验证 TypeScript 类型定义与后端实际响应结构匹配
 */

import { describe, it, expect } from 'vitest'
import type { ApiResponse, ApiError, PaginatedData } from '../types'

describe('前端类型定义一致性', () => {
  // ═══════════════════════════════════════════════════════
  // 1. ApiResponse 结构验证
  // ═══════════════════════════════════════════════════════

  it('ApiResponse 包含 success/data/message', () => {
    const resp: ApiResponse<{ id: string }> = {
      success: true,
      data: { id: '1' },
      message: '操作成功',
    }
    expect(resp.success).toBe(true)
    expect(resp.data).toEqual({ id: '1' })
    expect(resp.message).toBe('操作成功')
  })

  it('ApiResponse request_id 为可选字段', () => {
    const withRid: ApiResponse<null> = {
      success: true,
      data: null,
      message: 'ok',
      request_id: 'abc-123',
    }
    const withoutRid: ApiResponse<null> = {
      success: true,
      data: null,
      message: 'ok',
    }
    expect(withRid.request_id).toBe('abc-123')
    expect(withoutRid.request_id).toBeUndefined()
  })

  it('ApiResponse data 可为任意泛型', () => {
    const strResp: ApiResponse<string> = { success: true, data: 'hello', message: '' }
    const arrResp: ApiResponse<number[]> = { success: true, data: [1, 2], message: '' }
    const nullResp: ApiResponse<null> = { success: true, data: null, message: '' }

    expect(strResp.data).toBe('hello')
    expect(arrResp.data).toEqual([1, 2])
    expect(nullResp.data).toBeNull()
  })

  // ═══════════════════════════════════════════════════════
  // 2. ApiError 结构验证
  // ═══════════════════════════════════════════════════════

  it('ApiError success 为 false', () => {
    const err: ApiError = {
      success: false,
      error: { code: 'TEST_ERROR', message: '测试错误' },
    }
    expect(err.success).toBe(false)
  })

  it('ApiError error 包含 code 和 message', () => {
    const err: ApiError = {
      success: false,
      error: { code: 'RESOURCE_NOT_FOUND', message: '资源不存在' },
    }
    expect(err.error.code).toBe('RESOURCE_NOT_FOUND')
    expect(err.error.message).toBe('资源不存在')
  })

  it('ApiError details 为可选字段', () => {
    const withDetails: ApiError = {
      success: false,
      error: { code: 'VALIDATION_FAILED', message: '校验失败', details: { field: 'name' } },
    }
    const withoutDetails: ApiError = {
      success: false,
      error: { code: 'SYSTEM_ERROR', message: '系统错误' },
    }
    expect(withDetails.error.details).toEqual({ field: 'name' })
    expect(withoutDetails.error.details).toBeUndefined()
  })

  it('ApiError request_id 为可选字段', () => {
    const err: ApiError = {
      success: false,
      error: { code: 'X', message: 'Y' },
      request_id: 'rid-123',
    }
    expect(err.request_id).toBe('rid-123')
  })

  // ═══════════════════════════════════════════════════════
  // 3. PaginatedData 结构验证
  // ═══════════════════════════════════════════════════════

  it('PaginatedData 包含 items/page/page_size/total', () => {
    const data: PaginatedData<{ id: string }> = {
      items: [{ id: '1' }, { id: '2' }],
      page: 1,
      page_size: 20,
      total: 42,
    }
    expect(data.items).toHaveLength(2)
    expect(data.page).toBe(1)
    expect(data.page_size).toBe(20)
    expect(data.total).toBe(42)
  })

  it('PaginatedData items 可为空', () => {
    const data: PaginatedData<string> = {
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
    }
    expect(data.items).toHaveLength(0)
    expect(data.total).toBe(0)
  })

  it('PaginatedData 与后端 paginated_resp 输出匹配', () => {
    // 后端 paginated_resp 返回:
    // { success: true, data: { items, page, page_size, total }, message }
    const backendResp = {
      success: true,
      data: {
        items: ['a', 'b'],
        page: 2,
        page_size: 10,
        total: 25,
      },
      message: '查询成功',
    }
    // PaginatedData 应匹配 data 字段
    const paginated: PaginatedData<string> = backendResp.data
    expect(paginated.items).toEqual(['a', 'b'])
    expect(paginated.page).toBe(2)
    expect(paginated.page_size).toBe(10)
    expect(paginated.total).toBe(25)
  })

  // ═══════════════════════════════════════════════════════
  // 4. 后端错误码常量验证
  // ═══════════════════════════════════════════════════════

  const BACKEND_ERROR_CODES = [
    'AUTH_UNAUTHORIZED',
    'AUTH_FORBIDDEN',
    'RESOURCE_NOT_FOUND',
    'VALIDATION_FAILED',
    'SYSTEM_INTERNAL_ERROR',
    'PAYMENT_RATE_LIMITED',
    'RATE_LIMIT_EXCEEDED',
    'ACCOUNT_LOCKED',
  ] as const

  it.each(BACKEND_ERROR_CODES)('错误码 %s 符合 ApiError code 类型', (code) => {
    const err: ApiError = {
      success: false,
      error: { code, message: `错误: ${code}` },
    }
    expect(err.error.code).toBe(code)
  })

  // ═══════════════════════════════════════════════════════
  // 5. 响应类型守卫
  // ═══════════════════════════════════════════════════════

  it('成功响应可通过 success 字段区分', () => {
    const success: ApiResponse<string> = { success: true, data: 'ok', message: '' }
    const error: ApiError = { success: false, error: { code: 'X', message: 'Y' } }
    expect(success.success).toBe(true)
    expect(error.success).toBe(false)
  })

  it('ApiResponse 与 ApiError 可联合表示所有响应', () => {
    type AllResponses = ApiResponse<string> | ApiError
    const responses: AllResponses[] = [
      { success: true, data: 'ok', message: '' },
      { success: false, error: { code: 'ERR', message: 'fail' } },
    ]
    expect(responses[0].success).toBe(true)
    expect(responses[1].success).toBe(false)
  })

  // ═══════════════════════════════════════════════════════
  // 6. 后端错误响应与 ApiError 字段映射
  // ═══════════════════════════════════════════════════════

  it('HTTPException dict detail 映射到 ApiError', () => {
    // 后端返回: { success: false, error: { code, message }, request_id }
    const raw = {
      success: false,
      error: { code: 'AUTH_UNAUTHORIZED', message: '未登录或 Token 无效' },
      request_id: 'abc-123',
    }
    const err = raw as ApiError
    expect(err.success).toBe(false)
    expect(err.error.code).toBe('AUTH_UNAUTHORIZED')
    expect(err.error.message).toContain('Token')
  })

  it('422 校验错误映射到 ApiError', () => {
    const raw = {
      success: false,
      error: { code: 'VALIDATION_FAILED', message: 'body → name: field required' },
    }
    const err = raw as ApiError
    expect(err.error.code).toBe('VALIDATION_FAILED')
    expect(err.error.message).toContain('name')
  })

  it('404 映射到 ApiError', () => {
    const raw = {
      success: false,
      error: { code: 'RESOURCE_NOT_FOUND', message: '商品不存在' },
    }
    const err = raw as ApiError
    expect(err.error.code).toBe('RESOURCE_NOT_FOUND')
  })

  it('500 映射到 ApiError', () => {
    const raw = {
      success: false,
      error: { code: 'SYSTEM_INTERNAL_ERROR', message: '服务器内部错误，请稍后重试' },
    }
    const err = raw as ApiError
    expect(err.error.code).toBe('SYSTEM_INTERNAL_ERROR')
    expect(err.error.message).not.toContain('Exception') // 不泄露异常类名
  })
})
