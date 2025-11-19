import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow } from 'date-fns';
import type { AlertPriority, SignalType } from '@/types/api';

/**
 * Merge Tailwind CSS classes with clsx
 * Combines class names and handles Tailwind CSS conflicts
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ============================================================================
// Date/Time Formatting Functions
// ============================================================================

/**
 * Format a date to WIB (Western Indonesian Time) format - time only
 * WIB is UTC+7
 */
export function formatWIBTime(date: Date | string | number): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return format(dateObj, 'HH:mm:ss');
}

/**
 * Format a date to WIB (Western Indonesian Time) format - full date and time
 */
export function formatWIBDateTime(date: Date | string | number): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return format(dateObj, 'dd MMM yyyy, HH:mm:ss');
}

/**
 * Format a date with date and time
 */
export function formatDateTime(date: Date | string | number): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return format(dateObj, 'PPpp'); // e.g., "Apr 29, 2021, 9:00:00 AM"
}

/**
 * Format time only
 */
export function formatTime(date: Date | string | number): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return format(dateObj, 'HH:mm');
}

/**
 * Get relative time (e.g., "2 hours ago")
 */
export function getRelativeTime(date: Date | string | number): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return formatDistanceToNow(dateObj, { addSuffix: true });
}

// ============================================================================
// Market Functions
// ============================================================================

/**
 * Check if the Indonesian stock market (IDX) is currently open
 * Trading hours:
 * - Monday to Friday
 * - Session 1: 09:00 - 12:00 WIB
 * - Session 2: 13:30 - 15:50 WIB
 */
export function isMarketOpen(): boolean {
  const now = new Date();

  // Get current time in WIB (UTC+7)
  // JavaScript Date uses local timezone, so we need to adjust
  const wibOffset = 7 * 60; // WIB is UTC+7 in minutes
  const localOffset = now.getTimezoneOffset(); // Local timezone offset in minutes (negative for east of UTC)
  const wibTime = new Date(now.getTime() + (wibOffset + localOffset) * 60 * 1000);

  const day = wibTime.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
  const hours = wibTime.getHours();
  const minutes = wibTime.getMinutes();
  const totalMinutes = hours * 60 + minutes;

  // Check if it's a weekday (Monday to Friday)
  if (day === 0 || day === 6) {
    return false; // Weekend
  }

  // Session 1: 09:00 - 12:00 (540 - 720 minutes)
  const session1Start = 9 * 60; // 09:00
  const session1End = 12 * 60; // 12:00

  // Session 2: 13:30 - 15:50 (810 - 950 minutes)
  const session2Start = 13 * 60 + 30; // 13:30
  const session2End = 15 * 60 + 50; // 15:50

  return (
    (totalMinutes >= session1Start && totalMinutes < session1End) ||
    (totalMinutes >= session2Start && totalMinutes < session2End)
  );
}

// ============================================================================
// Number Formatting Functions
// ============================================================================

/**
 * Format number as Indonesian Rupiah (IDR)
 */
export function formatIDR(value: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format number as percentage
 */
export function formatPercent(value: number, decimals: number = 2): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

// ============================================================================
// Stock-related Functions
// ============================================================================

/**
 * Format stock code (e.g., "BBCA" -> "BBCA.JK")
 */
export function formatStockCode(code: string): string {
  if (!code) return '';
  // If it already has .JK suffix, return as is
  if (code.endsWith('.JK')) return code;
  // Otherwise add .JK suffix for Jakarta Stock Exchange
  return `${code}.JK`;
}

// ============================================================================
// CSS Class Helper Functions
// ============================================================================

/**
 * Get color class for P&L values
 */
export function getPnLColorClass(value: number): string {
  if (value > 0) return 'text-success-600';
  if (value < 0) return 'text-danger-600';
  return 'text-secondary-600';
}

/**
 * Get color class for trading signals
 */
export function getSignalColorClass(signalType: SignalType | string): string {
  switch (signalType) {
    case 'BUY':
    case 'STRONG_BUY':
      return 'text-success-600 bg-success-50 border-success-200';
    case 'SELL':
    case 'STRONG_SELL':
      return 'text-danger-600 bg-danger-50 border-danger-200';
    case 'HOLD':
      return 'text-warning-600 bg-warning-50 border-warning-200';
    default:
      return 'text-secondary-600 bg-secondary-50 border-secondary-200';
  }
}

/**
 * Get color class for alert priority
 */
export function getAlertPriorityColor(priority: AlertPriority | string): string {
  switch (priority) {
    case 'critical':
      return 'bg-danger-100 text-danger-800 border-danger-200';
    case 'high':
      return 'bg-warning-100 text-warning-800 border-warning-200';
    case 'medium':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'low':
      return 'bg-secondary-100 text-secondary-800 border-secondary-200';
    default:
      return 'bg-secondary-100 text-secondary-800 border-secondary-200';
  }
}

// ============================================================================
// Chart Utilities
// ============================================================================

/**
 * Generate chart colors for pie/bar charts
 */
export function generateChartColors(count: number): string[] {
  const baseColors = [
    '#3b82f6', // blue
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
    '#ec4899', // pink
    '#06b6d4', // cyan
    '#f97316', // orange
    '#84cc16', // lime
    '#6366f1', // indigo
  ];

  const colors: string[] = [];
  for (let i = 0; i < count; i++) {
    colors.push(baseColors[i % baseColors.length]);
  }
  return colors;
}

// ============================================================================
// Storage Utilities
// ============================================================================

/**
 * LocalStorage wrapper with JSON support and error handling
 */
export const storage = {
  get<T>(key: string, defaultValue?: T): T | null {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue ?? null;
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return defaultValue ?? null;
    }
  },

  set<T>(key: string, value: T): boolean {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error('Error writing to localStorage:', error);
      return false;
    }
  },

  remove(key: string): boolean {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error('Error removing from localStorage:', error);
      return false;
    }
  },

  clear(): boolean {
    try {
      localStorage.clear();
      return true;
    } catch (error) {
      console.error('Error clearing localStorage:', error);
      return false;
    }
  },
};
