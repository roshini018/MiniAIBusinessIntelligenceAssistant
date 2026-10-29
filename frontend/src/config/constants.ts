export const APP_CONFIG = {
  API_URL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  CURRENCY_SYMBOL: '₹',
  LOCALE: 'en-IN',
  CURRENCY_CODE: 'INR',
} as const;

export function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '—';
  }
  const formatted = new Intl.NumberFormat(APP_CONFIG.LOCALE, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(amount);
  return `${APP_CONFIG.CURRENCY_SYMBOL}${formatted}`;
}

export function formatNumber(count: number | null | undefined): string {
  if (count === null || count === undefined || isNaN(count)) {
    return '—';
  }
  return new Intl.NumberFormat(APP_CONFIG.LOCALE).format(count);
}
