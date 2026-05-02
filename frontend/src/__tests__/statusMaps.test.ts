import { describe, it, expect } from 'vitest'
import {
  productStatusMap,
  orderStatusMap,
  paymentStatusMap,
  customerSourceMap,
  customerLevelMap,
} from '@/constants/statusMaps'

describe('商品状态映射', () => {
  it('包含三种商品状态', () => {
    expect(Object.keys(productStatusMap)).toHaveLength(3)
    expect(productStatusMap.active.label).toBe('上架')
    expect(productStatusMap.inactive.label).toBe('下架')
    expect(productStatusMap.disabled.label).toBe('停用')
  })

  it('每种状态都有 color 和 label', () => {
    Object.values(productStatusMap).forEach((info) => {
      expect(info).toHaveProperty('color')
      expect(info).toHaveProperty('label')
      expect(info.label.length).toBeGreaterThan(0)
    })
  })
})

describe('订单状态映射', () => {
  it('包含 5 种订单状态', () => {
    expect(Object.keys(orderStatusMap)).toHaveLength(5)
    expect(orderStatusMap.draft.label).toBe('草稿')
    expect(orderStatusMap.confirmed.label).toBe('已确认')
    expect(orderStatusMap.cancelled.label).toBe('已取消')
    expect(orderStatusMap.partially_paid.label).toBe('部分收款')
    expect(orderStatusMap.completed.label).toBe('已完成')
  })

  it('每种状态都有 color 和 label', () => {
    Object.values(orderStatusMap).forEach((info) => {
      expect(info).toHaveProperty('color')
      expect(info).toHaveProperty('label')
    })
  })
})

describe('收款状态映射', () => {
  it('包含 2 种收款状态', () => {
    expect(Object.keys(paymentStatusMap)).toHaveLength(2)
    expect(paymentStatusMap.normal.label).toBe('正常')
    expect(paymentStatusMap.reversed.label).toBe('已冲正')
  })

  it('每种状态都有 color 和 label', () => {
    Object.values(paymentStatusMap).forEach((info) => {
      expect(info).toHaveProperty('color')
      expect(info).toHaveProperty('label')
    })
  })
})

describe('客户来源映射', () => {
  it('包含 5 种来源', () => {
    expect(Object.keys(customerSourceMap)).toHaveLength(5)
    expect(customerSourceMap.referral).toBe('转介绍')
    expect(customerSourceMap.online).toBe('线上')
    expect(customerSourceMap.offline).toBe('线下')
    expect(customerSourceMap.ad).toBe('广告')
    expect(customerSourceMap.other).toBe('其他')
  })

  it('每种来源都有非空标签', () => {
    Object.values(customerSourceMap).forEach((label) => {
      expect(label.length).toBeGreaterThan(0)
    })
  })
})

describe('客户等级映射', () => {
  it('包含 4 种等级', () => {
    expect(Object.keys(customerLevelMap)).toHaveLength(4)
    expect(customerLevelMap.vip.label).toBe('VIP')
    expect(customerLevelMap.important.label).toBe('重要')
    expect(customerLevelMap.normal.label).toBe('普通')
    expect(customerLevelMap.potential.label).toBe('潜在')
  })

  it('每种等级都有 color 和 label', () => {
    Object.values(customerLevelMap).forEach((info) => {
      expect(info).toHaveProperty('color')
      expect(info).toHaveProperty('label')
    })
  })
})
