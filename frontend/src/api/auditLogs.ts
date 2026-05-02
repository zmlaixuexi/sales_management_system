import { get } from './request'

export interface AuditLogItem {
  id: string;
  actor_id: string | null;
  actor_name: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  before_data: Record<string, unknown> | null;
  after_data: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  request_id: string | null;
  created_at: string | null;
}

interface AuditLogListResult {
  items: AuditLogItem[];
  page: number;
  page_size: number;
  total: number;
}

interface AuditActionsResult {
  actions: string[];
  resource_types: string[];
}

export async function fetchAuditLogs(params: {
  page?: number;
  page_size?: number;
  action?: string;
  resource_type?: string;
  resource_id?: string;
  start_date?: string;
  end_date?: string;
  keyword?: string;
}) {
  const res = await get<AuditLogListResult>('/audit-logs', params as Record<string, unknown>)
  return res.data
}

export async function fetchAuditActions() {
  const res = await get<AuditActionsResult>('/audit-logs/actions')
  return res.data
}
