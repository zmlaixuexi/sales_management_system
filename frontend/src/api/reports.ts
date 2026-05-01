import { get } from './request'

export interface SalesSummary {
  total_amount: string
  total_cost: string
  gross_profit: string
  gross_margin: string
  order_count: number
  period: string
  start_date: string
  end_date: string
}

export interface SalesTrendItem {
  date: string
  amount: string
  order_count: number
}

export interface ProductRankingItem {
  rank: number
  product_id: string
  product_name: string
  sku: string | null
  total_sales: string
  total_cost: string
  total_quantity: number
}

export interface InventoryWarningItem {
  id: string
  sku: string
  name: string
  stock_quantity: number
  sale_price: string
}

export interface CustomerRankingItem {
  rank: number
  customer_id: string
  customer_name: string
  total_sales: string
  total_cost?: string
  gross_profit?: string
  order_count: number
}

export interface SalespersonRankingItem {
  rank: number
  user_id: string
  name: string
  total_sales: string
  total_cost?: string
  gross_profit?: string
  order_count: number
}

export async function fetchSalesSummary(period?: string) {
  return get<SalesSummary>('/reports/sales-summary', { period })
}

export async function fetchSalesTrend(period?: string) {
  return get<{ items: SalesTrendItem[]; period: string }>('/reports/sales-trend', { period })
}

export async function fetchProductRanking(params?: { period?: string; limit?: number }) {
  return get<{ items: ProductRankingItem[]; period: string }>('/reports/product-ranking', params as Record<string, unknown>)
}

export async function fetchInventoryWarning(threshold?: number) {
  const params: Record<string, unknown> = {}
  if (threshold !== undefined) params.threshold = threshold
  return get<{ items: InventoryWarningItem[]; threshold: number; total: number }>('/reports/inventory-warning', params)
}

export async function fetchCustomerRanking(params?: { period?: string; limit?: number }) {
  return get<{ items: CustomerRankingItem[]; period: string }>('/reports/customer-ranking', params as Record<string, unknown>)
}

export async function fetchSalespersonRanking(params?: { period?: string; limit?: number }) {
  return get<{ items: SalespersonRankingItem[]; period: string }>('/reports/salesperson-ranking', params as Record<string, unknown>)
}
