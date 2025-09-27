import type {
  LoginRequest,
  TokenResponse,
  User,
  TradingSignal,
  DailySignalsResponse,
  Position,
  PortfolioSummary,
  Alert,
  RiskOverview,
  MarketStatus,
  PerformanceAnalytics,
  ApiResponse,
  ApiError,
} from '@/types/api';
import {
  ApiError as ApiErrorClass,
  AuthError,
  NetworkError,
  ValidationError
} from '@/lib/error-handler';

class ApiClient {
  private baseURL: string;
  private token: string | null = null;

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    this.token = localStorage.getItem('auth_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorData: any = {};
        try {
          errorData = await response.json();
        } catch (e) {
          errorData = { detail: response.statusText };
        }

        const errorMessage = errorData.detail || errorData.error || 'API request failed';

        if (response.status === 401) {
          this.clearAuth();
          window.location.href = '/login';
          throw new AuthError('Authentication failed', errorData);
        }

        if (response.status === 400) {
          throw new ValidationError(errorMessage, errorData);
        }

        throw new ApiErrorClass(errorMessage, response.status, errorData);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiErrorClass || error instanceof AuthError || error instanceof ValidationError) {
        throw error;
      }

      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new NetworkError('Network connection failed. Please check your internet connection.', error);
      }

      throw new NetworkError(
        error instanceof Error ? error.message : 'Network error occurred',
        error
      );
    }
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  clearAuth() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  // Authentication
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    this.setToken(response.access_token);
    return response;
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async logout(): Promise<void> {
    this.clearAuth();
  }

  // Signals
  async getDailySignals(date?: string): Promise<DailySignalsResponse> {
    const params = date ? `?date=${date}` : '';
    return this.request<DailySignalsResponse>(`/signals/daily${params}`);
  }

  async generateSignals(): Promise<{ task_id: string; status: string; message: string }> {
    return this.request('/signals/generate', {
      method: 'POST',
    });
  }

  // Portfolio
  async getPortfolioSummary(): Promise<PortfolioSummary> {
    return this.request<PortfolioSummary>('/portfolio/summary');
  }

  async getPositions(): Promise<Position[]> {
    return this.request<Position[]>('/portfolio/positions');
  }

  async updatePosition(position: {
    stock_code: string;
    quantity: number;
    average_price: number;
  }): Promise<Position> {
    return this.request<Position>('/portfolio/positions', {
      method: 'POST',
      body: JSON.stringify(position),
    });
  }

  // Alerts
  async getAlerts(params?: {
    limit?: number;
    offset?: number;
    status?: string;
    priority?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<Alert[]> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString());
        }
      });
    }

    const queryString = searchParams.toString();
    const url = `/alerts${queryString ? `?${queryString}` : ''}`;

    return this.request<Alert[]>(url);
  }

  async updateAlertStatus(
    alertId: number,
    status: string,
    notes?: string
  ): Promise<Alert> {
    return this.request<Alert>(`/alerts/${alertId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status, notes }),
    });
  }

  // Risk Management
  async getRiskOverview(): Promise<RiskOverview> {
    return this.request<RiskOverview>('/risk/overview');
  }

  // Market Data
  async getMarketStatus(): Promise<MarketStatus> {
    return this.request<MarketStatus>('/market/status');
  }

  // Analytics
  async getPerformanceAnalytics(days: number = 30): Promise<PerformanceAnalytics> {
    return this.request<PerformanceAnalytics>(`/analytics/performance?days=${days}`);
  }

  // Backtesting
  async getBacktestingPerformance(): Promise<any> {
    return this.request('/backtesting/performance');
  }

  // Health Check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request('/health');
  }
}

export const apiClient = new ApiClient();

// WebSocket connection for real-time updates
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;
  private listeners: Map<string, Function[]> = new Map();

  constructor() {
    this.connect();
  }

  private connect() {
    try {
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
      this.ws = new WebSocket(`${wsUrl}/ws/alerts`);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.notifyListeners(message.type, message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, this.reconnectInterval * this.reconnectAttempts);
    }
  }

  subscribe(eventType: string, callback: Function) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(callback);

    return () => {
      const callbacks = this.listeners.get(eventType);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }

  private notifyListeners(eventType: string, data: any) {
    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const wsClient = new WebSocketClient();