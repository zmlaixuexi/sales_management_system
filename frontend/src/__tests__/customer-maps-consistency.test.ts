/**
 * 需求符合性：前端 customerSourceMap/customerLevelMap 与后端常量一致性测试
 * 验证前端映射与后端 CustomerSource/CustomerLevel Literal 类型一致
 */

import { describe, it, expect } from 'vitest'
import {
  customerSourceMap,
  customerLevelMap,
} from '../constants/statusMaps'

// 后端定义（从 backend/app/schemas/customer.py 提取）
const BACKEND_CUSTOMER_SOURCES = ['referral', 'online', 'offline', 'ad', 'other'] as const
const BACKEND_CUSTOMER_LEVELS = ['vip', 'important', 'normal', 'potential'] as const

describe('前端客户映射与后端常量一致性', () => {
  // ═══════════════════════════════════════════════════════
  // 1. 客户来源映射
  // ═══════════════════════════════════════════════════════

  it('前端包含所有后端客户来源', () => {
    for (const source of BACKEND_CUSTOMER_SOURCES) {
      expect(customerSourceMap[source], `缺少客户来源: ${source}`).toBeDefined()
    }
  })

  it('前端客户来源不含多余来源', () => {
    const frontendSources = Object.keys(customerSourceMap)
    for (const s of frontendSources) {
      expect(BACKEND_CUSTOMER_SOURCES, `多余客户来源: ${s}`).toContain(s)
    }
  })

  it('前端客户来源数量与后端一致', () => {
    expect(Object.keys(customerSourceMap)).toHaveLength(BACKEND_CUSTOMER_SOURCES.length)
  })

  it('所有客户来源 label 非空', () => {
    for (const [, label] of Object.entries(customerSourceMap)) {
      expect(label).toBeTruthy()
      expect(typeof label).toBe('string')
    }
  })

  it('客户来源包含关键值', () => {
    expect(customerSourceMap['referral']).toBe('转介绍')
    expect(customerSourceMap['online']).toBe('线上')
    expect(customerSourceMap['offline']).toBe('线下')
    expect(customerSourceMap['ad']).toBe('广告')
    expect(customerSourceMap['other']).toBe('其他')
  })

  // ═══════════════════════════════════════════════════════
  // 2. 客户等级映射
  // ═══════════════════════════════════════════════════════

  it('前端包含所有后端客户等级', () => {
    for (const level of BACKEND_CUSTOMER_LEVELS) {
      expect(customerLevelMap[level], `缺少客户等级: ${level}`).toBeDefined()
    }
  })

  it('前端客户等级不含多余等级', () => {
    const frontendLevels = Object.keys(customerLevelMap)
    for (const l of frontendLevels) {
      expect(BACKEND_CUSTOMER_LEVELS, `多余客户等级: ${l}`).toContain(l)
    }
  })

  it('前端客户等级数量与后端一致', () => {
    expect(Object.keys(customerLevelMap)).toHaveLength(BACKEND_CUSTOMER_LEVELS.length)
  })

  it('每个客户等级有 color 和 label', () => {
    for (const [, info] of Object.entries(customerLevelMap)) {
      expect(info.color).toBeTruthy()
      expect(info.label).toBeTruthy()
    }
  })

  it('客户等级包含关键值', () => {
    expect(customerLevelMap['vip'].label).toBe('VIP')
    expect(customerLevelMap['important'].label).toBe('重要')
    expect(customerLevelMap['normal'].label).toBe('普通')
    expect(customerLevelMap['potential'].label).toBe('潜在')
  })

  it('客户等级默认值 normal 存在', () => {
    expect(customerLevelMap['normal']).toBeDefined()
    expect(customerLevelMap['normal'].label).toBe('普通')
  })

  // ═══════════════════════════════════════════════════════
  // 3. 后端常量完整性
  // ═══════════════════════════════════════════════════════

  it('后端客户来源列表完整（5 项）', () => {
    expect(BACKEND_CUSTOMER_SOURCES).toHaveLength(5)
  })

  it('后端客户等级列表完整（4 项）', () => {
    expect(BACKEND_CUSTOMER_LEVELS).toHaveLength(4)
  })
})
