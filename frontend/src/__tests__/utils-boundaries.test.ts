/**
 * 测试补强：前端 utils 工具函数边界测试
 * 覆盖 formatAmount、formatPercent、getApiErrorMessage、isToastDisplayed
 */

import { describe, it, expect } from 'vitest'
import {
  formatAmount,
  formatPercent,
  getApiErrorMessage,
  isToastDisplayed,
} from '../utils'

// ═══════════════════════════════════════════════════════════
// formatAmount
// ═══════════════════════════════════════════════════════════

describe('formatAmount 边界测试', () => {
  // --- nullish 输入 ---

  it('null 返回 "--"', () => {
    expect(formatAmount(null)).toBe('--')
  })

  it('undefined 返回 "--"', () => {
    expect(formatAmount(undefined)).toBe('--')
  })

  // --- 数字输入 ---

  it('整数 0 返回 "0.00"', () => {
    expect(formatAmount(0)).toBe('0.00')
  })

  it('正整数 123 返回 "123.00"', () => {
    expect(formatAmount(123)).toBe('123.00')
  })

  it('负整数 -50 返回 "-50.00"', () => {
    expect(formatAmount(-50)).toBe('-50.00')
  })

  it('小数 1.5 返回 "1.50"', () => {
    expect(formatAmount(1.5)).toBe('1.50')
  })

  it('已有两位小数 99.99 返回 "99.99"', () => {
    expect(formatAmount(99.99)).toBe('99.99')
  })

  it('超过两位小数 1.234 四舍五入为 "1.23"', () => {
    expect(formatAmount(1.234)).toBe('1.23')
  })

  it('超过两位小数 1.235 四舍五入为 "1.24"', () => {
    expect(formatAmount(1.235)).toBe('1.24')
  })

  it('NaN 返回 "--"', () => {
    expect(formatAmount(NaN)).toBe('--')
  })

  it('Infinity 返回 "Infinity"（toFixed 行为）', () => {
    expect(formatAmount(Infinity)).toBe('Infinity')
  })

  it('-Infinity 返回 "-Infinity"', () => {
    expect(formatAmount(-Infinity)).toBe('-Infinity')
  })

  // --- 字符串输入 ---

  it('字符串 "100" 返回 "100.00"', () => {
    expect(formatAmount('100')).toBe('100.00')
  })

  it('字符串 "0" 返回 "0.00"', () => {
    expect(formatAmount('0')).toBe('0.00')
  })

  it('字符串 "3.14159" 四舍五入为 "3.14"', () => {
    expect(formatAmount('3.14159')).toBe('3.14')
  })

  it('空字符串返回 "--"（parseFloat 返回 NaN）', () => {
    expect(formatAmount('')).toBe('--')
  })

  it('非数字字符串 "abc" 返回 "--"', () => {
    expect(formatAmount('abc')).toBe('--')
  })

  it('parseFloat 部分匹配：字符串 "12.34abc" 返回 "12.34"', () => {
    expect(formatAmount('12.34abc')).toBe('12.34')
  })

  it('parseFloat 部分匹配：字符串 "  3.5  " 返回 "3.50"', () => {
    expect(formatAmount('  3.5  ')).toBe('3.50')
  })

  it('科学计数法字符串 "1e3" 返回 "1000.00"', () => {
    expect(formatAmount('1e3')).toBe('1000.00')
  })
})

// ═══════════════════════════════════════════════════════════
// formatPercent
// ═══════════════════════════════════════════════════════════

describe('formatPercent 边界测试', () => {
  // --- nullish 输入 ---

  it('null 返回 "--"', () => {
    expect(formatPercent(null)).toBe('--')
  })

  it('undefined 返回 "--"', () => {
    expect(formatPercent(undefined)).toBe('--')
  })

  // --- 数字输入 ---

  it('0 返回 "0.00%"', () => {
    expect(formatPercent(0)).toBe('0.00%')
  })

  it('0.1234 返回 "12.34%"', () => {
    expect(formatPercent(0.1234)).toBe('12.34%')
  })

  it('1 返回 "100.00%"', () => {
    expect(formatPercent(1)).toBe('100.00%')
  })

  it('1.5 返回 "150.00%"（超过 100%）', () => {
    expect(formatPercent(1.5)).toBe('150.00%')
  })

  it('-0.5 返回 "-50.00%"（负值）', () => {
    expect(formatPercent(-0.5)).toBe('-50.00%')
  })

  it('NaN 返回 "--"', () => {
    expect(formatPercent(NaN)).toBe('--')
  })

  it('Infinity 返回 "Infinity%"', () => {
    expect(formatPercent(Infinity)).toBe('Infinity%')
  })

  // --- 字符串输入 ---

  it('字符串 "0.5" 返回 "50.00%"', () => {
    expect(formatPercent('0.5')).toBe('50.00%')
  })

  it('空字符串返回 "--"', () => {
    expect(formatPercent('')).toBe('--')
  })

  it('非数字字符串 "abc" 返回 "--"', () => {
    expect(formatPercent('abc')).toBe('--')
  })

  it('字符串 "0.005" 返回 "0.50%"', () => {
    expect(formatPercent('0.005')).toBe('0.50%')
  })
})

// ═══════════════════════════════════════════════════════════
// getApiErrorMessage
// ═══════════════════════════════════════════════════════════

describe('getApiErrorMessage 边界测试', () => {
  // --- 原始值输入（as 类型转换导致 TypeError） ---

  it('null 输入触发 TypeError', () => {
    expect(() => getApiErrorMessage(null)).toThrow()
  })

  it('undefined 输入触发 TypeError', () => {
    expect(() => getApiErrorMessage(undefined)).toThrow()
  })

  it('字符串输入返回默认 fallback（对象盒装，?. 安全）', () => {
    expect(getApiErrorMessage('error')).toBe('操作失败')
  })

  it('数字输入返回默认 fallback（对象盒装，?. 安全）', () => {
    expect(getApiErrorMessage(0)).toBe('操作失败')
  })

  // --- 结构化 API 错误 ---

  it('提取 response.data.error.message', () => {
    const err = { response: { data: { error: { message: '参数校验失败' } } } }
    expect(getApiErrorMessage(err)).toBe('参数校验失败')
  })

  it('提取 response.data.detail.message（无 error.message 时）', () => {
    const err = { response: { data: { detail: { message: '服务器内部错误' } } } }
    expect(getApiErrorMessage(err)).toBe('服务器内部错误')
  })

  it('error.message 优先于 detail.message', () => {
    const err = {
      response: {
        data: {
          error: { message: '优先消息' },
          detail: { message: '次要消息' },
        },
      },
    }
    expect(getApiErrorMessage(err)).toBe('优先消息')
  })

  it('error.message 为空字符串时回退到 detail.message', () => {
    const err = {
      response: {
        data: {
          error: { message: '' },
          detail: { message: '回退消息' },
        },
      },
    }
    expect(getApiErrorMessage(err)).toBe('回退消息')
  })

  // --- 无 response ---

  it('空对象 {} 返回默认 fallback', () => {
    expect(getApiErrorMessage({})).toBe('操作失败')
  })

  it('response 为 null 返回默认 fallback', () => {
    expect(getApiErrorMessage({ response: null })).toBe('操作失败')
  })

  it('response.data 为 undefined 返回默认 fallback', () => {
    expect(getApiErrorMessage({ response: {} })).toBe('操作失败')
  })

  it('response.data.error 为空对象返回默认 fallback', () => {
    expect(getApiErrorMessage({ response: { data: { error: {} } } })).toBe('操作失败')
  })

  // --- 自定义 fallback ---

  it('自定义 fallback 被使用（传入空对象避免 TypeError）', () => {
    expect(getApiErrorMessage({}, '自定义错误')).toBe('自定义错误')
  })

  it('自定义 fallback 为空字符串可用', () => {
    expect(getApiErrorMessage({}, '')).toBe('')
  })

  it('null 输入触发 TypeError（as 类型转换不安全）', () => {
    expect(() => getApiErrorMessage(null)).toThrow(TypeError)
  })
})

// ═══════════════════════════════════════════════════════════
// isToastDisplayed
// ═══════════════════════════════════════════════════════════

describe('isToastDisplayed 边界测试', () => {
  // --- 非对象输入 ---

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

  it('布尔值 true 返回 false', () => {
    expect(isToastDisplayed(true)).toBe(false)
  })

  // --- 对象输入 ---

  it('空对象 {} 返回 false', () => {
    expect(isToastDisplayed({})).toBe(false)
  })

  it('_toastDisplayed: true 返回 true', () => {
    expect(isToastDisplayed({ _toastDisplayed: true })).toBe(true)
  })

  it('_toastDisplayed: false 返回 false', () => {
    expect(isToastDisplayed({ _toastDisplayed: false })).toBe(false)
  })

  it('_toastDisplayed 为 truthy 非布尔值 "yes" 返回 false（严格 === 检查）', () => {
    expect(isToastDisplayed({ _toastDisplayed: 'yes' })).toBe(false)
  })

  it('_toastDisplayed 为 truthy 非布尔值 1 返回 false（严格 === 检查）', () => {
    expect(isToastDisplayed({ _toastDisplayed: 1 })).toBe(false)
  })

  it('包含其他属性和 _toastDisplayed: true 仍返回 true', () => {
    expect(isToastDisplayed({ message: 'err', _toastDisplayed: true })).toBe(true)
  })
})
