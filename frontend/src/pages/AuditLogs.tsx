import { useState, useEffect, useCallback } from 'react';
import { Table, Select, DatePicker, Input, Tag, Space, Typography, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { fetchAuditLogs, fetchAuditActions, type AuditLogItem } from '@/api/auditLogs';

const { RangePicker } = DatePicker;
const { Text } = Typography;

const ACTION_LABELS: Record<string, { label: string; color: string }> = {
  login_success: { label: '登录成功', color: 'green' },
  login_failed: { label: '登录失败', color: 'red' },
  product_create: { label: '新增商品', color: 'blue' },
  product_update: { label: '编辑商品', color: 'orange' },
  product_delete: { label: '删除商品', color: 'red' },
  product_disable: { label: '停用商品', color: 'default' },
  customer_create: { label: '新增客户', color: 'blue' },
  customer_update: { label: '编辑客户', color: 'orange' },
  customer_delete: { label: '删除客户', color: 'red' },
  customer_transfer: { label: '转移客户', color: 'purple' },
  order_create: { label: '创建订单', color: 'blue' },
  order_update: { label: '编辑订单', color: 'orange' },
  order_confirm: { label: '确认订单', color: 'green' },
  order_cancel: { label: '取消订单', color: 'red' },
  payment_create: { label: '登记收款', color: 'green' },
  payment_reverse: { label: '冲正收款', color: 'red' },
  inventory_adjust: { label: '库存调整', color: 'orange' },
  export_products: { label: '导出商品', color: 'cyan' },
  export_customers: { label: '导出客户', color: 'cyan' },
  export_orders: { label: '导出订单', color: 'cyan' },
  export_payments: { label: '导出收款', color: 'cyan' },
  product_import: { label: '批量导入商品', color: 'geekblue' },
};

const RESOURCE_LABELS: Record<string, string> = {
  user: '用户',
  product: '商品',
  customer: '客户',
  order: '订单',
  payment: '收款',
};

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState<string | undefined>();
  const [resourceFilter, setResourceFilter] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);
  const [keyword, setKeyword] = useState('');
  const [actions, setActions] = useState<string[]>([]);
  const [resourceTypes, setResourceTypes] = useState<string[]>([]);

  const loadActions = useCallback(async () => {
    try {
      const data = await fetchAuditActions();
      setActions(data.actions || []);
      setResourceTypes(data.resource_types || []);
    } catch { /* ignore */ }
  }, []);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (actionFilter) params.action = actionFilter;
      if (resourceFilter) params.resource_type = resourceFilter;
      if (keyword) params.keyword = keyword;
      if (dateRange && dateRange[0]) params.start_date = dateRange[0].format('YYYY-MM-DD');
      if (dateRange && dateRange[1]) params.end_date = dateRange[1].format('YYYY-MM-DD');
      const data = await fetchAuditLogs(params as Parameters<typeof fetchAuditLogs>[0]);
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch { /* ignore */ }
    setLoading(false);
  }, [page, pageSize, actionFilter, resourceFilter, dateRange, keyword]);

  useEffect(() => { loadActions(); }, [loadActions]);
  useEffect(() => { loadLogs(); }, [loadLogs]);

  const columns: ColumnsType<AuditLogItem> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 170,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作人',
      dataIndex: 'actor_name',
      width: 120,
      render: (v: string) => v || '-',
    },
    {
      title: '操作',
      dataIndex: 'action',
      width: 120,
      render: (v: string) => {
        const info = ACTION_LABELS[v];
        return info ? <Tag color={info.color}>{info.label}</Tag> : <Tag>{v}</Tag>;
      },
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      width: 100,
      render: (v: string) => RESOURCE_LABELS[v] || v || '-',
    },
    {
      title: '资源ID',
      dataIndex: 'resource_id',
      width: 120,
      ellipsis: true,
      render: (v: string) => v ? <Text copyable={{ text: v }} style={{ fontSize: 12 }}>{v.slice(0, 8)}...</Text> : '-',
    },
    {
      title: '变更内容',
      dataIndex: 'after_data',
      render: (_: unknown, record: AuditLogItem) => {
        const parts: string[] = [];
        if (record.after_data) {
          Object.entries(record.after_data).forEach(([k, v]) => {
            if (k === 'name' || k === 'order_no' || k === 'status') {
              parts.push(`${k}: ${String(v)}`);
            }
          });
        }
        return parts.length > 0 ? <Text style={{ fontSize: 12 }}>{parts.join(' | ')}</Text> : '-';
      },
    },
    {
      title: 'IP',
      dataIndex: 'ip_address',
      width: 130,
      render: (v: string, record: AuditLogItem) => {
        if (!v) return '-';
        const details: string[] = [];
        if (record.request_id) details.push(`RID: ${record.request_id}`);
        if (record.user_agent) details.push(`UA: ${record.user_agent.slice(0, 50)}`);
        return details.length > 0 ? (
          <Tooltip title={details.join('\n')}>
            <Text style={{ fontSize: 12 }}>{v}</Text>
          </Tooltip>
        ) : <Text style={{ fontSize: 12 }}>{v}</Text>;
      },
    },
  ];

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>操作日志</Typography.Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          allowClear
          placeholder="操作类型"
          style={{ width: 140 }}
          value={actionFilter}
          onChange={setActionFilter}
          options={actions.map(a => ({ label: ACTION_LABELS[a]?.label || a, value: a }))}
        />
        <Select
          allowClear
          placeholder="资源类型"
          style={{ width: 120 }}
          value={resourceFilter}
          onChange={setResourceFilter}
          options={resourceTypes.map(r => ({ label: RESOURCE_LABELS[r] || r, value: r }))}
        />
        <RangePicker
          value={dateRange}
          onChange={(dates) => setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null)}
        />
        <Input.Search
          placeholder="搜索操作人或资源ID"
          style={{ width: 200 }}
          onSearch={setKeyword}
          allowClear
        />
      </Space>
      <Table<AuditLogItem>
        rowKey="id"
        columns={columns}
        dataSource={logs}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
        size="small"
        scroll={{ x: 900 }}
      />
    </div>
  );
}
