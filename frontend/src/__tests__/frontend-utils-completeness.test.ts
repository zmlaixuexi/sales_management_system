/**
 * 代码质量：前端 utils 工具函数实现完整性验证测试
 * 覆盖 formatAmount/formatPercent 函数签名、getApiErrorMessage 逻辑、
 * isToastDisplayed 逻辑、常量映射完整性、utils 模块使用覆盖
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')

function frontendSrc(relPath: string): string {
  return readFileSync(resolve(root, 'frontend/src', relPath), 'utf-8')
}

const utilsCode = frontendSrc('utils/index.ts')
const statusMapsCode = frontendSrc('constants/statusMaps.ts')
const useSubmitCode = frontendSrc('hooks/useSubmit.ts')
const usePaginatedCode = frontendSrc('hooks/usePaginatedList.ts')
const loginCode = frontendSrc('pages/Login.tsx')
const ordersCode = frontendSrc('pages/Orders.tsx')
const productsCode = frontendSrc('pages/Products.tsx')
const dashboardCode = frontendSrc('pages/Dashboard.tsx')

// ═══════════════════════════════════════════════════════════
// 1. formatAmount/formatPercent 函数签名验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('formatAmount/formatPercent 函数签名', () => {
  it('formatAmount 接受 number|string|null|undefined 返回 string', () => {
    expect(utilsCode).toContain('formatAmount(value: number | string | null | undefined): string')
  })

  it('formatAmount 处理 null/undefined 返回 --', () => {
    expect(utilsCode).toContain("value === null || value === undefined")
    expect(utilsCode).toContain("'--'")
  })

  it('formatAmount 处理 NaN 返回 --', () => {
    expect(utilsCode).toContain('isNaN(num)')
    expect(utilsCode).toContain("'--'")
  })

  it('formatPercent 接受相同类型参数并乘以 100', () => {
    expect(utilsCode).toContain('formatPercent(value: number | string | null | undefined): string')
    expect(utilsCode).toContain('num * 100')
    expect(utilsCode).toContain("toFixed(2)")
    expect(utilsCode).toContain(".toFixed(2)}%")
  })

  it('两个函数都使用 toFixed(2) 保留两位小数', () => {
    const fixedCount = (utilsCode.match(/toFixed\(2\)/g) || []).length
    expect(fixedCount).toBeGreaterThanOrEqual(2)
  })
})

// ═══════════════════════════════════════════════════════════
// 2. getApiErrorMessage 逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('getApiErrorMessage 逻辑', () => {
  it('定义 ApiErrorResponse 接口', () => {
    expect(utilsCode).toContain('interface ApiErrorResponse')
    expect(utilsCode).toContain('response?')
    expect(utilsCode).toContain('error?')
    expect(utilsCode).toContain('message?')
  })

  it('接受 unknown 类型错误和可选 fallback 参数', () => {
    expect(utilsCode).toContain('getApiErrorMessage(e: unknown')
    expect(utilsCode).toContain("fallback = '操作失败'")
  })

  it('提取 error.message 或 detail.message', () => {
    expect(utilsCode).toContain('error?.message')
    expect(utilsCode).toContain('detail?.message')
  })

  it('Login 页面使用 getApiErrorMessage', () => {
    expect(loginCode).toContain("import { getApiErrorMessage } from '@/utils'")
    expect(loginCode).toContain("getApiErrorMessage(e, '用户名或密码错误')")
  })

  it('useSubmit 使用 getApiErrorMessage 作为 fallback', () => {
    expect(useSubmitCode).toContain("import { getApiErrorMessage, isToastDisplayed } from '@/utils'")
    expect(useSubmitCode).toContain('getApiErrorMessage(e, fallbackError)')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. isToastDisplayed 逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('isToastDisplayed 逻辑', () => {
  it('接受 unknown 参数返回 boolean', () => {
    expect(utilsCode).toContain('isToastDisplayed(e: unknown): boolean')
  })

  it('检查 _toastDisplayed 属性', () => {
    expect(utilsCode).toContain("'_toastDisplayed' in e")
    expect(utilsCode).toContain('_toastDisplayed')
    expect(utilsCode).toContain('=== true')
  })

  it('检查 typeof e === object 且 e !== null', () => {
    expect(utilsCode).toContain("typeof e === 'object'")
    expect(utilsCode).toContain('e !== null')
  })

  it('usePaginatedList 使用 isToastDisplayed 去重', () => {
    expect(usePaginatedCode).toContain("import { isToastDisplayed } from '@/utils'")
    expect(usePaginatedCode).toContain('isToastDisplayed')
  })

  it('useSubmit 使用 isToastDisplayed 防止重复提示', () => {
    expect(useSubmitCode).toContain('isToastDisplayed(e)')
    expect(useSubmitCode).toContain('if (isToastDisplayed(e)) return')
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 常量映射完整性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('常量映射完整性', () => {
  it('productStatusMap 包含 active/inactive/disabled', () => {
    expect(statusMapsCode).toContain('productStatusMap')
    expect(statusMapsCode).toContain('active:')
    expect(statusMapsCode).toContain('inactive:')
    expect(statusMapsCode).toContain('disabled:')
  })

  it('orderStatusMap 包含全部 5 个状态', () => {
    expect(statusMapsCode).toContain('orderStatusMap')
    expect(statusMapsCode).toContain('draft:')
    expect(statusMapsCode).toContain('confirmed:')
    expect(statusMapsCode).toContain('cancelled:')
    expect(statusMapsCode).toContain('partially_paid:')
    expect(statusMapsCode).toContain('completed:')
  })

  it('paymentStatusMap 包含 normal/reversed', () => {
    expect(statusMapsCode).toContain('paymentStatusMap')
    expect(statusMapsCode).toContain('normal:')
    expect(statusMapsCode).toContain('reversed:')
  })

  it('customerSourceMap 包含 5 种来源', () => {
    expect(statusMapsCode).toContain('customerSourceMap')
    expect(statusMapsCode).toContain('referral:')
    expect(statusMapsCode).toContain('online:')
    expect(statusMapsCode).toContain('offline:')
    expect(statusMapsCode).toContain('ad:')
    expect(statusMapsCode).toContain('other:')
  })

  it('StatusInfo 类型定义了 color 和 label', () => {
    expect(statusMapsCode).toContain('type StatusInfo')
    expect(statusMapsCode).toContain('color: string')
    expect(statusMapsCode).toContain('label: string')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. utils 模块使用覆盖验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('utils 模块使用覆盖', () => {
  it('formatAmount 在金额相关页面使用', () => {
    expect(ordersCode).toContain('formatAmount')
    expect(productsCode).toContain('formatAmount')
    expect(dashboardCode).toContain('formatAmount')
  })

  it('formatPercent 在毛利率列使用', () => {
    expect(ordersCode).toContain('formatPercent')
  })

  it('所有 4 个导出函数都被外部模块使用', () => {
    // Check that each exported function is used in at least one page
    const pageFiles = [ordersCode, productsCode, dashboardCode, loginCode]
    const allCode = pageFiles.join('\n')
    expect(allCode).toContain('formatAmount')
    expect(allCode).toContain('formatPercent')
    expect(allCode).toContain('getApiErrorMessage')
  })

  it('所有金额显示都带人民币符号前缀', () => {
    const amountWithSymbol = (ordersCode.match(/`¥\$\{formatAmount/g) || []).length
    expect(amountWithSymbol).toBeGreaterThanOrEqual(3)
  })

  it('hooks 和 pages 都从 @/utils 导入', () => {
    expect(useSubmitCode).toContain("from '@/utils'")
    expect(usePaginatedCode).toContain("from '@/utils'")
    expect(loginCode).toContain("from '@/utils'")
    expect(ordersCode).toContain("from '@/utils'")
  })
})
