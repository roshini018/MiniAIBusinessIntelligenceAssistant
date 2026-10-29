export type SupportedIntent =
  | 'total_revenue'
  | 'top_product'
  | 'monthly_trend'
  | 'top_region'
  | 'month_comparison'
  | 'unsupported';

export interface AskResponse {
  question: string;
  intent: SupportedIntent | string;
  answer: string;
  sql_used?: string | null;
  params?: (string | number)[];
  supporting_data?: Record<string, any>[];
  classified_by?: 'gemini' | 'keywords' | 'unknown' | string;
}

export interface KPIResponse {
  total_revenue: number;
  orders_counted: number;
  top_product: {
    name: string | null;
    revenue: number;
  };
  top_region: {
    name: string | null;
    revenue: number;
  };
  timeframe?: {
    start_month?: string | null;
    end_month?: string | null;
    label?: string | null;
  };
}

export interface HealthResponse {
  status: string;
}

export interface QueryHistoryItem {
  id: string;
  timestamp: Date;
  question: string;
  response?: AskResponse;
  error?: string;
  isLoading?: boolean;
}

export interface ChartDataResponse {
  monthly_trend: { month: string; revenue: number }[];
  products: { product: string; revenue: number }[];
  regions: { region: string; revenue: number }[];
}
