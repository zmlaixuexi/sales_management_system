/** 业务状态映射 — 共享常量 */

export type StatusInfo = { color: string; label: string }

// 商品状态
export const productStatusMap: Record<string, StatusInfo> = {
  active: { color: 'green', label: '上架' },
  inactive: { color: 'orange', label: '下架' },
  disabled: { color: 'red', label: '停用' },
}

// 订单状态
export const orderStatusMap: Record<string, StatusInfo> = {
  draft: { color: 'default', label: '草稿' },
  confirmed: { color: 'blue', label: '已确认' },
  cancelled: { color: 'red', label: '已取消' },
  partially_paid: { color: 'orange', label: '部分收款' },
  completed: { color: 'green', label: '已完成' },
}

// 收款状态
export const paymentStatusMap: Record<string, StatusInfo> = {
  normal: { color: 'green', label: '正常' },
  reversed: { color: 'red', label: '已冲正' },
}

// 客户来源
export const customerSourceMap: Record<string, string> = {
  referral: '转介绍',
  online: '线上',
  offline: '线下',
  ad: '广告',
  other: '其他',
}

// 客户等级
export const customerLevelMap: Record<string, StatusInfo> = {
  vip: { color: 'gold', label: 'VIP' },
  important: { color: 'blue', label: '重要' },
  normal: { color: 'default', label: '普通' },
  potential: { color: 'green', label: '潜在' },
}

// 收款方式
export const paymentMethodMap: Record<string, string> = {
  cash: '现金',
  transfer: '银行转账',
  wechat: '微信',
  alipay: '支付宝',
  other: '其他',
}
