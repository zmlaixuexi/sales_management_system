import { get, post } from './request'
import type { PaginatedData } from '@/types'

export interface InventoryMovement {
  id: string
  product_id: string
  movement_type: string
  quantity_before: number
  quantity_change: number
  quantity_after: number
  related_type: string | null
  related_id: string | null
  remark: string | null
  created_at: string | null
}

export interface InventoryAdjustPayload {
  product_id: string
  quantity_change: number
  remark?: string | null
}

export interface InventoryAdjustedResult {
  product_id: string
  quantity_before: number
  quantity_change: number
  quantity_after: number
}

export async function fetchInventoryMovements(params?: {
  page?: number
  page_size?: number
  product_id?: string
  movement_type?: string
}) {
  return get<PaginatedData<InventoryMovement>>('/inventory/movements', params as Record<string, unknown>)
}

export async function adjustInventory(data: InventoryAdjustPayload) {
  return post<InventoryAdjustedResult>('/inventory/adjustments', data)
}
