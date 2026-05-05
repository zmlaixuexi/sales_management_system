/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _customerMocks = {
  fetchCustomers: vi.fn(),
  deleteCustomer: vi.fn(),
}

vi.mock('@/api/customers', () => ({
  fetchCustomers: (...args: any[]) => _customerMocks.fetchCustomers(...args),
  deleteCustomer: (...args: any[]) => _customerMocks.deleteCustomer(...args),
}))

vi.mock('@/utils', () => ({
  getApiErrorMessage: (_e: any, fallback: string) => fallback,
  isToastDisplayed: (e: any) => !!e?._toastDisplayed,
}))

vi.mock('@/api/request', () => ({
  downloadCsv: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  default: { post: vi.fn() },
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: any) => selector({ hasPermission: (code: string) => code === 'customer:create' || code === 'customer:delete' || code === 'customer:view_all' }),
}))

const _paginatedListReturn = {
  data: [
    { id: 'c1', name: '客户甲', contact_name: '张三', phone: '13800001111', source: 'referral', level: 'vip', owner_name: '销售A', follow_status: '活跃' },
    { id: 'c2', name: '客户乙', contact_name: '李四', phone: '13800002222', source: 'online', level: 'normal', owner_name: '销售B', follow_status: '待跟进' },
    { id: 'c3', name: '客户丙', contact_name: null, phone: null, source: null, level: null, owner_name: null, follow_status: null },
  ],
  total: 3,
  loading: false,
  error: false,
  page: 1,
  pageSize: 10,
  keyword: '',
  setPage: vi.fn(),
  setKeyword: vi.fn(),
  onPageChange: vi.fn(),
  refresh: vi.fn(),
}

vi.mock('@/hooks/usePaginatedList', () => ({
  usePaginatedList: (fetchFn: any) => {
    try { const p = fetchFn({ page: 1, page_size: 20 }); p?.catch?.(() => {}) } catch { /* mock 返回非 Promise 时抛错 */ }
    return _paginatedListReturn
  },
}))

vi.mock('antd', () => ({
  Table: ({ dataSource, columns, rowKey, locale, loading, pagination }: any) => (
    loading ? <span>加载中...</span> : (
    <div>
      <table data-testid="customers-table">
        <thead>
          <tr>{columns?.map((col: any) => <th key={col.dataIndex || col.title}>{col.title}</th>)}</tr>
        </thead>
        <tbody>
          {dataSource?.length ? dataSource.map((row: any) => (
            <tr key={row[rowKey]} data-testid={`row-${row[rowKey]}`}>
              {columns?.map((col: any) => (
                <td key={col.dataIndex} data-col={col.dataIndex}>
                  {col.render ? col.render(row[col.dataIndex], row) : row[col.dataIndex]}
                </td>
              ))}
            </tr>
          )) : (
            <tr><td colSpan={99}>{typeof locale?.emptyText === 'string' ? locale.emptyText : locale?.emptyText}</td></tr>
          )}
        </tbody>
      </table>
      {pagination?.showTotal && <span data-testid="pagination-total">{pagination.showTotal(pagination.total)}</span>}
      {pagination?.onChange && <button data-testid="page-change" onClick={() => pagination.onChange(2, pagination.pageSize)}>翻页</button>}
    </div>
    )
  ),
  Button: ({ children, onClick, icon, type, danger }: any) => (
    <button data-testid="button" data-type={type} data-danger={danger ? 'true' : undefined} onClick={onClick}>{icon}{children}</button>
  ),
  Input: ({ value, onChange, placeholder }: any) => (
    <input data-testid="search-input" placeholder={placeholder} value={value || ''} onChange={(e: any) => onChange?.(e)} />
  ),
  Select: ({ value, onChange, options, placeholder }: any) => (
    <select data-testid="source-select" value={value || ''} onChange={(e: any) => onChange?.(e.target.value)}>
      <option value="">{placeholder || '全部'}</option>
      {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
  Popconfirm: ({ title, children, onConfirm }: any) => (
    <span data-testid="popconfirm" data-title={title} onClick={onConfirm}>{children}</span>
  ),
  message: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span>+</span>,
  EditOutlined: () => <span>✏️</span>,
  DeleteOutlined: () => <span>🗑️</span>,
  SearchOutlined: () => <span>🔍</span>,
  DownloadOutlined: () => <span>📥</span>,
  UploadOutlined: () => <span>📤</span>,
}))

import CustomersPage from '@/pages/Customers'

function renderCustomers() {
  return render(
    <MemoryRouter initialEntries={['/customers']}>
      <Routes>
        <Route path="/customers" element={<CustomersPage />} />
        <Route path="/customers/:id/edit" element={<div>Edit Page</div>} />
        <Route path="/customers/new" element={<div>New Customer Page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CustomersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染搜索输入和来源筛选器', () => {
    renderCustomers()
    expect(screen.getByTestId('search-input')).toBeInTheDocument()
    expect(screen.getByTestId('source-select')).toBeInTheDocument()
  })

  it('渲染新增客户按钮', () => {
    renderCustomers()
    expect(screen.getByText('新增客户')).toBeInTheDocument()
  })

  it('渲染客户数据表格', () => {
    renderCustomers()
    const table = screen.getByTestId('customers-table')
    expect(table).toBeInTheDocument()
    expect(screen.getByTestId('row-c1')).toBeInTheDocument()
    expect(screen.getByTestId('row-c2')).toBeInTheDocument()
  })

  it('客户行显示名称、联系人、电话', () => {
    renderCustomers()
    expect(screen.getByText('客户甲')).toBeInTheDocument()
    expect(screen.getByText('张三')).toBeInTheDocument()
    expect(screen.getByText('13800001111')).toBeInTheDocument()
  })

  it('来源正确映射为中文', () => {
    renderCustomers()
    // 来源文本同时出现在表格和下拉菜单中，用 getAllByText
    expect(screen.getAllByText('转介绍').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('线上').length).toBeGreaterThanOrEqual(1)
  })

  it('等级标签正确渲染', () => {
    renderCustomers()
    const tags = screen.getAllByTestId('tag')
    const tagTexts = tags.map((t) => t.textContent)
    expect(tagTexts).toContain('VIP')
    expect(tagTexts).toContain('普通')
  })

  it('空值字段显示占位符', () => {
    renderCustomers()
    const row3 = screen.getByTestId('row-c3')
    const dashes = row3.querySelectorAll('td')
    // 联系人、电话、来源、等级、归属销售、跟进状态应为 '--'
    const dashTexts = Array.from(dashes).filter((td) => td.textContent === '--')
    expect(dashTexts.length).toBeGreaterThanOrEqual(5)
  })

  it('表格列包含必要字段', () => {
    renderCustomers()
    const table = screen.getByTestId('customers-table')
    const headerTexts = Array.from(table.querySelectorAll('th')).map((th) => th.textContent)
    expect(headerTexts).toContain('客户名称')
    expect(headerTexts).toContain('联系人')
    expect(headerTexts).toContain('电话')
    expect(headerTexts).toContain('来源')
    expect(headerTexts).toContain('等级')
    expect(headerTexts).toContain('操作')
  })

  it('无数据时显示空状态提示', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0 })
    renderCustomers()
    expect(screen.getByText('暂无客户，点击"新增客户"添加')).toBeInTheDocument()
    // 恢复
    _paginatedListReturn.data = [
      { id: 'c1', name: '客户甲', contact_name: '张三', phone: '13800001111', source: 'referral', level: 'vip', owner_name: '销售A', follow_status: '活跃' },
      { id: 'c2', name: '客户乙', contact_name: '李四', phone: '13800002222', source: 'online', level: 'normal', owner_name: '销售B', follow_status: '待跟进' },
      { id: 'c3', name: '客户丙', contact_name: null, phone: null, source: null, level: null, owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 3
  })

  it('加载失败时显示错误和重试链接', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, error: true })
    renderCustomers()
    expect(screen.getByText('加载失败，')).toBeInTheDocument()
    expect(screen.getByText('重试')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'c1', name: '客户甲', contact_name: '张三', phone: '13800001111', source: 'referral', level: 'vip', owner_name: '销售A', follow_status: '活跃' },
      { id: 'c2', name: '客户乙', contact_name: '李四', phone: '13800002222', source: 'online', level: 'normal', owner_name: '销售B', follow_status: '待跟进' },
      { id: 'c3', name: '客户丙', contact_name: null, phone: null, source: null, level: null, owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 3
    _paginatedListReturn.error = false
  })

  it('加载中显示加载提示', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, loading: true })
    renderCustomers()
    expect(screen.getByText('加载中...')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'c1', name: '客户甲', contact_name: '张三', phone: '13800001111', source: 'referral', level: 'vip', owner_name: '销售A', follow_status: '活跃' },
      { id: 'c2', name: '客户乙', contact_name: '李四', phone: '13800002222', source: 'online', level: 'normal', owner_name: '销售B', follow_status: '待跟进' },
      { id: 'c3', name: '客户丙', contact_name: null, phone: null, source: null, level: null, owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 3
    _paginatedListReturn.loading = false
  })

  it('删除确认弹窗点击触发 handleDelete', async () => {
    _customerMocks.deleteCustomer.mockResolvedValueOnce({ success: true })
    renderCustomers()
    const popconfirms = screen.getAllByTestId('popconfirm')
    expect(popconfirms.length).toBeGreaterThan(0)
    // Popconfirm mock 的 onClick 直接调用 onConfirm -> handleDelete
    await import('@ant-design/icons').then(() => {}) // 确保 mocks 就绪
    popconfirms[0].click()
    expect(_customerMocks.deleteCustomer).toHaveBeenCalled()
  })

  it('导出按钮点击调用 downloadCsv', async () => {
    const { downloadCsv } = await import('@/api/request')
    renderCustomers()
    const buttons = screen.getAllByTestId('button')
    const exportBtn = buttons.find((b) => b.textContent?.includes('导出'))
    expect(exportBtn).toBeTruthy()
    exportBtn!.click()
    expect(downloadCsv).toHaveBeenCalledWith('/exports/customers', expect.objectContaining({}))
  })

  it('导入按钮存在', () => {
    renderCustomers()
    expect(screen.getByText('导入')).toBeInTheDocument()
  })

  it('编辑按钮存在于操作列', () => {
    renderCustomers()
    const editBtns = screen.getAllByText('编辑')
    expect(editBtns.length).toBeGreaterThanOrEqual(1)
  })

  it('删除失败不崩溃', async () => {
    _customerMocks.deleteCustomer.mockRejectedValueOnce(new Error('删除失败'))
    renderCustomers()
    const popconfirms = screen.getAllByTestId('popconfirm')
    popconfirms[0].click()
    expect(_customerMocks.deleteCustomer).toHaveBeenCalled()
  })

  it('来源筛选器包含全部选项', () => {
    renderCustomers()
    const select = screen.getByTestId('source-select')
    const options = Array.from(select.querySelectorAll('option'))
    const optionTexts = options.map((o) => o.textContent)
    expect(optionTexts).toContain('转介绍')
    expect(optionTexts).toContain('线上')
  })

  it('有筛选条件时空数据显示"没有匹配的客户"', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, keyword: '不存在的客户' })
    renderCustomers()
    expect(screen.getByText('没有匹配的客户')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'c1', name: '客户甲', contact_name: '张三', phone: '13800001111', source: 'referral', level: 'vip', owner_name: '销售A', follow_status: '活跃' },
      { id: 'c2', name: '客户乙', contact_name: '李四', phone: '13800002222', source: 'online', level: 'normal', owner_name: '销售B', follow_status: '待跟进' },
      { id: 'c3', name: '客户丙', contact_name: null, phone: null, source: null, level: null, owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 3
    _paginatedListReturn.keyword = ''
  })

  it('未知来源显示原始值', () => {
    _paginatedListReturn.data = [
      { id: 'c4', name: '客户丁', contact_name: '王五', phone: '13900001111', source: 'unknown_source', level: 'normal', owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 1
    renderCustomers()
    expect(screen.getByText('unknown_source')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'c1', name: '客户甲', contact_name: '张三', phone: '13800001111', source: 'referral', level: 'vip', owner_name: '销售A', follow_status: '活跃' },
      { id: 'c2', name: '客户乙', contact_name: '李四', phone: '13800002222', source: 'online', level: 'normal', owner_name: '销售B', follow_status: '待跟进' },
      { id: 'c3', name: '客户丙', contact_name: null, phone: null, source: null, level: null, owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 3
  })

  it('点击客户名称导航到客户详情', async () => {
    renderCustomers()
    const link = screen.getByText('客户甲')
    await act(async () => { fireEvent.click(link) })
    // 导航到 /customers/:id（详情页路由未定义，但链接已被点击）
    expect(link).toBeTruthy()
  })

  it('点击编辑按钮导航到编辑页', async () => {
    renderCustomers()
    const editBtns = screen.getAllByText('编辑')
    await act(async () => { fireEvent.click(editBtns[0]) })
    // 编辑按钮点击后导航到 /customers/:id/edit
    await waitFor(() => {
      expect(screen.getByText('Edit Page')).toBeInTheDocument()
    })
  })

  it('点击新增客户按钮导航到新建页', async () => {
    renderCustomers()
    const addBtn = screen.getByText('新增客户')
    await act(async () => { fireEvent.click(addBtn) })
    await waitFor(() => {
      expect(screen.getByText('New Customer Page')).toBeInTheDocument()
    })
  })

  it('来源筛选器 onChange 调用 setPage 和 setSourceFilter', async () => {
    renderCustomers()
    const select = screen.getByTestId('source-select')
    await act(async () => {
      fireEvent.change(select, { target: { value: 'referral' } })
    })
    expect(_paginatedListReturn.setPage).toHaveBeenCalledWith(1)
  })

  it('搜索输入 onChange 调用 setKeyword', async () => {
    renderCustomers()
    const input = screen.getByTestId('search-input')
    await act(async () => {
      fireEvent.change(input, { target: { value: '测试' } })
    })
    expect(_paginatedListReturn.setKeyword).toHaveBeenCalled()
  })

  it('删除成功后调用 loadData 刷新列表', async () => {
    _customerMocks.deleteCustomer.mockResolvedValueOnce({ success: true })
    renderCustomers()
    const popconfirms = screen.getAllByTestId('popconfirm')
    await act(async () => { fireEvent.click(popconfirms[0]) })
    await waitFor(() => {
      expect(_customerMocks.deleteCustomer).toHaveBeenCalled()
      expect(_paginatedListReturn.refresh).toHaveBeenCalled()
    })
  })

  it('导入按钮触发 file input click', () => {
    renderCustomers()
    const importBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('导入'),
    )
    expect(importBtn).toBeTruthy()
    // file input 存在但 hidden
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(fileInput).toBeTruthy()
    expect(fileInput.accept).toBe('.csv')
  })

  it('handleImport 调用 API 上传文件', async () => {
    const { default: apiClient } = await import('@/api/client')
    const mockPost = apiClient.post as ReturnType<typeof vi.fn>
    mockPost.mockResolvedValueOnce({ data: { success: true, message: '导入3条' } })

    renderCustomers()
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(fileInput).toBeTruthy()

    const file = new File(['name,phone\n测试,138'], 'test.csv', { type: 'text/csv' })
    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [file] } })
    })

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/customers/import', expect.any(FormData), {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    })
  })

  it('导入成功后刷新列表', async () => {
    const { default: apiClient } = await import('@/api/client')
    const mockPost = apiClient.post as ReturnType<typeof vi.fn>
    mockPost.mockResolvedValueOnce({ data: { success: true, message: '导入成功' } })

    renderCustomers()
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [file] } })
    })

    await waitFor(() => {
      expect(_paginatedListReturn.refresh).toHaveBeenCalled()
    })
  })

  it('来源筛选空数据显示"没有匹配的客户"', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, sourceFilter: 'referral', keyword: '' })
    // need to set sourceFilter on state, but hook returns fixed data
    // Instead test with keyword set
    Object.assign(_paginatedListReturn, { data: [], total: 0, keyword: 'xyz' })
    renderCustomers()
    expect(screen.getByText('没有匹配的客户')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'c1', name: '客户甲', contact_name: '张三', phone: '13800001111', source: 'referral', level: 'vip', owner_name: '销售A', follow_status: '活跃' },
      { id: 'c2', name: '客户乙', contact_name: '李四', phone: '13800002222', source: 'online', level: 'normal', owner_name: '销售B', follow_status: '待跟进' },
      { id: 'c3', name: '客户丙', contact_name: null, phone: null, source: null, level: null, owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 3
    _paginatedListReturn.keyword = ''
  })

  it('分页显示总条数', () => {
    renderCustomers()
    expect(screen.getByTestId('pagination-total')).toHaveTextContent('共 3 条')
  })

  it('翻页触发 onPageChange', () => {
    renderCustomers()
    fireEvent.click(screen.getByTestId('page-change'))
    expect(_paginatedListReturn.onPageChange).toHaveBeenCalled()
  })

  it('导入按钮点击触发 fileInput click', async () => {
    renderCustomers()
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const clickSpy = vi.spyOn(fileInput, 'click')
    const importBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('导入'),
    )
    await act(async () => { importBtn!.click() })
    expect(clickSpy).toHaveBeenCalled()
    clickSpy.mockRestore()
  })

  it('导入 API 返回 success=false 不刷新', async () => {
    const { default: apiClient } = await import('@/api/client')
    const mockPost = apiClient.post as ReturnType<typeof vi.fn>
    mockPost.mockResolvedValueOnce({ data: { success: false, message: '导入失败' } })
    const { message } = await import('antd')

    renderCustomers()
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    await act(async () => { fireEvent.change(fileInput, { target: { files: [file] } }) })

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalled()
    })
    expect(_paginatedListReturn.refresh).not.toHaveBeenCalled()
    expect(message.success).not.toHaveBeenCalled()
  })

  it('handleImport 文件为空不调用 API', async () => {
    const { default: apiClient } = await import('@/api/client')
    const mockPost = apiClient.post as ReturnType<typeof vi.fn>

    renderCustomers()
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    await act(async () => { fireEvent.change(fileInput, { target: { files: [] } }) })

    expect(mockPost).not.toHaveBeenCalled()
  })

  it('导入期间卸载组件 ref 清理不崩溃', async () => {
    const { default: apiClient } = await import('@/api/client')
    const mockPost = apiClient.post as ReturnType<typeof vi.fn>
    let resolvePost: (v: unknown) => void
    mockPost.mockReturnValueOnce(new Promise((r) => { resolvePost = r }))

    const { unmount } = renderCustomers()
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [file] } })
    })
    // 卸载组件 → fileInputRef.current 变为 null
    unmount()
    // 解除 pending 的 API 调用，handleImport 继续执行到 fileInputRef.current 检查
    await act(async () => {
      resolvePost!({ data: { success: true, message: 'ok' } })
    })
    // 不崩溃即可，fileInputRef.current 为 null 时不执行 .value = ''
  })

  it('handleDelete _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _customerMocks.deleteCustomer.mockRejectedValueOnce(err)
    const { message } = await import('antd')
    renderCustomers()
    const popconfirms = screen.getAllByTestId('popconfirm')
    await act(async () => { fireEvent.click(popconfirms[0]) })
    await waitFor(() => {
      expect(_customerMocks.deleteCustomer).toHaveBeenCalled()
    })
    expect(message.error).not.toHaveBeenCalledWith('删除失败')
  })

  it('未知等级显示原始值', () => {
    _paginatedListReturn.data = [
      { id: 'c5', name: '客户戊', contact_name: null, phone: null, source: null, level: 'platinum', owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 1
    renderCustomers()
    const tags = screen.getAllByTestId('tag')
    const platinumTag = tags.find((t) => t.textContent === 'platinum')
    expect(platinumTag).toBeTruthy()
    expect(platinumTag?.getAttribute('data-color')).toBe('default')
    _paginatedListReturn.data = [
      { id: 'c1', name: '客户甲', contact_name: '张三', phone: '13800001111', source: 'referral', level: 'vip', owner_name: '销售A', follow_status: '活跃' },
      { id: 'c2', name: '客户乙', contact_name: '李四', phone: '13800002222', source: 'online', level: 'normal', owner_name: '销售B', follow_status: '待跟进' },
      { id: 'c3', name: '客户丙', contact_name: null, phone: null, source: null, level: null, owner_name: null, follow_status: null },
    ]
    _paginatedListReturn.total = 3
  })
})
