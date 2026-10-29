import { APP_CONFIG } from '../config/constants';
import type { AskResponse, ChartDataResponse, HealthResponse, KPIResponse } from '../types/bi';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number = 500) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  let data: any;
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const errorMsg =
      (data && typeof data === 'object' && data.error) ||
      (typeof data === 'string' && data.length > 0 ? data : `Request failed with status ${res.status}`);
    throw new ApiError(errorMsg, res.status);
  }

  return data as T;
}

export async function fetchHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${APP_CONFIG.API_URL}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    const data = await handleResponse<HealthResponse>(res);
    if (!data || data.status !== 'ok') {
      throw new ApiError('Backend returned invalid health response.', 500);
    }
    return data;
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError('Unable to connect to backend server. Is FastAPI running on port 8000?', 503);
  }
}

export async function fetchKpis(): Promise<KPIResponse> {
  try {
    const res = await fetch(`${APP_CONFIG.API_URL}/kpis`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    return await handleResponse<KPIResponse>(res);
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(err?.message || 'Failed to load KPI metrics.', 500);
  }
}

export async function fetchChartData(): Promise<ChartDataResponse> {
  try {
    const res = await fetch(`${APP_CONFIG.API_URL}/chart-data`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    return await handleResponse<ChartDataResponse>(res);
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(err?.message || 'Failed to load chart data.', 500);
  }
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const trimmed = question.trim();
  if (!trimmed) {
    throw new ApiError('Question cannot be empty.', 400);
  }

  try {
    const res = await fetch(`${APP_CONFIG.API_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ question: trimmed }),
    });
    return await handleResponse<AskResponse>(res);
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      err?.message || 'Network error while contacting assistant backend.',
      500
    );
  }
}
