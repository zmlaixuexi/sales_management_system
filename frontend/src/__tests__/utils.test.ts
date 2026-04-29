import { describe, it, expect } from 'vitest'
import { formatAmount, formatPercent } from '@/utils'

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
})
