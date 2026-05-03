/**
 * 代码质量：前端工具函数 & 类型结构边界测试
 * 覆盖 formatAmount/formatPercent 边界、getApiErrorMessage 解析、
 * isToastDisplayed 判断、API 类型结构验证
 */

import { describe, it, expect } from 'vitest'
import { formatAmount, formatPercent, getApiErrorMessage, isToastDisplayed } from '@/utils'
import type { ApiResponse, ApiError, PaginatedData } from '@/types'

// ═══════════════════════════════════════════════════════
// 1. formatAmount 边界测试
// ═══════════════════════════════════════════════════════

describe('formatAmount 边界', () => {
  it('null 返回 "--"', () => {
    expect(formatAmount(null)).toBe('--')
  })

  it('undefined 返回 "--"', () => {
    expect(formatAmount(undefined)).toBe('--')
  })

  it('整数显示两位小数', () => {
    expect(formatAmount(100)).toBe('100.00')
  })

  it('浮点数保留两位小数', () => {
    expect(formatAmount(99.9)).toBe('99.90')
  })

  it('字符串数字正确解析', () => {
    expect(formatAmount('123.456')).toBe('123.46')
  })

  it('NaN 字符串返回 "--"', () => {
    expect(formatAmount('abc')).toBe('--')
  })

  it('空字符串返回 "--"', () => {
    expect(formatAmount('')).toBe('--')
  })

  it('零值显示 "0.00"', () => {
    expect(formatAmount(0)).toBe('0.00')
  })

  it('负数保留两位小数', () => {
    expect(formatAmount(-50.5)).toBe('-50.50')
  })

  it('大数值不丢失精度', () => {
    expect(formatAmount(9999999999.99)).toBe('9999999999.99')
  })
})

// ═══════════════════════════════════════════════════════
// 2. formatPercent 边界测试
// ═══════════════════════════════════════════════════════

describe('formatPercent 边界', () => {
  it('null 返回 "--"', () => {
    expect(formatPercent(null)).toBe('--')
  })

  it('undefined 返回 "--"', () => {
    expect(formatPercent(undefined)).toBe('--')
  })

  it('0.5 显示 "50.00%"', () => {
    expect(formatPercent(0.5)).toBe('50.00%')
  })

  it('1 显示 "100.00%"', () => {
    expect(formatPercent(1)).toBe('100.00%')
  })

  it('0 显示 "0.00%"', () => {
    expect(formatPercent(0)).toBe('0.00%')
  })

  it('字符串 "0.1234" 显示 "12.34%"', () => {
    expect(formatPercent('0.1234')).toBe('12.34%')
  })

  it('NaN 字符串返回 "--"', () => {
    expect(formatPercent('not-a-number')).toBe('--')
  })

  it('负数百分比正常显示', () => {
    expect(formatPercent(-0.1)).toBe('-10.00%')
  })

  it('超过 100% 正常显示', () => {
    expect(formatPercent(2.5)).toBe('250.00%')
  })
})

// ═══════════════════════════════════════════════════════
// 3. getApiErrorMessage 边界测试
// ═══════════════════════════════════════════════════════

describe('getApiErrorMessage 边界', () => {
  it('标准 error.message 优先提取', () => {
    const e = { response: { data: { error: { message: '参数错误' } } } }
    expect(getApiErrorMessage(e)).toBe('参数错误')
  })

  it('无 error.message 时回退到 detail.message', () => {
    const e = { response: { data: { detail: { message: '详情错误' } } } }
    expect(getApiErrorMessage(e)).toBe('详情错误')
  })

  it('error.message 优先于 detail.message', () => {
    const e = {
      response: {
        data: {
          error: { message: '首选' },
          detail: { message: '备选' },
        },
      },
    }
    expect(getApiErrorMessage(e)).toBe('首选')
  })

  it('无响应数据时使用默认 fallback', () => {
    expect(getApiErrorMessage({})).toBe('操作失败')
  })

  it('自定义 fallback 字符串', () => {
    // getApiErrorMessage(null) 会崩溃（null.response），这是已知行为
    // 传入空对象即可
    expect(getApiErrorMessage({}, '自定义失败')).toBe('自定义失败')
  })

  it('空 response.data 使用 fallback', () => {
    const e = { response: { data: {} } }
    expect(getApiErrorMessage(e)).toBe('操作失败')
  })

  it('response 存在但 data 为 null 时使用 fallback', () => {
    const e = { response: { data: null } }
    expect(getApiErrorMessage(e)).toBe('操作失败')
  })

  it('error.message 为空字符串时走 fallback', () => {
    const e = { response: { data: { error: { message: '' } } } }
    expect(getApiErrorMessage(e)).toBe('操作失败')
  })

  it('detail.message 为空字符串时走 fallback', () => {
    const e = { response: { data: { detail: { message: '' } } } }
    expect(getApiErrorMessage(e)).toBe('操作失败')
  })

  it('error.message 为非字符串 falsy 时走 fallback', () => {
    const e = { response: { data: { error: { message: 0 } } } }
    expect(getApiErrorMessage(e)).toBe('操作失败')
  })
})

// ═══════════════════════════════════════════════════════
// 4. isToastDisplayed 边界测试
// ═══════════════════════════════════════════════════════

describe('isToastDisplayed 边界', () => {
  it('_toastDisplayed=true 返回 true', () => {
    const e = { _toastDisplayed: true }
    expect(isToastDisplayed(e)).toBe(true)
  })

  it('_toastDisplayed=false 返回 false', () => {
    const e = { _toastDisplayed: false }
    expect(isToastDisplayed(e)).toBe(false)
  })

  it('无 _toastDisplayed 属性返回 false', () => {
    const e = { message: 'some error' }
    expect(isToastDisplayed(e)).toBe(false)
  })

  it('null 返回 false', () => {
    expect(isToastDisplayed(null)).toBe(false)
  })

  it('undefined 返回 false', () => {
    expect(isToastDisplayed(undefined)).toBe(false)
  })

  it('字符串返回 false', () => {
    expect(isToastDisplayed('error')).toBe(false)
  })

  it('数字返回 false', () => {
    expect(isToastDisplayed(42)).toBe(false)
  })

  it('空对象返回 false', () => {
    expect(isToastDisplayed({})).toBe(false)
  })
})

// ═══════════════════════════════════════════════════════
// 5. API 类型结构验证（运行时检查）
// ═══════════════════════════════════════════════════════

describe('API 类型结构', () => {
  it('ApiResponse 类型包含必要字段', () => {
    const resp: ApiResponse<string> = {
      success: true,
      data: 'test',
      message: 'ok',
    }
    expect(resp.success).toBe(true)
    expect(resp.data).toBe('test')
    expect(resp.message).toBe('ok')
  })

  it('ApiResponse 可选 request_id', () => {
    const resp: ApiResponse<string> = {
      success: true,
      data: 'test',
      message: 'ok',
      request_id: 'req-123',
    }
    expect(resp.request_id).toBe('req-123')
  })

  it('ApiError 类型包含必要字段', () => {
    const err: ApiError = {
      success: false,
      error: {
        code: 'VALIDATION_FAILED',
        message: '校验失败',
      },
    }
    expect(err.success).toBe(false)
    expect(err.error.code).toBe('VALIDATION_FAILED')
    expect(err.error.message).toBe('校验失败')
  })

  it('ApiError 可选 details 和 request_id', () => {
    const err: ApiError = {
      success: false,
      error: {
        code: 'BAD_REQUEST',
        message: '参数错误',
        details: { field: 'name' },
      },
      request_id: 'req-456',
    }
    expect(err.error.details).toEqual({ field: 'name' })
    expect(err.request_id).toBe('req-456')
  })

  it('PaginatedData 包含分页字段', () => {
    const page: PaginatedData<string> = {
      items: ['a', 'b'],
      page: 1,
      page_size: 20,
      total: 100,
    }
    expect(page.items).toHaveLength(2)
    expect(page.total).toBe(100)
  })

  it('PaginatedData items 可为空数组', () => {
    const page: PaginatedData<string> = {
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
    }
    expect(page.items).toHaveLength(0)
    expect(page.total).toBe(0)
  })
})
