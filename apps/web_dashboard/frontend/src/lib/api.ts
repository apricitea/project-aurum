import type {
  TradingSignal,
  DailySignalsResponse,
  PortfolioSummary,
  Position,
  Alert,
  RiskOverview,
  MarketStatus,
  PerformanceAnalytics,
  LoginRequest,
  TokenResponse,
  User,
  WebSocketMessage,
} from '@/types/api';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws';

// ============================================================================
// API Client
// ============================================================================

class ApiClient {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    this.loadAuthToken();
  }

  private loadAuthToken(): void {
    this.authToken = localStorage.getItem('auth_token');
  }

  private saveAuthToken(token: string): void {
    this.authToken = token;
    localStorage.setItem('auth_token', token);
  }

  public clearAuth(): void {
    this.authToken = null;
    localStorage.removeItem('auth_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    // Merge with any provided headers
    if (options.headers) {
      Object.assign(headers, options.headers);
    }

    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.clearAuth();
          throw new Error('Authentication failed. Please log in again.');
        }

        if (response.status === 404) {
          throw new Error(
            'API endpoint not found. Please ensure the backend server is running on http://localhost:8000'
          );
        }

        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || errorData.error || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // ============================================================================
  // Authentication
  // ============================================================================

  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    if (response.access_token) {
      this.saveAuthToken(response.access_token);
    }

    return response;
  }

  logout(): void {
    this.clearAuth();
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // ============================================================================
  // Trading Signals
  // ============================================================================

  async getDailySignals(date?: string): Promise<DailySignalsResponse> {
    const params = date ? `?date=${date}` : '';
    return this.request<DailySignalsResponse>(`/signals/daily${params}`);
  }

  async getSignalById(signalId: number): Promise<TradingSignal> {
    return this.request<TradingSignal>(`/signals/${signalId}`);
  }

  // ============================================================================
  // Portfolio
  // ============================================================================

  async getPortfolioSummary(): Promise<PortfolioSummary> {
    return this.request<PortfolioSummary>('/portfolio/summary');
  }

  async getPositions(): Promise<Position[]> {
    return this.request<Position[]>('/portfolio/positions');
  }

  async addPosition(position: Partial<Position>): Promise<Position> {
    return this.request<Position>('/portfolio/positions', {
      method: 'POST',
      body: JSON.stringify(position),
    });
  }

  async updatePosition(positionId: number, updates: Partial<Position>): Promise<Position> {
    return this.request<Position>(`/portfolio/positions/${positionId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deletePosition(positionId: number): Promise<void> {
    return this.request<void>(`/portfolio/positions/${positionId}`, {
      method: 'DELETE',
    });
  }

  // ============================================================================
  // Alerts
  // ============================================================================

  async getAlerts(params: {
    limit?: number;
    status?: string;
    priority?: string
  } = {}): Promise<Alert[]> {
    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.set('limit', params.limit.toString());
    if (params.status) queryParams.set('status', params.status);
    if (params.priority) queryParams.set('priority', params.priority);

    const query = queryParams.toString();
    return this.request<Alert[]>(`/alerts${query ? `?${query}` : ''}`);
  }

  async getAlertById(alertId: number): Promise<Alert> {
    return this.request<Alert>(`/alerts/${alertId}`);
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

  async dismissAlert(alertId: number): Promise<Alert> {
    return this.updateAlertStatus(alertId, 'dismissed');
  }

  // ============================================================================
  // Risk Management
  // ============================================================================

  async getRiskOverview(): Promise<RiskOverview> {
    return this.request<RiskOverview>('/risk/overview');
  }

  // ============================================================================
  // Market Data
  // ============================================================================

  async getMarketStatus(): Promise<MarketStatus> {
    return this.request<MarketStatus>('/market/status');
  }

  // ============================================================================
  // Performance Analytics
  // ============================================================================

  async getPerformanceAnalytics(days: number = 30): Promise<PerformanceAnalytics> {
    return this.request<PerformanceAnalytics>(`/analytics/performance?days=${days}`);
  }

  // ============================================================================
  // Backtesting
  // ============================================================================

  async runBacktest(params: {
    start_date: string;
    end_date: string;
    strategy_config?: Record<string, any>;
  }): Promise<any> {
    return this.request('/backtest/run', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getBacktestResults(backtestId: string): Promise<any> {
    return this.request(`/backtest/results/${backtestId}`);
  }
}

// ============================================================================
// WebSocket Client
// ============================================================================

type WebSocketEventHandler = (message: WebSocketMessage) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private eventHandlers: Map<string, Set<WebSocketEventHandler>> = new Map();

  constructor(url: string) {
    this.url = url;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    try {
      const token = localStorage.getItem('auth_token');
      const wsUrl = token ? `${this.url}?token=${token}` : this.url;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.eventHandlers.clear();
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
  }

  private handleMessage(message: WebSocketMessage): void {
    const handlers = this.eventHandlers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => handler(message));
    }

    // Also trigger wildcard handlers
    const wildcardHandlers = this.eventHandlers.get('*');
    if (wildcardHandlers) {
      wildcardHandlers.forEach(handler => handler(message));
    }
  }

  on(eventType: string, handler: WebSocketEventHandler): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType)!.add(handler);
  }

  off(eventType: string, handler: WebSocketEventHandler): void {
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// ============================================================================
// Export singleton instances
// ============================================================================

export const apiClient = new ApiClient(API_BASE_URL);
export const wsClient = new WebSocketClient(WS_BASE_URL);
