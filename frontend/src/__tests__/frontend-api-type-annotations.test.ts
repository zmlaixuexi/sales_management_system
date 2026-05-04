/**
 * 代码质量：前端 API 函数返回类型标注完整性验证测试
 * 覆盖 request 封装类型签名、API 函数泛型标注、
 * 接口导出完整性、分页函数一致性、HTTP 方法一致性
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')

function apiSrc(module: string): string {
  return readFileSync(resolve(root, 'frontend/src/api', module), 'utf-8')
}

function srcFile(relPath: string): string {
  return readFileSync(resolve(root, relPath), 'utf-8')
}

const requestCode = apiSrc('request.ts')
const clientCode = apiSrc('client.ts')
const productsCode = apiSrc('products.ts')
const ordersCode = apiSrc('orders.ts')
const customersCode = apiSrc('customers.ts')
const paymentsCode = apiSrc('payments.ts')
const authCode = apiSrc('auth.ts')
const usersCode = apiSrc('users.ts')
const rolesCode = apiSrc('roles.ts')
const inventoryCode = apiSrc('inventory.ts')
const reportsCode = apiSrc('reports.ts')
const auditLogsCode = apiSrc('auditLogs.ts')
const typesCode = srcFile('frontend/src/types/index.ts')

// ═══════════════════════════════════════════════════════════
// 1. request 封装类型签名验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('request 封装类型签名', () => {
  it('get/post/put/del/upload 均使用泛型 T', () => {
    for (const fn of ['get<T>', 'post<T>', 'put<T>', 'del<T>', 'upload<T>']) {
      expect(requestCode).toContain(fn)
    }
  })

  it('所有封装函数返回 Promise<ApiResponse<T>>', () => {
    const promiseCount = (requestCode.match(/Promise<ApiResponse<T>>/g) || []).length
    expect(promiseCount).toBeGreaterThanOrEqual(4)
  })

  it('ApiResponse 类型定义完整', () => {
    expect(typesCode).toContain('interface ApiResponse<T = unknown>')
    expect(typesCode).toContain('success: boolean')
    expect(typesCode).toContain('data: T')
    expect(typesCode).toContain('message: string')
  })

  it('PaginatedData 类型定义完整', () => {
    expect(typesCode).toContain('interface PaginatedData<T>')
    expect(typesCode).toContain('items: T[]')
    expect(typesCode).toContain('page: number')
    expect(typesCode).toContain('page_size: number')
    expect(typesCode).toContain('total: number')
  })

  it('ApiError 类型定义完整', () => {
    expect(typesCode).toContain('interface ApiError')
    expect(typesCode).toContain('success: false')
    expect(typesCode).toContain('code: string')
  })
})

// ═══════════════════════════════════════════════════════════
// 2. API 函数泛型标注验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('API 函数泛型标注', () => {
  it('fetchProducts 使用 PaginatedData<Product> 泛型', () => {
    expect(productsCode).toContain('get<PaginatedData<Product>>')
    expect(productsCode).toContain("'/products'")
  })

  it('fetchOrders 使用 PaginatedData<Order> 泛型', () => {
    expect(ordersCode).toContain('get<PaginatedData<Order>>')
    expect(ordersCode).toContain("'/sales-orders'")
  })

  it('fetchProduct/fetchOrder 使用详情类型', () => {
    expect(productsCode).toContain('get<ProductDetail>')
    expect(ordersCode).toContain('get<OrderDetail>')
  })

  it('报表函数均使用具体类型标注', () => {
    expect(reportsCode).toContain('get<SalesSummary>')
    expect(reportsCode).toContain('SalesTrendItem[]')
    expect(reportsCode).toContain('ProductRankingItem[]')
    expect(reportsCode).toContain('InventoryWarningItem[]')
  })

  it('create/update 函数使用实体类型', () => {
    expect(productsCode).toContain('post<Product>')
    expect(productsCode).toContain('put<Product>')
    expect(ordersCode).toContain('post<Order>')
    expect(ordersCode).toContain('put<')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. 接口导出完整性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('接口导出完整性', () => {
  it('products 模块导出 Product/ProductDetail/ProductFormValues', () => {
    expect(productsCode).toContain('export interface Product ')
    expect(productsCode).toContain('export interface ProductDetail')
    expect(productsCode).toContain('export interface ProductFormValues')
  })

  it('orders 模块导出 Order/OrderDetail/OrderFormValues', () => {
    expect(ordersCode).toContain('export interface Order ')
    expect(ordersCode).toContain('export interface OrderDetail')
    expect(ordersCode).toContain('export interface OrderFormValues')
  })

  it('auth 模块导出 LoginParams/TokenData/CurrentUser', () => {
    expect(authCode).toContain('interface LoginParams')
    expect(authCode).toContain('interface TokenData')
    expect(authCode).toContain('interface CurrentUser')
  })

  it('reports 模块导出所有报表类型', () => {
    expect(reportsCode).toContain('export interface SalesSummary')
    expect(reportsCode).toContain('export interface SalesTrendItem')
    expect(reportsCode).toContain('export interface ProductRankingItem')
    expect(reportsCode).toContain('export interface InventoryWarningItem')
  })

  it('业务 API 模块使用 export async function 导出函数（auth 使用对象模式）', () => {
    const modules = [productsCode, ordersCode, customersCode, paymentsCode]
    for (const code of modules) {
      expect(code).toMatch(/export async function \w+/)
    }
    // auth 使用 apiClient 对象模式
    expect(authCode).toContain('export const authApi')
  })
})

// ═══════════════════════════════════════════════════════════
// 4. 分页函数一致性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('分页函数一致性', () => {
  it('所有列表函数使用 PaginatedData 泛型', () => {
    const modules = [productsCode, ordersCode, customersCode, paymentsCode, inventoryCode, usersCode]
    for (const code of modules) {
      expect(code).toContain('PaginatedData<')
    }
  })

  it('所有列表函数接受可选分页参数', () => {
    const modules = [productsCode, ordersCode, customersCode, paymentsCode, inventoryCode]
    for (const code of modules) {
      expect(code).toMatch(/page\?/)
    }
  })

  it('业务 API 模块从 request 导入封装函数（auth 除外）', () => {
    const modules = [productsCode, ordersCode, customersCode, paymentsCode, usersCode, rolesCode, inventoryCode, reportsCode, auditLogsCode]
    for (const code of modules) {
      expect(code).toMatch(/import \{[^}]*\} from ['"]\.\/request['"]/)
    }
  })

  it('使用分页的 API 模块从 @/types 导入类型', () => {
    const modules = [productsCode, ordersCode, customersCode, paymentsCode, inventoryCode, usersCode]
    for (const code of modules) {
      expect(code).toMatch(/import.*from ['"]@\/types['"]/)
    }
  })

  it('fetchProducts 接受完整的 ProductListParams', () => {
    expect(productsCode).toContain('interface ProductListParams')
    expect(productsCode).toContain('page?')
    expect(productsCode).toContain('page_size?')
    expect(productsCode).toContain('keyword?')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. HTTP 方法一致性验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('HTTP 方法一致性', () => {
  it('create 函数使用 post 方法', () => {
    expect(productsCode).toContain('post<Product>(\'/products\'')
    expect(customersCode).toContain('post<Customer>(\'/customers\'')
    expect(ordersCode).toContain('post<Order>(\'/sales-orders\'')
  })

  it('update 函数使用 put 方法', () => {
    expect(productsCode).toContain('put<Product>')
    expect(customersCode).toContain('put<Customer>')
    expect(ordersCode).toContain('put<')
  })

  it('delete 函数使用 del 方法', () => {
    expect(productsCode).toContain('del(')
    expect(customersCode).toContain('del(')
  })

  it('动作端点使用 post 方法', () => {
    expect(ordersCode).toContain('confirmOrder')
    expect(ordersCode).toContain('post<{ id: string; status: string }>')
    expect(ordersCode).toContain('cancelOrder')
    expect(productsCode).toContain('disableProduct')
  })

  it('业务 API 模块不直接引用 apiClient（auth 除外）', () => {
    const businessModules = [productsCode, ordersCode, customersCode, paymentsCode, usersCode, rolesCode, inventoryCode, reportsCode, auditLogsCode]
    for (const code of businessModules) {
      expect(code).not.toContain('apiClient.')
    }
  })
})
