/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _userMocks = {
  fetchUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  fetchRoles: vi.fn(),
}

vi.mock('@/api/users', () => ({
  fetchUsers: (...args: any[]) => _userMocks.fetchUsers(...args),
  createUser: (...args: any[]) => _userMocks.createUser(...args),
  updateUser: (...args: any[]) => _userMocks.updateUser(...args),
  fetchRoles: (...args: any[]) => _userMocks.fetchRoles(...args),
}))

vi.mock('@/utils', () => ({
  getApiErrorMessage: (_e: any, fallback: string) => fallback,
}))

vi.mock('@/hooks/usePaginatedList', () => ({
  usePaginatedList: (_fetchFn: any, _filters: any, _errorMsg: string) => {
    const result = _userMocks.fetchUsers()
    return {
      data: result?.data?.items ?? [],
      total: result?.data?.total ?? 0,
      loading: false,
      page: 1,
      pageSize: 20,
      keyword: '',
      setKeyword: vi.fn(),
      onPageChange: vi.fn(),
      refresh: vi.fn(),
    }
  },
}))

const _messageSuccess = vi.fn()
const _messageError = vi.fn()
vi.mock('antd', () => {
  function FormItem({ children, label }: any) {
    return <div data-testid="form-item" data-label={label}>{children}</div>
  }
  return {
    Table: ({ dataSource, columns, rowKey, locale }: any) => (
      <div>
        <table data-testid="table">
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
      </div>
    ),
    Button: ({ children, onClick, type, icon }: any) => (
      <button data-testid="button" data-type={type} onClick={onClick}>{icon}{children}</button>
    ),
    Input: Object.assign(
      ({ value, onChange, placeholder }: any) => (
        <input data-testid="input" value={value || ''} placeholder={placeholder} onChange={(e: any) => onChange?.(e)} />
      ),
      { Password: (props: any) => <input data-testid="input-password" {...props} /> },
    ),
    Select: ({ value, onChange, options }: any) => (
      <select data-testid="select" value={value} onChange={(e: any) => onChange?.(e.target.value)}>
        {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    ),
    Switch: ({ checked, onChange }: any) => (
      <button data-testid="switch" data-checked={checked} onClick={() => onChange?.(!checked)} />
    ),
    Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
    Space: ({ children }: any) => <span>{children}</span>,
    Modal: ({ title, children, open }: any) => open ? <div data-testid="modal" data-title={title}>{children}</div> : null,
    Form: Object.assign(
      ({ children }: any) => <div>{children}</div>,
      { Item: FormItem, useForm: () => [{ resetFields: vi.fn(), setFieldsValue: vi.fn(), validateFields: vi.fn() }] },
    ),
    message: { success: (...args: any[]) => _messageSuccess(...args), error: (...args: any[]) => _messageError(...args) },
  }
})

vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span>+</span>,
  SearchOutlined: () => <span>🔍</span>,
}))

const mockUsersData = {
  data: {
    items: [
      {
        id: 'user-001',
        username: 'admin',
        display_name: '管理员',
        phone: '13800000001',
        email: 'admin@test.com',
        is_active: true,
        is_superuser: true,
        roles: [{ id: 'role-1', name: 'admin', display_name: '管理员' }],
        created_at: '2026-05-01T10:00:00Z',
        updated_at: '2026-05-01T10:00:00Z',
      },
      {
        id: 'user-002',
        username: 'sales01',
        display_name: '销售员A',
        phone: null,
        email: null,
        is_active: true,
        is_superuser: false,
        roles: [{ id: 'role-2', name: 'sales', display_name: '销售' }],
        created_at: '2026-05-01T12:00:00Z',
        updated_at: null,
      },
    ],
    total: 2,
  },
}

const mockRoles = {
  success: true,
  data: [
    { id: 'role-1', name: 'admin', display_name: '管理员' },
    { id: 'role-2', name: 'sales', display_name: '销售' },
  ],
}

import UsersPage from '@/pages/Users'

function renderUsers() {
  return render(
    <MemoryRouter initialEntries={['/users']}>
      <Routes>
        <Route path="/users" element={<UsersPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('UsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _userMocks.fetchUsers.mockReturnValue(mockUsersData)
    _userMocks.fetchRoles.mockResolvedValue(mockRoles)
  })

  it('渲染用户数据行', () => {
    renderUsers()
    expect(screen.getByTestId('row-user-001')).toBeInTheDocument()
    expect(screen.getByTestId('row-user-002')).toBeInTheDocument()
  })

  it('显示用户名和显示名', () => {
    renderUsers()
    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByText('sales01')).toBeInTheDocument()
  })

  it('显示角色标签', () => {
    renderUsers()
    const tags = screen.getAllByTestId('tag')
    const tagTexts = tags.map((t) => t.textContent)
    expect(tagTexts).toContain('管理员')
    expect(tagTexts).toContain('销售')
  })

  it('显示超级管理员标记', () => {
    renderUsers()
    const tags = screen.getAllByTestId('tag')
    const goldTag = tags.find((t) => t.getAttribute('data-color') === 'gold')
    expect(goldTag).toBeTruthy()
    expect(goldTag?.textContent).toBe('是')
  })

  it('显示新建用户按钮', () => {
    renderUsers()
    expect(screen.getByText('新建用户')).toBeInTheDocument()
  })

  it('显示编辑按钮', () => {
    renderUsers()
    const editButtons = screen.getAllByText('编辑')
    expect(editButtons.length).toBeGreaterThanOrEqual(2)
  })

  it('空值显示为 --', () => {
    renderUsers()
    const dashes = screen.getAllByText('--')
    expect(dashes.length).toBeGreaterThanOrEqual(2) // phone + email for sales01
  })

  it('点击新建用户按钮打开弹窗', async () => {
    renderUsers()
    screen.getByText('新建用户').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
      expect(screen.getByTestId('modal').getAttribute('data-title')).toBe('新建用户')
    })
  })

  it('无数据时显示空状态提示', () => {
    _userMocks.fetchUsers.mockReturnValue({ data: { items: [], total: 0 } })
    renderUsers()
    expect(screen.getByText('暂无用户数据')).toBeInTheDocument()
  })
})
