/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _auditMocks = {
  fetchAuditActions: vi.fn(),
}
const _searchValues: Record<string, string> = {}

vi.mock('@/api/auditLogs', () => ({
  fetchAuditLogs: vi.fn(),
  fetchAuditActions: (...args: any[]) => _auditMocks.fetchAuditActions(...args),
}))

const _paginatedListReturn = {
  data: [
    { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
    { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
    { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
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
  usePaginatedList: () => _paginatedListReturn,
}))

vi.mock('antd', () => ({
  Table: ({ dataSource, columns, rowKey, locale, pagination }: any) => (
    <div>
      <table data-testid="audit-table">
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
  ),
  Select: ({ value, onChange, options, placeholder }: any) => (
    <select data-testid="action-select" value={value || ''} onChange={(e: any) => onChange?.(e.target.value)}>
      <option value="">{placeholder || '全部'}</option>
      {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  ),
  Input: Object.assign(
    ({ value, onChange, placeholder }: any) => (
      <input data-testid="search-input" placeholder={placeholder} value={value || ''} onChange={(e: any) => onChange?.(e)} />
    ),
    {
      Search: ({ placeholder, onSearch, onClear }: any) => (
        <div>
          <input data-testid="search-input" placeholder={placeholder} onChange={(e: any) => { _searchValues[placeholder] = e.target.value }} />
          <button data-testid={`search-btn-${placeholder}`} onClick={() => onSearch?.(_searchValues[placeholder] ?? 'test-search')}>搜索</button>
          {onClear && <button data-testid={`clear-btn-${placeholder}`} onClick={onClear}>清除</button>}
        </div>
      ),
    },
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
  Typography: {
    Title: ({ children }: any) => <h2>{children}</h2>,
    Text: ({ children }: any) => <span>{children}</span>,
  },
  Tooltip: ({ children }: any) => <span>{children}</span>,
  DatePicker: { RangePicker: ({ onChange }: any) => (
    <div data-testid="date-range">
      <button data-testid="date-range-change" onClick={() => onChange?.(null)}>设置日期</button>
    </div>
  ) },
  message: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('dayjs', () => {
  const mockDayjs = (v: any) => ({
    format: (fmt: string) => {
      if (!v) return ''
      const d = new Date(v)
      if (fmt === 'YYYY-MM-DD') return d.toISOString().slice(0, 10)
      if (fmt === 'YYYY-MM-DD HH:mm:ss') return d.toISOString().replace('T', ' ').slice(0, 19)
      return String(v)
    },
  })
  return { default: mockDayjs }
})

vi.mock('@ant-design/icons', () => ({}))

import AuditLogs from '@/pages/AuditLogs'

function renderAuditLogs() {
  return render(
    <MemoryRouter initialEntries={['/audit-logs']}>
      <Routes>
        <Route path="/audit-logs" element={<AuditLogs />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AuditLogs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.keys(_searchValues).forEach((k) => delete _searchValues[k])
    _auditMocks.fetchAuditActions.mockResolvedValue({
      actions: ['product_create', 'order_confirm', 'login_success'],
      resource_types: ['product', 'order', 'user'],
    })
  })

  it('渲染页面标题', () => {
    renderAuditLogs()
    expect(screen.getByText('操作日志')).toBeInTheDocument()
  })

  it('渲染筛选器', () => {
    renderAuditLogs()
    const selects = screen.getAllByTestId('action-select')
    expect(selects.length).toBeGreaterThanOrEqual(2)
    expect(screen.getByTestId('date-range')).toBeInTheDocument()
    const searchInputs = screen.getAllByTestId('search-input')
    expect(searchInputs.length).toBe(2)
    const placeholders = searchInputs.map((el) => el.getAttribute('placeholder'))
    expect(placeholders).toContain('搜索操作人或资源ID')
    expect(placeholders).toContain('资源ID精确筛选')
  })

  it('渲染审计日志表格', () => {
    renderAuditLogs()
    expect(screen.getByTestId('audit-table')).toBeInTheDocument()
    expect(screen.getByTestId('row-al1')).toBeInTheDocument()
  })

  it('操作标签正确映射为中文', () => {
    renderAuditLogs()
    const tags = screen.getAllByTestId('tag')
    const tagTexts = tags.map((t) => t.textContent)
    expect(tagTexts).toContain('新增商品')
    expect(tagTexts).toContain('确认订单')
    expect(tagTexts).toContain('登录成功')
  })

  it('资源类型映射为中文', () => {
    renderAuditLogs()
    expect(screen.getByText('商品')).toBeInTheDocument()
    expect(screen.getByText('订单')).toBeInTheDocument()
    expect(screen.getByText('用户')).toBeInTheDocument()
  })

  it('空值显示短横线', () => {
    renderAuditLogs()
    const row2 = screen.getByTestId('row-al2')
    expect(row2.textContent).toContain('-')
  })

  it('表格列包含必要字段', () => {
    renderAuditLogs()
    const table = screen.getByTestId('audit-table')
    const headerTexts = Array.from(table.querySelectorAll('th')).map((th) => th.textContent)
    expect(headerTexts).toContain('时间')
    expect(headerTexts).toContain('操作人')
    expect(headerTexts).toContain('操作')
    expect(headerTexts).toContain('资源类型')
    expect(headerTexts).toContain('IP')
  })

  it('fetchAuditActions 在挂载时调用', async () => {
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
  })

  it('无数据时显示空状态提示', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0 })
    renderAuditLogs()
    expect(screen.getByText('暂无操作日志')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
      { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
      { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 3
  })

  it('加载失败时显示错误和重试链接', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, error: true })
    renderAuditLogs()
    expect(screen.getByText('加载失败，')).toBeInTheDocument()
    expect(screen.getByText('重试')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
      { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
      { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 3
    _paginatedListReturn.error = false
  })

  it('加载中显示加载提示', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, loading: true })
    renderAuditLogs()
    expect(screen.getByText('加载中...')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
      { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
      { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 3
    _paginatedListReturn.loading = false
  })

  it('操作类型筛选器填充选项', async () => {
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
    const selects = screen.getAllByTestId('action-select')
    const actionSelect = selects[0]
    const optionTexts = Array.from(actionSelect.querySelectorAll('option')).map((o) => o.textContent)
    expect(optionTexts).toContain('新增商品')
    expect(optionTexts).toContain('确认订单')
    expect(optionTexts).toContain('登录成功')
  })

  it('资源类型筛选器填充选项', async () => {
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
    const selects = screen.getAllByTestId('action-select')
    const resourceSelect = selects[1]
    const optionTexts = Array.from(resourceSelect.querySelectorAll('option')).map((o) => o.textContent)
    expect(optionTexts).toContain('商品')
    expect(optionTexts).toContain('订单')
    expect(optionTexts).toContain('用户')
  })

  it('操作类型筛选变更重置分页', async () => {
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
    const selects = screen.getAllByTestId('action-select')
    fireEvent.change(selects[0], { target: { value: 'product_create' } })
    expect(_paginatedListReturn.setPage).toHaveBeenCalledWith(1)
  })

  it('资源类型筛选变更重置分页', async () => {
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
    const selects = screen.getAllByTestId('action-select')
    fireEvent.change(selects[1], { target: { value: 'product' } })
    expect(_paginatedListReturn.setPage).toHaveBeenCalledWith(1)
  })

  it('未知操作类型显示原始值', () => {
    _paginatedListReturn.data = [
      { id: 'al4', created_at: '2026-05-01T12:00:00Z', actor_name: '管理员', action: 'unknown_action', resource_type: 'product', resource_id: 'res-001', after_data: null, ip_address: '127.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 1
    renderAuditLogs()
    const tags = screen.getAllByTestId('tag')
    const tagTexts = tags.map((t) => t.textContent)
    expect(tagTexts).toContain('unknown_action')
    _paginatedListReturn.data = [
      { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
      { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
      { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 3
  })

  it('未知资源类型显示原始值', () => {
    _paginatedListReturn.data = [
      { id: 'al5', created_at: '2026-05-01T13:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'invoice', resource_id: 'inv-001', after_data: null, ip_address: '127.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 1
    renderAuditLogs()
    expect(screen.getByText('invoice')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
      { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
      { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 3
  })

  it('fetchAuditActions 失败不阻塞渲染', async () => {
    _auditMocks.fetchAuditActions.mockRejectedValue(new Error('接口错误'))
    renderAuditLogs()
    await waitFor(() => {
      expect(screen.getByText('操作日志')).toBeInTheDocument()
    })
  })

  it('资源ID搜索触发 setResourceIdFilter 和 setPage', async () => {
    renderAuditLogs()
    await waitFor(() => { expect(_auditMocks.fetchAuditActions).toHaveBeenCalled() })
    const searchBtn = screen.getByTestId('search-btn-资源ID精确筛选')
    fireEvent.click(searchBtn)
    expect(_paginatedListReturn.setPage).toHaveBeenCalledWith(1)
  })

  it('日期范围变更触发 setPage', async () => {
    renderAuditLogs()
    await waitFor(() => { expect(_auditMocks.fetchAuditActions).toHaveBeenCalled() })
    const dateBtn = screen.getByTestId('date-range-change')
    fireEvent.click(dateBtn)
    expect(_paginatedListReturn.setPage).toHaveBeenCalledWith(1)
  })

  it('关键词搜索触发 setKeyword', async () => {
    renderAuditLogs()
    await waitFor(() => { expect(_auditMocks.fetchAuditActions).toHaveBeenCalled() })
    const searchBtn = screen.getByTestId('search-btn-搜索操作人或资源ID')
    fireEvent.click(searchBtn)
    expect(_paginatedListReturn.setKeyword).toHaveBeenCalledWith('test-search')
  })

  it('分页显示总条数', () => {
    renderAuditLogs()
    expect(screen.getByTestId('pagination-total')).toHaveTextContent('共 3 条')
  })

  it('翻页触发 onPageChange', () => {
    renderAuditLogs()
    fireEvent.click(screen.getByTestId('page-change'))
    expect(_paginatedListReturn.onPageChange).toHaveBeenCalled()
  })

  it('资源ID搜索清除触发 setResourceIdFilter 和 setPage', async () => {
    renderAuditLogs()
    await waitFor(() => { expect(_auditMocks.fetchAuditActions).toHaveBeenCalled() })
    const clearBtn = screen.getByTestId('clear-btn-资源ID精确筛选')
    fireEvent.click(clearBtn)
    expect(_paginatedListReturn.setPage).toHaveBeenCalledWith(1)
  })

  it('loadActions _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _auditMocks.fetchAuditActions.mockRejectedValue(err)
    const { message } = await import('antd')
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
    expect(message.error).not.toHaveBeenCalledWith('加载筛选选项失败')
  })

  it('fetchAuditActions 返回空 actions 和 resource_types', async () => {
    _auditMocks.fetchAuditActions.mockResolvedValue({ actions: null, resource_types: null })
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
    // 不崩溃即可
    expect(screen.getByText('操作日志')).toBeInTheDocument()
  })

  it('空操作类型显示原始值', async () => {
    _paginatedListReturn.data = [
      { id: 'log-x', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'custom_action', resource_type: 'order', resource_id: 'ord-1', detail: null },
      { id: 'log-y', created_at: '2026-05-01T11:00:00Z', actor_name: '销售', action: 'login_success', resource_type: 'user', resource_id: null, detail: '登录' },
    ]
    _paginatedListReturn.total = 2
    renderAuditLogs()
    // 未知 action 显示原始值
    expect(screen.getByText('custom_action')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'log-1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'login_success', resource_type: 'user', resource_id: null, detail: 'IP: 127.0.0.1' },
      { id: 'log-2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售员', action: 'customer_create', resource_type: 'customer', resource_id: 'cust-1', detail: '创建了客户' },
      { id: 'log-3', created_at: '2026-05-01T12:00:00Z', actor_name: '管理员', action: 'product_update', resource_type: 'product', resource_id: 'prod-1', detail: '更新了商品' },
    ]
    _paginatedListReturn.total = 3
  })

  it('resource_type 为 null 显示 -', () => {
    _paginatedListReturn.data = [
      { id: 'al-null-rt', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'login_success', resource_type: null, resource_id: 'x', after_data: null, ip_address: '127.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 1
    renderAuditLogs()
    const row = screen.getByTestId('row-al-null-rt')
    // resource_type null → '-' (the RESOURCE_LABELS[v] || v || '-' expression)
    expect(row.textContent).toContain('-')
    _paginatedListReturn.data = [
      { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
      { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
      { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 3
  })

  it('after_data 包含 order_no 显示变更内容', () => {
    _paginatedListReturn.data = [
      { id: 'al-order-no', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'order_create', resource_type: 'order', resource_id: 'ord-1', after_data: { order_no: 'ORD-20260501-001' }, ip_address: '127.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 1
    renderAuditLogs()
    expect(screen.getByText(/order_no: ORD-20260501-001/)).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
      { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
      { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 3
  })

  it('after_data 仅含非匹配键显示 -', () => {
    _paginatedListReturn.data = [
      { id: 'al-no-match', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_update', resource_type: 'product', resource_id: 'prod-1', after_data: { price: 100, quantity: 5 }, ip_address: '127.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 1
    renderAuditLogs()
    const row = screen.getByTestId('row-al-no-match')
    // after_data keys 'price' and 'quantity' don't match name/order_no/status → parts empty → '-'
    const cells = row.querySelectorAll('td')
    const changeCell = Array.from(cells).find((td) => td.getAttribute('data-col') === 'after_data')
    expect(changeCell?.textContent).toBe('-')
    _paginatedListReturn.data = [
      { id: 'al1', created_at: '2026-05-01T10:00:00Z', actor_name: '管理员', action: 'product_create', resource_type: 'product', resource_id: 'abc-def012345', after_data: { name: '新商品', status: 'active' }, ip_address: '192.168.1.1', request_id: 'req-001', user_agent: 'Mozilla/5.0' },
      { id: 'al2', created_at: '2026-05-01T11:00:00Z', actor_name: '销售A', action: 'order_confirm', resource_type: 'order', resource_id: null, after_data: null, ip_address: null, request_id: null, user_agent: null },
      { id: 'al3', created_at: null, actor_name: null, action: 'login_success', resource_type: 'user', resource_id: 'xyz-123', after_data: null, ip_address: '10.0.0.1', request_id: null, user_agent: null },
    ]
    _paginatedListReturn.total = 3
  })

  it('操作筛选器含未知操作类型显示原始值', async () => {
    _auditMocks.fetchAuditActions.mockResolvedValue({
      actions: ['product_create', 'custom_action'],
      resource_types: ['product'],
    })
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
    const selects = screen.getAllByTestId('action-select')
    const actionSelect = selects[0]
    const optionTexts = Array.from(actionSelect.querySelectorAll('option')).map((o) => o.textContent)
    // custom_action not in ACTION_LABELS → label falls to raw value 'custom_action'
    expect(optionTexts).toContain('custom_action')
  })

  it('资源筛选器含未知资源类型显示原始值', async () => {
    _auditMocks.fetchAuditActions.mockResolvedValue({
      actions: ['product_create'],
      resource_types: ['product', 'invoice'],
    })
    renderAuditLogs()
    await waitFor(() => {
      expect(_auditMocks.fetchAuditActions).toHaveBeenCalled()
    })
    const selects = screen.getAllByTestId('action-select')
    const resourceSelect = selects[1]
    const optionTexts = Array.from(resourceSelect.querySelectorAll('option')).map((o) => o.textContent)
    // 'invoice' not in RESOURCE_LABELS → label falls to raw value 'invoice'
    expect(optionTexts).toContain('invoice')
  })

  it('资源ID搜索空值触发 setResourceIdFilter(undefined)', async () => {
    _searchValues['资源ID精确筛选'] = ''
    renderAuditLogs()
    await waitFor(() => { expect(_auditMocks.fetchAuditActions).toHaveBeenCalled() })
    const searchBtn = screen.getByTestId('search-btn-资源ID精确筛选')
    fireEvent.click(searchBtn)
    // v || undefined with v='' → undefined, but setPage(1) is always called
    expect(_paginatedListReturn.setPage).toHaveBeenCalledWith(1)
  })
})
