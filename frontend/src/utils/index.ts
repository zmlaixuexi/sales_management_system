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
 * 触发 CSV 文件下载
 */
export async function downloadCsv(path: string, params: Record<string, string | undefined> = {}): Promise<void> {
  const token = localStorage.getItem('access_token')
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

  const query = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '') query.set(k, v)
  })
  const url = `${baseUrl}${path}?${query.toString()}`

  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!resp.ok) throw new Error('导出失败')

  const blob = await resp.blob()
  const disposition = resp.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename=(.+)/)
  const filename = match ? match[1] : 'export.csv'

  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}
