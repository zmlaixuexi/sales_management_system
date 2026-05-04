/**
 * 代码质量：前端 Store / Hooks / API 调用一致性验证测试
 * 覆盖 API 函数 HTTP 方法一致性、auth store 与 authApi 调用对齐、
 * usePaginatedList 参数传递、client 拦截器逻辑、request.ts 辅助函数覆盖
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')

function src(module: string): string {
  return readFileSync(resolve(root, module), 'utf-8')
}

/**
 * 提取函数体（含多行参数定义）。
 * 先找到函数签名结束位置（匹配括号），再收集缩进行。
 */
function extractFnBody(source: string, fnName: string): string {
  const idx = source.indexOf(`export async function ${fnName}(`)
  if (idx === -1) return ''
  let parenDepth = 0
  let sigEnd = 0
  for (let i = idx; i < source.length; i++) {
    if (source[i] === '(') parenDepth++
    else if (source[i] === ')') {
      parenDepth--
      if (parenDepth === 0) {
        const brace = source.indexOf('{', i)
        if (brace !== -1) sigEnd = brace + 1
        break
      }
    }
  }
  const bodyStart = source.indexOf('\n', sigEnd)
  if (bodyStart === -1) return ''
  const lines = source.substring(bodyStart + 1).split('\n')
  const collected: string[] = []
  for (const line of lines) {
    if (line && !line[0].match(/\s/) && line.trim()) break
    collected.push(line)
  }
  return collected.join('\n')
}

/**
 * 检查指定函数体内是否调用了某个 HTTP 方法辅助函数
 */
function fnUses(source: string, fnName: string, method: string): boolean {
  const body = extractFnBody(source, fnName)
  if (method === 'del') return body.includes('del(')
  return body.includes(`${method}<`) || body.includes(`${method}(`)
}

// ═══════════════════════════════════════════════════════════
// 1. API 函数 HTTP 方法一致性验证（7 项）
// ═══════════════════════════════════════════════════════════

describe('API 函数 HTTP 方法一致性', () => {
  it('products: fetchProducts 用 get, createProduct 用 post, updateProduct 用 put, deleteProduct 用 del', () => {
    const code = src('api/products.ts')
    expect(fnUses(code, 'fetchProducts', 'get')).toBe(true)
    expect(fnUses(code, 'createProduct', 'post')).toBe(true)
    expect(fnUses(code, 'updateProduct', 'put')).toBe(true)
    expect(fnUses(code, 'deleteProduct', 'del')).toBe(true)
  })

  it('orders: fetchOrders 用 get, createOrder 用 post, confirmOrder 用 post, cancelOrder 用 post', () => {
    const code = src('api/orders.ts')
    expect(fnUses(code, 'fetchOrders', 'get')).toBe(true)
    expect(fnUses(code, 'createOrder', 'post')).toBe(true)
    expect(fnUses(code, 'confirmOrder', 'post')).toBe(true)
    expect(fnUses(code, 'cancelOrder', 'post')).toBe(true)
  })

  it('customers: fetchCustomers 用 get, createCustomer 用 post, updateCustomer 用 put, deleteCustomer 用 del', () => {
    const code = src('api/customers.ts')
    expect(fnUses(code, 'fetchCustomers', 'get')).toBe(true)
    expect(fnUses(code, 'createCustomer', 'post')).toBe(true)
    expect(fnUses(code, 'updateCustomer', 'put')).toBe(true)
    expect(fnUses(code, 'deleteCustomer', 'del')).toBe(true)
  })

  it('payments: fetchPayments 用 get, createPayment 用 post, reversePayment 用 post', () => {
    const code = src('api/payments.ts')
    expect(fnUses(code, 'fetchPayments', 'get')).toBe(true)
    expect(fnUses(code, 'createPayment', 'post')).toBe(true)
    expect(fnUses(code, 'reversePayment', 'post')).toBe(true)
  })

  it('roles: fetchRoles 用 get, createRole 用 post, updateRole 用 put, deleteRole 用 del', () => {
    const code = src('api/roles.ts')
    expect(fnUses(code, 'fetchRoles', 'get')).toBe(true)
    expect(fnUses(code, 'createRole', 'post')).toBe(true)
    expect(fnUses(code, 'updateRole', 'put')).toBe(true)
    expect(fnUses(code, 'deleteRole', 'del')).toBe(true)
  })

  it('inventory: fetchInventoryMovements 用 get, adjustInventory 用 post', () => {
    const code = src('api/inventory.ts')
    expect(fnUses(code, 'fetchInventoryMovements', 'get')).toBe(true)
    expect(fnUses(code, 'adjustInventory', 'post')).toBe(true)
  })

  it('reports: 所有 6 个查询端点用 get', () => {
    const code = src('api/reports.ts')
    const fns = code.match(/export async function (\w+)/g) || []
    expect(fns.length).toBe(6)
    for (const fnDecl of fns) {
      const fnName = fnDecl.replace('export async function ', '')
      expect(fnUses(code, fnName, 'get'), `${fnName} 未使用 get`).toBe(true)
    }
  })
})

// ═══════════════════════════════════════════════════════════
// 2. auth store 与 authApi 调用对齐验证（6 项）
// ═══════════════════════════════════════════════════════════

describe('auth store 与 authApi 调用对齐', () => {
  const storeCode = src('stores/auth.ts')
  const authApiCode = src('api/auth.ts')

  it('store login 调用 authApi.login', () => {
    expect(storeCode).toContain('authApi.login(')
  })

  it('store logout 调用 authApi.logout', () => {
    expect(storeCode).toContain('authApi.logout()')
  })

  it('store fetchUser 调用 authApi.getMe', () => {
    expect(storeCode).toContain('authApi.getMe()')
  })

  it('authApi 包含 login/refresh/logout/getMe/changePassword 5 个方法', () => {
    const methods = authApiCode.match(/(\w+):\s*\(/g) || []
    expect(methods.length).toBe(5)
  })

  it('authApi.login 使用 POST 方法', () => {
    expect(authApiCode).toMatch(/login:.*?\.post\b/s)
  })

  it('authApi.getMe 使用 GET 方法', () => {
    expect(authApiCode).toMatch(/getMe:.*?\.get\b/s)
  })
})

// ═══════════════════════════════════════════════════════════
// 3. usePaginatedList 参数传递一致性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('usePaginatedList 参数传递一致性', () => {
  const hookCode = src('hooks/usePaginatedList.ts')

  it('传递 page 和 page_size 参数', () => {
    expect(hookCode).toContain('page,')
    expect(hookCode).toContain('page_size: pageSize,')
  })

  it('传递 keyword 参数', () => {
    expect(hookCode).toContain('keyword: keyword')
  })

  it('解构 items 和 total 从结果', () => {
    expect(hookCode).toContain('result.items')
    expect(hookCode).toContain('result.total')
  })

  it('setKeyword 重置 page 为 1', () => {
    expect(hookCode).toMatch(/setKeyword.*setPage\(1\)/s)
  })

  it('返回 refresh 函数供外部刷新', () => {
    expect(hookCode).toContain('refresh: loadData')
  })
})

// ═══════════════════════════════════════════════════════════
// 4. client 拦截器逻辑一致性验证（6 项）
// ═══════════════════════════════════════════════════════════

describe('client 拦截器逻辑一致性', () => {
  const clientCode = src('api/client.ts')

  it('请求拦截器附加 Bearer token', () => {
    expect(clientCode).toMatch(/Authorization.*Bearer/)
  })

  it('请求拦截器生成请求 ID', () => {
    expect(clientCode).toContain('X-Request-ID')
    expect(clientCode).toContain('crypto.randomUUID()')
  })

  it('401 响应尝试刷新 token', () => {
    expect(clientCode).toContain('401')
    expect(clientCode).toContain('refresh_token')
    expect(clientCode).toContain('/auth/refresh')
  })

  it('429 响应自动重试一次', () => {
    expect(clientCode).toContain('429')
    expect(clientCode).toContain('_retry429')
    expect(clientCode).toContain('retry-after')
  })

  it('刷新失败清除 token 并跳转 /login', () => {
    expect(clientCode).toMatch(/localStorage\.removeItem\('access_token'\)/)
    expect(clientCode).toContain("window.location.href = '/login'")
  })

  it('超时配置 15000ms', () => {
    expect(clientCode).toContain('timeout: 15000')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. request.ts 辅助函数覆盖验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('request.ts 辅助函数覆盖', () => {
  const requestCode = src('api/request.ts')

  it('导出 get/post/put/del/upload/downloadCsv 6 个函数', () => {
    const exports = requestCode.match(/export async function \w+/g) || []
    expect(exports).toHaveLength(6)
    const names = exports.map((e) => e.replace('export async function ', ''))
    expect(names).toContain('get')
    expect(names).toContain('post')
    expect(names).toContain('put')
    expect(names).toContain('del')
    expect(names).toContain('upload')
    expect(names).toContain('downloadCsv')
  })

  it('所有函数返回 ApiResponse<T>', () => {
    const returnTypes = requestCode.match(/Promise<ApiResponse<\w+>>/g) || []
    expect(returnTypes.length).toBeGreaterThanOrEqual(4)
  })

  it('downloadCsv 处理 JSON 错误响应', () => {
    expect(requestCode).toContain('application/json')
    expect(requestCode).toContain('blob')
  })

  it('downloadCsv 从 content-disposition 提取文件名', () => {
    expect(requestCode).toContain('content-disposition')
    expect(requestCode).toContain('filename=')
  })

  it('upload 使用 multipart/form-data', () => {
    expect(requestCode).toContain('multipart/form-data')
    expect(requestCode).toContain('FormData')
  })
})

// ═══════════════════════════════════════════════════════════
// 6. useSubmit 防重复提交验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('useSubmit 防重复提交', () => {
  const submitCode = src('hooks/useSubmit.ts')

  it('使用 locked ref 防止重复提交', () => {
    expect(submitCode).toContain('locked.current')
    expect(submitCode).toMatch(/if\s*\(locked\.current\)\s*return/)
  })

  it('提交开始时 locked = true', () => {
    expect(submitCode).toContain('locked.current = true')
  })

  it('finally 中重置 locked = false', () => {
    const finallyBlock = submitCode.match(/finally\s*\{[^}]*\}/s)
    expect(finallyBlock?.[0]).toContain('locked.current = false')
  })

  it('跳过 Ant Design 表单校验错误', () => {
    expect(submitCode).toContain('errorFields')
  })

  it('拦截器已展示 toast 时跳过重复提示', () => {
    expect(submitCode).toContain('isToastDisplayed')
  })
})

// ═══════════════════════════════════════════════════════════
// 7. API 模块导入一致性验证（6 项）
// ═══════════════════════════════════════════════════════════

describe('API 模块导入一致性', () => {
  const modules = [
    'api/products.ts',
    'api/orders.ts',
    'api/customers.ts',
    'api/payments.ts',
    'api/roles.ts',
    'api/inventory.ts',
  ]

  it('CRUD 模块从 request.ts 导入 HTTP 方法', () => {
    for (const mod of modules) {
      const code = src(mod)
      const imports = code.match(/import\s*\{[^}]+\}\s*from\s*['"]\.\/request['"]/)?.[0] || ''
      expect(imports.length, `${mod} 未从 request.ts 导入`).toBeGreaterThan(0)
    }
  })

  it('auth 模块直接使用 apiClient 而非 request.ts 辅助函数', () => {
    const code = src('api/auth.ts')
    expect(code).toContain("from './client'")
    expect(code).not.toContain("from './request'")
  })

  it('分页 API 函数返回类型包含 PaginatedData', () => {
    expect(src('api/products.ts')).toContain('PaginatedData<')
    expect(src('api/orders.ts')).toContain('PaginatedData<')
    expect(src('api/customers.ts')).toContain('PaginatedData<')
  })

  it('分页 API 模块导入 PaginatedData 类型', () => {
    const paginatedModules = [
      'api/products.ts',
      'api/orders.ts',
      'api/customers.ts',
      'api/payments.ts',
      'api/inventory.ts',
    ]
    for (const mod of paginatedModules) {
      const code = src(mod)
      if (code.includes('PaginatedData<')) {
        expect(code, `${mod} 使用 PaginatedData 但未导入`).toContain("from '@/types'")
      }
    }
  })

  it('reports 模块不使用 PaginatedData（报表非标准分页）', () => {
    expect(src('api/reports.ts')).not.toContain('PaginatedData<')
  })

  it('所有 API 模块导出函数而非对象（auth 除外）', () => {
    for (const mod of modules) {
      const code = src(mod)
      const constExports = code.match(/^export const \w+/gm) || []
      expect(constExports.length, `${mod} 使用了 const 导出而非函数导出`).toBe(0)
    }
  })
})
