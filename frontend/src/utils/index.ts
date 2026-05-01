/**
 * 金额格式化：统一显示两位小数
 */
export function formatAmount(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return '--'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '--'
  return num.toFixed(2)
}

/**
 * 百分比格式化
 */
export function formatPercent(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return '--'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '--'
  return `${(num * 100).toFixed(2)}%`
}

/**
 * 显示 API 错误消息（提取后端 detail.message）
 */
export function getApiErrorMessage(e: unknown, fallback = '操作失败'): string {
  const err = e as { response?: { data?: { detail?: { message?: string } } } }
  return err.response?.data?.detail?.message || fallback
}
