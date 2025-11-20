// API types matching the FastAPI backend schemas

export enum SignalType {
  BUY = 'BUY',
  SELL = 'SELL',
  HOLD = 'HOLD',
  STRONG_BUY = 'STRONG_BUY',
  STRONG_SELL = 'STRONG_SELL',
}

export enum AlertPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum AlertStatus {
  ACTIVE = 'active',
  ACKNOWLEDGED = 'acknowledged',
  DISMISSED = 'dismissed',
  EXPIRED = 'expired',
  RESOLVED = 'resolved',
}

// Type alias for string literal to match mock API usage
export type AlertStatusType = 'active' | 'acknowledged' | 'dismissed' | 'expired' | 'resolved';

export enum TaskStatus {
  PENDING = 'pending',
  STARTED = 'started',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  permissions: Record<string, boolean>;
  created_at: string;
  last_login?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  user?: Record<string, any>;
}

export interface TradingSignal {
  id: number;
  date: string;
  stock_code: string;
  sector?: string;
  signal_type: SignalType;
  signal: string; // For backward compatibility - should be same as signal_type
  composite_score: number;
  confidence: number;
  position_size: number;
  current_price: number;
  target_price?: number;
  company_name?: string;
  volume?: number;
  technical_score?: number;
  fundamental_score?: number;
  sentiment_score?: number;
  risk_adjusted: boolean;
  metadata?: Record<string, any>;
  generated_at: string;
}

export interface DailySignalsResponse {
  date: string;
  signals: TradingSignal[];
  generated_at?: string;
  total_signals: number;
}

export interface Position {
  id: number;
  stock_code: string;
  quantity: number;
  average_price: number;
  current_price?: number;
  sector?: string;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_percent?: number;
  position_size_percent?: number;
  last_updated: string;
}

export interface PortfolioSummary {
  total_positions: number;
  total_market_value: number;
  total_cost_basis: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_percent: number;
  sector_breakdown: Record<string, number>;
  cash_available?: number;
  portfolio_beta?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  last_updated: string;
  // Additional properties used in components
  total_value?: number;
  daily_pnl?: number;
  positions_count?: number;
}

export interface Alert {
  id: number;
  alert_type: string;
  message: string;
  priority: AlertPriority;
  status: AlertStatusType;
  stock_code?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  expires_at?: string;
}

export interface RiskMetric {
  name: string;
  current_value: number;
  limit_value: number;
  warning_threshold: number;
  critical_threshold: number;
  status: 'normal' | 'warning' | 'critical';
  description: string;
}

export interface RiskOverview {
  risk_metrics: Record<string, RiskMetric>;
  alert_counts: Record<string, number>;
  monitoring_status: string;
  last_check?: string;
  portfolio_risk_score?: number;
  // Additional properties used in components
  overall_risk_level?: string;
  value_at_risk?: number;
  beta?: number;
  diversification_score?: number;
  position_risks?: Array<{
    stock_code: string;
    risk_score: number;
    allocation_percent: number;
  }>;
  max_drawdown?: number;
  sharpe_ratio?: number;
  volatility?: number;
  correlation?: number;
  last_updated?: string;
}

export interface MarketStatus {
  is_open: boolean;
  current_time: string;
  next_open?: string;
  next_close?: string;
  session_type: string;
}

export interface PerformanceMetrics {
  period_days: number;
  total_return?: number;
  annualized_return?: number;
  volatility?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  avg_trade_return?: number;
}

export interface PerformanceAnalytics {
  period_days: number;
  total_signals: number;
  signal_type_distribution: Record<string, number>;
  avg_confidence: number;
  avg_position_size: number;
  avg_daily_signals: number;
  daily_signal_counts: Record<string, number>;
  performance_metrics?: PerformanceMetrics;
  analysis_date: string;
}

export interface WebSocketMessage {
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

export interface AIResearchReport {
  stock_code: string;
  trade_date: string;
  analyst_notes: Record<string, string>;
  debate_summary: string;
  risk_assessment: string;
  final_recommendation: string;
  conviction: number;
  timestamp: string;
}

export interface AuctionMarketProfile {
  stock_code: string;
  session_date: string;
  point_of_control: number;
  value_area_high: number;
  value_area_low: number;
  initial_balance_high?: number;
  initial_balance_low?: number;
  profile_type?: string;
  total_volume?: number;
  vwap?: number;
  session_range?: number;
  open_price?: number;
  close_price?: number;
  single_prints?: number[];
  metrics?: Record<string, any>;
}

// API Response wrapper
export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

// API Error
export interface ApiError {
  error: string;
  detail?: string;
  timestamp: string;
  request_id?: string;
}

// Performance Analytics for Dashboard
export interface PerformanceAnalytics {
  period_days: number;
  total_signals: number;
  signal_type_distribution: Record<string, number>;
  avg_confidence: number;
  avg_position_size: number;
  avg_daily_signals: number;
  daily_signal_counts: Record<string, number>;
  performance_metrics?: PerformanceMetrics;
  analysis_date: string;
}

// Settings interface
export interface Settings {
  theme: 'light' | 'dark' | 'system';
  notifications: {
    alerts: boolean;
    signals: boolean;
    portfolio: boolean;
    email: boolean;
    push: boolean;
  };
  risk: {
    maxPositionSize: number;
    maxDrawdown: number;
    stopLoss: number;
    alertThreshold: number;
  };
  trading: {
    defaultPositionSize: number;
    autoTrading: boolean;
    riskManagement: boolean;
  };
  profile: {
    name: string;
    email: string;
    phone: string;
    timezone: string;
  };
}
