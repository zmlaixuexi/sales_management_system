/**
 * 代码质量：前端页面组件与 API 调用对应关系验证测试
 * 覆盖列表页分页函数、表单页提交函数、详情页数据加载、
 * 导出功能、API 模块导入正确性、页面组件默认导出
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')

function src(module: string): string {
  return readFileSync(resolve(root, module), 'utf-8')
}

/** 提取 import { ... } from 'source' 中指定的导入名列表 */
function extractImports(source: string, modulePattern: string | RegExp): string[] {
  const regex = typeof modulePattern === 'string'
    ? new RegExp(`import\\s*\\{([^}]+)\\}\\s*from\\s*['"]${modulePattern}['"]`, 'g')
    : new RegExp(`import\\s*\\{([^}]+)\\}\\s*from\\s*['"](${modulePattern.source})['"]`, 'g')
  const names: string[] = []
  let match: RegExpExecArray | null
  while ((match = regex.exec(source)) !== null) {
    for (const item of match[1].split(',')) {
      const name = item.trim().split(/\s+as\s+/)[0].trim()
      if (name) names.push(name)
    }
  }
  return names
}

// ═══════════════════════════════════════════════════════════
// 1. 列表页分页函数验证（7 项）
// ═══════════════════════════════════════════════════════════

describe('列表页 usePaginatedList 绑定正确 API 函数', () => {
  const listPages = [
    { file: 'pages/Products.tsx', fetchFn: 'fetchProducts' },
    { file: 'pages/Customers.tsx', fetchFn: 'fetchCustomers' },
    { file: 'pages/Orders.tsx', fetchFn: 'fetchOrders' },
    { file: 'pages/Payments.tsx', fetchFn: 'fetchPayments' },
    { file: 'pages/Inventory.tsx', fetchFn: 'fetchInventoryMovements' },
    { file: 'pages/Users.tsx', fetchFn: 'fetchUsers' },
    { file: 'pages/AuditLogs.tsx', fetchFn: 'fetchAuditLogs' },
  ]

  it.each(listPages)('$file 使用 $fetchFn 作为分页数据源', ({ file, fetchFn }) => {
    const code = src(file)
    expect(code).toContain('usePaginatedList')
    expect(code).toContain(fetchFn)
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 表单页提交函数验证（3 项）
// ═══════════════════════════════════════════════════════════

describe('表单页 useSubmit 绑定正确 API 函数', () => {
  it('ProductForm 使用 createProduct / updateProduct', () => {
    const code = src('pages/ProductForm.tsx')
    expect(code).toContain('useSubmit')
    expect(code).toContain('createProduct')
    expect(code).toContain('updateProduct')
  })

  it('CustomerForm 使用 createCustomer / updateCustomer', () => {
    const code = src('pages/CustomerForm.tsx')
    expect(code).toContain('useSubmit')
    expect(code).toContain('createCustomer')
    expect(code).toContain('updateCustomer')
  })

  it('OrderForm 使用 createOrder / updateOrder', () => {
    const code = src('pages/OrderForm.tsx')
    expect(code).toContain('useSubmit')
    expect(code).toContain('createOrder')
    expect(code).toContain('updateOrder')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 详情页数据加载验证（2 项）
// ═══════════════════════════════════════════════════════════

describe('详情页加载数据', () => {
  it('OrderDetail 使用 fetchOrder 加载详情', () => {
    const code = src('pages/OrderDetail.tsx')
    expect(code).toContain('fetchOrder')
  })

  it('CustomerDetail 使用 fetchCustomer 加载详情', () => {
    const code = src('pages/CustomerDetail.tsx')
    expect(code).toContain('fetchCustomer')
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 导出功能验证（4 项）
// ═══════════════════════════════════════════════════════════

describe('导出功能', () => {
  it('Products 导入 downloadCsv', () => {
    const code = src('pages/Products.tsx')
    expect(code).toContain('downloadCsv')
  })

  it('Customers 导入 downloadCsv', () => {
    const code = src('pages/Customers.tsx')
    expect(code).toContain('downloadCsv')
  })

  it('Orders 导入 downloadCsv', () => {
    const code = src('pages/Orders.tsx')
    expect(code).toContain('downloadCsv')
  })

  it('Payments 导入 downloadCsv', () => {
    const code = src('pages/Payments.tsx')
    expect(code).toContain('downloadCsv')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. API 模块导入正确性验证（7 项）
// ═══════════════════════════════════════════════════════════

describe('页面导入正确的 API 模块', () => {
  it('Products.tsx 仅导入自 @/api/products 和 @/api/request', () => {
    const code = src('pages/Products.tsx')
    expect(code).toMatch(/from\s+['"]@\/api\/products['"]/)
    expect(code).not.toContain("from '@/api/orders'")
    expect(code).not.toContain("from '@/api/customers'")
  })

  it('Orders.tsx 仅导入自 @/api/orders 和 @/api/request', () => {
    const code = src('pages/Orders.tsx')
    expect(code).toMatch(/from\s+['"]@\/api\/orders['"]/)
    expect(code).not.toContain("from '@/api/products'")
    expect(code).not.toContain("from '@/api/customers'")
  })

  it('Customers.tsx 仅导入自 @/api/customers 和 @/api/request', () => {
    const code = src('pages/Customers.tsx')
    expect(code).toMatch(/from\s+['"]@\/api\/customers['"]/)
    expect(code).not.toContain("from '@/api/orders'")
    expect(code).not.toContain("from '@/api/products'")
  })

  it('Payments.tsx 仅导入自 @/api/payments 和 @/api/request', () => {
    const code = src('pages/Payments.tsx')
    expect(code).toMatch(/from\s+['"]@\/api\/payments['"]/)
    expect(code).not.toContain("from '@/api/orders'")
    expect(code).not.toContain("from '@/api/products'")
  })

  it('OrderForm 跨模块导入 orders + customers + products', () => {
    const code = src('pages/OrderForm.tsx')
    expect(code).toMatch(/from\s+['"]@\/api\/orders['"]/)
    expect(code).toMatch(/from\s+['"]@\/api\/customers['"]/)
    expect(code).toMatch(/from\s+['"]@\/api\/products['"]/)
  })

  it('OrderDetail 导入 orders + payments', () => {
    const code = src('pages/OrderDetail.tsx')
    expect(code).toMatch(/from\s+['"]@\/api\/orders['"]/)
    expect(code).toMatch(/from\s+['"]@\/api\/payments['"]/)
  })

  it('ReportsCenter 导入所有报表 API 函数', () => {
    const code = src('pages/ReportsCenter.tsx')
    const imports = extractImports(code, /@\/api\/reports/)
    expect(imports).toContain('fetchSalesSummary')
    expect(imports).toContain('fetchSalesTrend')
    expect(imports).toContain('fetchProductRanking')
    expect(imports).toContain('fetchCustomerRanking')
    expect(imports).toContain('fetchSalespersonRanking')
    expect(imports).toContain('fetchInventoryWarning')
  })
})

// ═══════════════════════════════════════════════════════════
// 6. 页面组件默认导出验证（7 项）
// ═══════════════════════════════════════════════════════════

describe('页面组件默认导出', () => {
  const pages = [
    'pages/Products.tsx',
    'pages/Customers.tsx',
    'pages/Orders.tsx',
    'pages/Payments.tsx',
    'pages/Inventory.tsx',
    'pages/Dashboard.tsx',
    'pages/ReportsCenter.tsx',
  ]

  it.each(pages)('$s 有 export default', (file) => {
    const code = src(file)
    expect(code).toContain('export default')
  })
})

// ═══════════════════════════════════════════════════════════
// 7. 动作端点调用验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('动作端点调用', () => {
  it('Products 调用 deleteProduct 和 disableProduct', () => {
    const code = src('pages/Products.tsx')
    expect(code).toContain('deleteProduct')
    expect(code).toContain('disableProduct')
  })

  it('Customers 调用 deleteCustomer', () => {
    const code = src('pages/Customers.tsx')
    expect(code).toContain('deleteCustomer')
  })

  it('CustomerDetail 调用 deleteCustomer', () => {
    const code = src('pages/CustomerDetail.tsx')
    expect(code).toContain('deleteCustomer')
  })

  it('OrderDetail 调用 confirmOrder 和 cancelOrder', () => {
    const code = src('pages/OrderDetail.tsx')
    expect(code).toContain('confirmOrder')
    expect(code).toContain('cancelOrder')
  })

  it('OrderDetail 调用 createPayment 和 reversePayment', () => {
    const code = src('pages/OrderDetail.tsx')
    expect(code).toContain('createPayment')
    expect(code).toContain('reversePayment')
  })
})
