import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}


// Format percentage
export function formatPercent(value: number, decimals: number = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

// Format number with K, M, B suffixes
export function formatNumber(num: number): string {
  if (num >= 1e9) {
    return `${(num / 1e9).toFixed(1)}B`;
  }
  if (num >= 1e6) {
    return `${(num / 1e6).toFixed(1)}M`;
  }
  if (num >= 1e3) {
    return `${(num / 1e3).toFixed(1)}K`;
  }
  return num.toFixed(0);
}

// Format stock code for display (add .JK suffix if not present)
export function formatStockCode(code: string): string {
  if (code.endsWith('.JK')) return code;
  return `${code}.JK`;
}

// Format time for Indonesian timezone (WIB)
export function formatWIBTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(dateObj);
}

// Format date for Indonesian locale
export function formatWIBDate(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(dateObj);
}

// Format datetime for Indonesian locale
export function formatWIBDateTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(dateObj);
}

// Get color class for P&L values
export function getPnLColorClass(value: number): string {
  if (value > 0) return 'text-success-600';
  if (value < 0) return 'text-danger-600';
  return 'text-secondary-600';
}

// Get color class for signal types
export function getSignalColorClass(signalType: string): string {
  switch (signalType) {
    case 'STRONG_BUY':
      return 'text-success-700 bg-success-100';
    case 'BUY':
      return 'text-success-600 bg-success-50';
    case 'HOLD':
      return 'text-secondary-600 bg-secondary-100';
    case 'SELL':
      return 'text-danger-600 bg-danger-50';
    case 'STRONG_SELL':
      return 'text-danger-700 bg-danger-100';
    default:
      return 'text-secondary-600 bg-secondary-100';
  }
}

// Get color class for alert priorities
export function getAlertPriorityColor(priority: string): string {
  switch (priority) {
    case 'critical':
      return 'text-danger-700 bg-danger-100 border-danger-200';
    case 'high':
      return 'text-warning-700 bg-warning-100 border-warning-200';
    case 'medium':
      return 'text-primary-700 bg-primary-100 border-primary-200';
    case 'low':
      return 'text-secondary-700 bg-secondary-100 border-secondary-200';
    default:
      return 'text-secondary-700 bg-secondary-100 border-secondary-200';
  }
}

// Check if market is currently open (IDX: 09:00-15:49 WIB, Mon-Fri)
export function isMarketOpen(): boolean {
  const now = new Date();
  const jakartaTime = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Jakarta' }));

  const day = jakartaTime.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
  const hour = jakartaTime.getHours();
  const minute = jakartaTime.getMinutes();

  // Check if it's a weekday (Monday to Friday)
  if (day === 0 || day === 6) return false;

  // Check if it's within trading hours (09:00 to 15:49)
  const currentTime = hour * 60 + minute;
  const marketOpen = 9 * 60; // 09:00
  const marketClose = 15 * 60 + 49; // 15:49

  return currentTime >= marketOpen && currentTime <= marketClose;
}

// Debounce function for search inputs
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number;

  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = window.setTimeout(() => func(...args), wait);
  };
}

// Throttle function for scroll events
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// Generate color for charts
export function generateChartColors(count: number, alpha: number = 0.8): string[] {
  const colors = [
    `rgba(239, 68, 68, ${alpha})`,   // Red
    `rgba(34, 197, 94, ${alpha})`,   // Green
    `rgba(59, 130, 246, ${alpha})`,  // Blue
    `rgba(245, 158, 11, ${alpha})`,  // Orange
    `rgba(168, 85, 247, ${alpha})`,  // Purple
    `rgba(20, 184, 166, ${alpha})`,  // Teal
    `rgba(251, 191, 36, ${alpha})`,  // Yellow
    `rgba(244, 63, 94, ${alpha})`,   // Pink
  ];

  const result: string[] = [];
  for (let i = 0; i < count; i++) {
    result.push(colors[i % colors.length]);
  }

  return result;
}

// Calculate relative time (e.g., "2 hours ago")
export function getRelativeTime(date: string | Date): string {
  const now = new Date();
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const diffInSeconds = Math.floor((now.getTime() - dateObj.getTime()) / 1000);

  if (diffInSeconds < 60) return `${diffInSeconds} detik yang lalu`;
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} menit yang lalu`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} jam yang lalu`;
  if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)} hari yang lalu`;
  if (diffInSeconds < 31536000) return `${Math.floor(diffInSeconds / 2592000)} bulan yang lalu`;

  return `${Math.floor(diffInSeconds / 31536000)} tahun yang lalu`;
}

// Format date and time for display
export function formatDateTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(dateObj);
}

// Format time only
export function formatTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(dateObj);
}

// Enhanced IDR formatter with abbreviation option
export function formatIDR(amount: number, abbreviated: boolean = false): string {
  if (abbreviated) {
    if (amount >= 1e12) {
      return `Rp ${(amount / 1e12).toFixed(1)}T`;
    }
    if (amount >= 1e9) {
      return `Rp ${(amount / 1e9).toFixed(1)}B`;
    }
    if (amount >= 1e6) {
      return `Rp ${(amount / 1e6).toFixed(1)}M`;
    }
    if (amount >= 1e3) {
      return `Rp ${(amount / 1e3).toFixed(1)}K`;
    }
  }

  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

// Local storage helpers with error handling
export const storage = {
  get: <T>(key: string, defaultValue: T): T => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  },

  set: <T>(key: string, value: T): void => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn('Failed to save to localStorage:', error);
    }
  },

  remove: (key: string): void => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Failed to remove from localStorage:', error);
    }
  },
};