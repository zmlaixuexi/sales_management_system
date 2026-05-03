/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _auditMocks = {
  fetchAuditActions: vi.fn(),
}

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
  Table: ({ dataSource, columns, rowKey, locale }: any) => (
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
      Search: ({ placeholder }: any) => (
        <input data-testid="search-input" placeholder={placeholder} />
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
  DatePicker: { RangePicker: () => <input data-testid="date-range" /> },
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
})
