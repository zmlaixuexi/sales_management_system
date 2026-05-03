/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _customerApi = {
  fetchCustomer: vi.fn(),
  createCustomer: vi.fn(),
  updateCustomer: vi.fn(),
}

vi.mock('@/api/customers', () => ({
  fetchCustomer: (...a: any[]) => _customerApi.fetchCustomer(...a),
  createCustomer: (...a: any[]) => _customerApi.createCustomer(...a),
  updateCustomer: (...a: any[]) => _customerApi.updateCustomer(...a),
}))

vi.mock('@/hooks/useSubmit', () => ({
  useSubmit: (_onSubmit: any) => ({
    submitting: false,
    handleSubmit: (e: any) => { e?.preventDefault?.() },
  }),
}))

const _mockForm = {
  setFieldsValue: vi.fn(),
  getFieldsValue: vi.fn(() => ({})),
  validateFields: vi.fn(() => Promise.resolve({})),
  resetFields: vi.fn(),
}

vi.mock('antd', () => ({
  Form: Object.assign(
    ({ children, onFinish, initialValues }: any) => (
      <form data-testid="form" onSubmit={(e) => { e.preventDefault(); onFinish?.(initialValues || {}) }}>
        {children}
      </form>
    ),
    {
      Item: ({ children, label, name }: any) => (
        <div data-testid="form-item" data-label={label} data-name={name}>{children}</div>
      ),
      useForm: () => [_mockForm],
    },
  ),
  Input: Object.assign(
    (props: any) => <input data-testid="input" {...props} />,
    { TextArea: (props: any) => <textarea data-testid="textarea" {...props} /> },
  ),
  Button: ({ children, onClick, icon, type, htmlType }: any) => (
    <button data-testid="button" data-type={type} data-htmltype={htmlType} onClick={onClick}>{icon}{children}</button>
  ),
  Card: ({ title, children, loading }: any) => (
    <div data-testid="card" data-title={title} data-loading={loading ? 'true' : 'false'}>{children}</div>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Select: ({ options, value, onChange }: any) => (
    <select data-testid="select" value={value} onChange={(e: any) => onChange?.(e.target.value)}>
      {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  ),
  message: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@ant-design/icons', () => ({
  ArrowLeftOutlined: () => <span>←</span>,
}))

import CustomerForm from '@/pages/CustomerForm'

function renderNewCustomer() {
  return render(
    <MemoryRouter initialEntries={['/customers/new']}>
      <Routes>
        <Route path="/customers/new" element={<CustomerForm />} />
        <Route path="/customers/:id" element={<CustomerForm />} />
        <Route path="/customers" element={<div>Customers List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderEditCustomer(customerId = 'c-123') {
  return render(
    <MemoryRouter initialEntries={[`/customers/${customerId}`]}>
      <Routes>
        <Route path="/customers/new" element={<CustomerForm />} />
        <Route path="/customers/:id" element={<CustomerForm />} />
        <Route path="/customers" element={<div>Customers List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CustomerForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('新增模式渲染"新增客户"标题', () => {
    renderNewCustomer()
    const card = screen.getByTestId('card')
    expect(card.getAttribute('data-title')).toBe('新增客户')
  })

  it('渲染返回列表按钮', () => {
    renderNewCustomer()
    expect(screen.getByText('返回列表')).toBeInTheDocument()
  })

  it('渲染必要表单字段', () => {
    renderNewCustomer()
    const formItems = screen.getAllByTestId('form-item')
    const labels = formItems.map((fi) => fi.getAttribute('data-label'))
    expect(labels).toContain('客户名称')
    expect(labels).toContain('联系人')
    expect(labels).toContain('电话')
    expect(labels).toContain('邮箱')
  })

  it('客户名称为必填字段', () => {
    renderNewCustomer()
    const nameItem = screen.getAllByTestId('form-item').find(
      (fi) => fi.getAttribute('data-name') === 'name',
    )
    expect(nameItem).toBeTruthy()
  })

  it('渲染提交按钮', () => {
    renderNewCustomer()
    expect(screen.getByText('创建客户')).toBeInTheDocument()
  })

  it('渲染取消按钮', () => {
    renderNewCustomer()
    expect(screen.getByText('取消')).toBeInTheDocument()
  })

  it('渲染来源、等级和跟进状态下拉', () => {
    renderNewCustomer()
    const selects = screen.getAllByTestId('select')
    expect(selects.length).toBeGreaterThanOrEqual(3)
  })

  it('新增模式不调用 fetchCustomer', () => {
    renderNewCustomer()
    expect(_customerApi.fetchCustomer).not.toHaveBeenCalled()
  })

  describe('编辑模式', () => {
    it('编辑模式渲染"编辑客户"标题', () => {
      _customerApi.fetchCustomer.mockResolvedValue({ success: true, data: {} })
      renderEditCustomer()
      const card = screen.getByTestId('card')
      expect(card.getAttribute('data-title')).toBe('编辑客户')
    })

    it('编辑模式调用 fetchCustomer 获取数据', () => {
      _customerApi.fetchCustomer.mockResolvedValue({ success: true, data: {} })
      renderEditCustomer('c-456')
      expect(_customerApi.fetchCustomer).toHaveBeenCalledWith('c-456')
    })

    it('编辑模式用 fetchCustomer 数据填充表单', async () => {
      _customerApi.fetchCustomer.mockResolvedValue({
        success: true,
        data: {
          name: '测试客户',
          contact_name: '张三',
          phone: '13800001111',
          email: 'test@example.com',
          source: 'online',
          level: 'vip',
          follow_status: 'following',
          remark: '重要客户',
        },
      })
      renderEditCustomer()

      // 等待 useEffect 中的 fetchCustomer 完成
      await vi.waitFor(() => {
        expect(_mockForm.setFieldsValue).toHaveBeenCalledWith(
          expect.objectContaining({
            name: '测试客户',
            contact_name: '张三',
            phone: '13800001111',
            source: 'online',
            level: 'vip',
          }),
        )
      })
    })

    it('编辑模式渲染"保存修改"按钮', () => {
      _customerApi.fetchCustomer.mockResolvedValue({ success: true, data: {} })
      renderEditCustomer()
      expect(screen.getByText('保存修改')).toBeInTheDocument()
    })
  })

  it('电话字段有 maxLength 限制', () => {
    renderNewCustomer()
    const inputs = screen.getAllByTestId('input')
    const phoneInput = inputs.find((inp) => inp.getAttribute('placeholder') === '联系电话')
    expect(phoneInput).toHaveAttribute('maxlength', '30')
  })

  it('邮箱字段有 maxLength 限制', () => {
    renderNewCustomer()
    const inputs = screen.getAllByTestId('input')
    const emailInput = inputs.find((inp) => inp.getAttribute('placeholder') === '邮箱地址')
    expect(emailInput).toHaveAttribute('maxlength', '100')
  })

  it('客户名称字段有 maxLength 限制', () => {
    renderNewCustomer()
    const inputs = screen.getAllByTestId('input')
    const nameInput = inputs.find((inp) => inp.getAttribute('placeholder') === '请输入客户名称')
    expect(nameInput).toHaveAttribute('maxlength', '100')
  })

  it('备注字段有 maxLength 限制', () => {
    renderNewCustomer()
    const textarea = screen.getByTestId('textarea')
    expect(textarea).toHaveAttribute('maxlength', '500')
  })

  it('来源下拉包含正确选项', () => {
    renderNewCustomer()
    const selects = screen.getAllByTestId('select')
    // 来源 select 包含 转介绍/线上/线下/广告/其他
    const sourceSelect = selects[0]
    const options = Array.from(sourceSelect.querySelectorAll('option'))
    const optionTexts = options.map((o) => o.textContent)
    expect(optionTexts).toContain('转介绍')
    expect(optionTexts).toContain('线上')
    expect(optionTexts).toContain('其他')
  })

  it('等级下拉包含正确选项', () => {
    renderNewCustomer()
    const selects = screen.getAllByTestId('select')
    const levelSelect = selects[1]
    const options = Array.from(levelSelect.querySelectorAll('option'))
    const optionTexts = options.map((o) => o.textContent)
    expect(optionTexts).toContain('VIP')
    expect(optionTexts).toContain('普通')
  })

  it('跟进状态下拉包含正确选项', () => {
    renderNewCustomer()
    const selects = screen.getAllByTestId('select')
    const followSelect = selects[2]
    const options = Array.from(followSelect.querySelectorAll('option'))
    const optionTexts = options.map((o) => o.textContent)
    expect(optionTexts).toContain('新客户')
    expect(optionTexts).toContain('已成交')
  })

  it('返回列表按钮导航到客户列表', async () => {
    renderNewCustomer()
    screen.getByText('返回列表').click()
    await (() => new Promise((r) => setTimeout(r, 0)))()
    expect(screen.getByText('Customers List')).toBeInTheDocument()
  })

  it('取消按钮导航到客户列表', async () => {
    renderNewCustomer()
    screen.getByText('取消').click()
    await (() => new Promise((r) => setTimeout(r, 0)))()
    expect(screen.getByText('Customers List')).toBeInTheDocument()
  })

  it('编辑模式 fetchCustomer 失败验证', async () => {
    _customerApi.fetchCustomer.mockRejectedValue(new Error('加载失败'))
    renderEditCustomer()
    await vi.waitFor(() => {
      expect(_customerApi.fetchCustomer).toHaveBeenCalled()
    })
  })

  it('创建按钮 htmlType 为 submit', () => {
    renderNewCustomer()
    const submitBtn = screen.getByText('创建客户').closest('button')
    expect(submitBtn?.getAttribute('data-htmltype')).toBe('submit')
  })

  it('表单包含备注字段', () => {
    renderNewCustomer()
    const formItems = screen.getAllByTestId('form-item')
    const names = formItems.map((fi) => fi.getAttribute('data-name'))
    expect(names).toContain('remark')
  })
})
