import { useState, useEffect, useCallback } from 'react'
import { Table, Button, Space, Tag, Modal, Form, Input, Checkbox, message, Popconfirm } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { fetchRoles, fetchPermissions, createRole, updateRole, deleteRole } from '@/api/roles'
import type { RoleItem, PermissionItem } from '@/api/roles'
import { getApiErrorMessage, isToastDisplayed } from '@/utils'
import useDocumentTitle from '@/hooks/useDocumentTitle'

export default function RolesPage() {
  useDocumentTitle('角色管理')
  const [roles, setRoles] = useState<RoleItem[]>([])
  const [permissions, setPermissions] = useState<Record<string, PermissionItem[]>>({})
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRole, setEditingRole] = useState<RoleItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const loadRoles = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchRoles()
      if (res.success && Array.isArray(res.data)) setRoles(res.data)
    } catch (e: unknown) {
      if (!isToastDisplayed(e)) message.error(getApiErrorMessage(e, '加载角色列表失败'))
    } finally {
      setLoading(false)
    }
  }, [])

  const loadPermissions = useCallback(async () => {
    try {
      const res = await fetchPermissions()
      if (res.success && res.data && typeof res.data === 'object') setPermissions(res.data as Record<string, PermissionItem[]>)
    } catch { /* 静默 */ }
  }, [])

  useEffect(() => { loadRoles() }, [loadRoles])
  useEffect(() => { loadPermissions() }, [loadPermissions])

  const openCreate = () => {
    setEditingRole(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (role: RoleItem) => {
    setEditingRole(role)
    form.setFieldsValue({
      name: role.name,
      display_name: role.display_name || '',
      description: role.description || '',
      permission_ids: role.permissions.map((p) => p.id),
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      const payload = {
        name: values.name,
        display_name: values.display_name || undefined,
        description: values.description || undefined,
        permission_ids: values.permission_ids || [],
      }

      if (editingRole) {
        const res = await updateRole(editingRole.id, payload)
        if (res.success) {
          message.success('角色已更新')
          setModalOpen(false)
          loadRoles()
        }
      } else {
        const res = await createRole(payload)
        if (res.success) {
          message.success('角色已创建')
          setModalOpen(false)
          loadRoles()
        }
      }
    } catch (e: unknown) {
      if (isToastDisplayed(e)) return
      const msg = editingRole ? '更新角色失败' : '创建角色失败'
      message.error(getApiErrorMessage(e, msg))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (roleId: string) => {
    try {
      const res = await deleteRole(roleId)
      if (res.success) {
        message.success('角色已删除')
        loadRoles()
      }
    } catch (e: unknown) {
      if (!isToastDisplayed(e)) message.error(getApiErrorMessage(e, '删除角色失败'))
    }
  }

  const columns: ColumnsType<RoleItem> = [
    {
      title: '角色标识',
      dataIndex: 'name',
      width: 140,
    },
    {
      title: '显示名',
      dataIndex: 'display_name',
      width: 140,
      render: (v: string | null) => v || '--',
    },
    {
      title: '说明',
      dataIndex: 'description',
      width: 200,
      render: (v: string | null) => v || '--',
    },
    {
      title: '权限数',
      dataIndex: 'permissions',
      width: 80,
      render: (perms: PermissionItem[]) => perms.length,
    },
    {
      title: '关联用户',
      dataIndex: 'user_count',
      width: 90,
      render: (v: number) => `${v} 人`,
    },
    {
      title: '权限概览',
      dataIndex: 'permissions',
      render: (perms: PermissionItem[]) => {
        if (perms.length === 0) return <Tag>无权限</Tag>
        const modules = [...new Set(perms.map((p) => p.module))]
        return (
          <Space size={[4, 4]} wrap>
            {modules.map((m) => <Tag key={m} color="blue">{m}</Tag>)}
          </Space>
        )
      },
    },
    {
      title: '操作',
      width: 140,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm
            title="确认删除该角色？"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" size="small" danger disabled={record.user_count > 0}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const permissionOptions = Object.entries(permissions).flatMap(([module, perms]) =>
    perms.map((p) => ({ label: `${module} - ${p.name}`, value: p.id }))
  )

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>角色权限管理</h3>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建角色
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={roles}
        rowKey="id"
        loading={loading}
        pagination={false}
        locale={{ emptyText: '暂无角色数据' }}
      />

      <Modal
        title={editingRole ? '编辑角色' : '新建角色'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="角色标识" rules={[{ required: true, message: '请输入角色标识' }, { max: 50, message: '最多 50 个字符' }]}>
            <Input maxLength={50} placeholder="如 sales_manager" />
          </Form.Item>
          <Form.Item name="display_name" label="显示名" rules={[{ max: 100, message: '最多 100 个字符' }]}>
            <Input maxLength={100} placeholder="如 销售主管" />
          </Form.Item>
          <Form.Item name="description" label="说明" rules={[{ max: 255, message: '最多 255 个字符' }]}>
            <Input.TextArea maxLength={255} rows={2} />
          </Form.Item>
          <Form.Item name="permission_ids" label="权限">
            <Checkbox.Group options={permissionOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
