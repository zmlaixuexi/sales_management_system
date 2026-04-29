import apiClient from './client';

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
  created_at: string | null;
}

export async function fetchAuditLogs(params: {
  page?: number;
  page_size?: number;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
  keyword?: string;
}) {
  const { data } = await apiClient.get('/audit-logs', { params });
  return data.data;
}

export async function fetchAuditActions() {
  const { data } = await apiClient.get('/audit-logs/actions');
  return data.data;
}
