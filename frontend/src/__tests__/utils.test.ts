import { describe, it, expect } from 'vitest'
import { formatAmount, formatPercent, getApiErrorMessage } from '@/utils'

describe('formatAmount', () => {
  it('格式化数字金额为两位小数', () => {
    expect(formatAmount(100)).toBe('100.00')
    expect(formatAmount(99.5)).toBe('99.50')
    expect(formatAmount(0)).toBe('0.00')
  })

  it('格式化字符串金额', () => {
    expect(formatAmount('200.5')).toBe('200.50')
    expect(formatAmount('0')).toBe('0.00')
  })

  it('处理 null/undefined', () => {
    expect(formatAmount(null)).toBe('--')
    expect(formatAmount(undefined)).toBe('--')
  })

  it('处理无效字符串', () => {
    expect(formatAmount('abc')).toBe('--')
  })

  it('处理负数', () => {
    expect(formatAmount(-50)).toBe('-50.00')
    expect(formatAmount('-99.9')).toBe('-99.90')
  })

  it('处理大数', () => {
    expect(formatAmount(9999999.99)).toBe('9999999.99')
    expect(formatAmount('1234567.89')).toBe('1234567.89')
  })

  it('处理空字符串', () => {
    expect(formatAmount('')).toBe('--')
  })
})

describe('formatPercent', () => {
  it('格式化小数为百分比', () => {
    expect(formatPercent(0.1234)).toBe('12.34%')
    expect(formatPercent(0.5)).toBe('50.00%')
    expect(formatPercent(1)).toBe('100.00%')
  })

  it('格式化字符串', () => {
    expect(formatPercent('0.25')).toBe('25.00%')
  })

  it('处理 null/undefined', () => {
    expect(formatPercent(null)).toBe('--')
    expect(formatPercent(undefined)).toBe('--')
  })

  it('处理无效字符串', () => {
    expect(formatPercent('abc')).toBe('--')
  })

  it('处理负数百分比', () => {
    expect(formatPercent(-0.1)).toBe('-10.00%')
  })

  it('处理超过 100% 的值', () => {
    expect(formatPercent(1.5)).toBe('150.00%')
    expect(formatPercent(2)).toBe('200.00%')
  })

  it('处理零', () => {
    expect(formatPercent(0)).toBe('0.00%')
    expect(formatPercent('0')).toBe('0.00%')
  })
})

describe('getApiErrorMessage', () => {
  it('提取 error.message（新格式）', () => {
    const err = { response: { data: { error: { code: 'VALIDATION_FAILED', message: '参数校验失败' } } } }
    expect(getApiErrorMessage(err)).toBe('参数校验失败')
  })

  it('提取 detail.message（旧格式）', () => {
    const err = { response: { data: { detail: { message: '库存不足' } } } }
    expect(getApiErrorMessage(err)).toBe('库存不足')
  })

  it('error.message 优先于 detail.message', () => {
    const err = { response: { data: { error: { code: 'X', message: '新消息' }, detail: { message: '旧消息' } } } }
    expect(getApiErrorMessage(err)).toBe('新消息')
  })

  it('无 response 时使用 fallback', () => {
    expect(getApiErrorMessage({})).toBe('操作失败')
    expect(getApiErrorMessage({}, '删除失败')).toBe('删除失败')
  })

  it('无 error.message 且无 detail.message 时使用 fallback', () => {
    const err = { response: { data: {} } }
    expect(getApiErrorMessage(err)).toBe('操作失败')
  })
})
