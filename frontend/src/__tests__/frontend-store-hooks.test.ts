/**
 * 代码质量：前端 Store 状态管理与 Hooks 逻辑验证测试
 * 覆盖 auth store 状态定义、auth store 业务逻辑、
 * auth API 接口定义、usePaginatedList 逻辑、useDocumentTitle 逻辑
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')

function frontendSrc(module: string): string {
  return readFileSync(resolve(root, 'frontend/src', module), 'utf-8')
}

const authStoreCode = frontendSrc('stores/auth.ts')
const authApiCode = frontendSrc('api/auth.ts')
const usePaginatedCode = frontendSrc('hooks/usePaginatedList.ts')
const useSubmitCode = frontendSrc('hooks/useSubmit.ts')
const useDocTitleCode = frontendSrc('hooks/useDocumentTitle.ts')

// ═══════════════════════════════════════════════════════════
// 1. auth store 状态定义验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('auth store 状态定义', () => {
  it('AuthState 接口定义 token/user/loading 三个状态字段', () => {
    expect(authStoreCode).toContain('interface AuthState')
    expect(authStoreCode).toContain('token: string | null')
    expect(authStoreCode).toContain('user: CurrentUser | null')
    expect(authStoreCode).toContain('loading: boolean')
  })

  it('AuthState 接口定义 login/logout/fetchUser/hasPermission 四个方法', () => {
    const interfaceMatch = authStoreCode.match(/interface AuthState \{([\s\S]*?)\}/)
    expect(interfaceMatch).not.toBeNull()
    const iface = interfaceMatch![1]
    expect(iface).toContain('login:')
    expect(iface).toContain('logout:')
    expect(iface).toContain('fetchUser:')
    expect(iface).toContain('hasPermission:')
  })

  it('使用 create<AuthState> 泛型创建 store', () => {
    expect(authStoreCode).toContain('create<AuthState>')
    expect(authStoreCode).toContain('(set, get)')
  })

  it('初始 token 从 localStorage 读取', () => {
    expect(authStoreCode).toContain("localStorage.getItem('access_token')")
  })

  it('初始 user 为 null', () => {
    expect(authStoreCode).toContain('user: null')
  })
})

// ═══════════════════════════════════════════════════════════
// 2. auth store 业务逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('auth store 业务逻辑', () => {
  it('login 调用 authApi.login 并存储 token', () => {
    expect(authStoreCode).toContain('authApi.login')
    expect(authStoreCode).toContain("localStorage.setItem('access_token'")
    expect(authStoreCode).toContain("localStorage.setItem('refresh_token'")
  })

  it('login 成功后调用 fetchUser', () => {
    expect(authStoreCode).toContain('get().fetchUser()')
  })

  it('login 设置 loading 状态并在 finally 中重置', () => {
    expect(authStoreCode).toContain('set({ loading: true })')
    expect(authStoreCode).toContain('set({ loading: false })')
    expect(authStoreCode).toContain('finally')
  })

  it('logout 清除 localStorage 和 store 状态', () => {
    expect(authStoreCode).toContain("localStorage.removeItem('access_token')")
    expect(authStoreCode).toContain("localStorage.removeItem('refresh_token')")
    expect(authStoreCode).toContain('set({ token: null, user: null })')
  })

  it('fetchUser 失败时清除 token 和 user', () => {
    expect(authStoreCode).toMatch(/catch[^{]*\{[^}]*set\(\{ token: null, user: null \}\)/s)
  })
})

// ═══════════════════════════════════════════════════════════
// 3. auth API 接口定义验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('auth API 接口定义', () => {
  it('定义 LoginParams/TokenData/CurrentUser 三个接口', () => {
    expect(authApiCode).toContain('interface LoginParams')
    expect(authApiCode).toContain('interface TokenData')
    expect(authApiCode).toContain('interface CurrentUser')
  })

  it('TokenData 包含 access_token/refresh_token/token_type', () => {
    expect(authApiCode).toContain('access_token: string')
    expect(authApiCode).toContain('refresh_token: string')
    expect(authApiCode).toContain('token_type: string')
  })

  it('CurrentUser 包含 id/username/is_superuser/permissions', () => {
    expect(authApiCode).toContain('id: string')
    expect(authApiCode).toContain('username: string')
    expect(authApiCode).toContain('is_superuser: boolean')
    expect(authApiCode).toContain('permissions: string[]')
  })

  it('authApi 对象包含 login/refresh/logout/getMe/changePassword', () => {
    expect(authApiCode).toContain('login:')
    expect(authApiCode).toContain('refresh:')
    expect(authApiCode).toContain('logout:')
    expect(authApiCode).toContain('getMe:')
    expect(authApiCode).toContain('changePassword:')
  })

  it('login 调用 POST /auth/login', () => {
    expect(authApiCode).toContain("post<")
    expect(authApiCode).toContain("/auth/login")
  })
})

// ═══════════════════════════════════════════════════════════
// 4. usePaginatedList 逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('usePaginatedList 逻辑', () => {
  it('返回 data/total/loading/error/page/pageSize/keyword 状态', () => {
    expect(usePaginatedCode).toContain('return {')
    expect(usePaginatedCode).toContain('data')
    expect(usePaginatedCode).toContain('total')
    expect(usePaginatedCode).toContain('loading')
    expect(usePaginatedCode).toContain('error')
    expect(usePaginatedCode).toContain('page')
    expect(usePaginatedCode).toContain('pageSize')
    expect(usePaginatedCode).toContain('keyword')
  })

  it('使用 fetchFnRef 避免 fetchFn 闭包过期', () => {
    expect(usePaginatedCode).toContain('fetchFnRef')
    expect(usePaginatedCode).toContain('useRef(fetchFn)')
    expect(usePaginatedCode).toContain('useEffect')
    expect(usePaginatedCode).toContain('fetchFnRef.current = fetchFn')
  })

  it('返回 setPage/setKeyword/onPageChange/refresh 方法', () => {
    expect(usePaginatedCode).toContain('setPage')
    expect(usePaginatedCode).toContain('setKeyword')
    expect(usePaginatedCode).toContain('onPageChange')
    expect(usePaginatedCode).toContain('refresh')
  })

  it('setKeyword 同时重置 page 为 1', () => {
    expect(usePaginatedCode).toMatch(/setKeyword.*setKeyword:.*setPage\(1\)/s)
  })

  it('错误处理检查 isToastDisplayed 避免重复提示', () => {
    expect(usePaginatedCode).toContain('isToastDisplayed')
  })
})

// ═══════════════════════════════════════════════════════════
// 5. useDocumentTitle 逻辑验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('useDocumentTitle 逻辑', () => {
  it('默认导出函数', () => {
    expect(useDocTitleCode).toContain('export default function useDocumentTitle')
  })

  it('接受可选 title 参数', () => {
    expect(useDocTitleCode).toContain('title?: string')
  })

  it('使用 useRef 保存之前的标题', () => {
    expect(useDocTitleCode).toContain('useRef')
    expect(useDocTitleCode).toContain('prevTitleRef')
  })

  it('组件卸载时恢复之前的标题', () => {
    expect(useDocTitleCode).toContain('return () =>')
    expect(useDocTitleCode).toContain('document.title = prev')
  })

  it('标题格式为 "页面标题 - 销售管理系统"', () => {
    expect(useDocTitleCode).toContain('销售管理系统')
    expect(useDocTitleCode).toMatch(/\$\{title\}.*\$\{APP_TITLE\}/)
  })
})
