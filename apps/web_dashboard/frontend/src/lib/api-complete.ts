/**
 * Complete API Client Library
 * Provides type-safe methods for all backend endpoints
 */

import type {
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
  AIResearchReport,
  AuctionMarketProfile
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.token = localStorage.getItem('access_token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('access_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('access_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: 'Unknown error occurred'
      }));
      throw new ApiError(response.status, error.detail || error.message);
    }

    return response.json();
  }

  // ==========================================================================
  // AUTHENTICATION
  // ==========================================================================

  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    if (response.access_token) {
      this.setToken(response.access_token);
    }

    return response;
  }

  async logout() {
    this.clearToken();
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // ==========================================================================
  // MARKET DATA
  // ==========================================================================

  async getMarketStatus(): Promise<MarketStatus> {
    return this.request<MarketStatus>('/market/status');
  }

  async getMarketSnapshot(): Promise<any> {
    return this.request('/market/snapshot');
  }

  async getMarketIndices(): Promise<any> {
    return this.request('/market/indices');
  }

  async getSectorPerformance(days: number = 30): Promise<any> {
    return this.request(`/market/sectors?days=${days}`);
  }

  // ==========================================================================
  // SIGNALS
  // ==========================================================================

  async getDailySignals(date?: string): Promise<DailySignalsResponse> {
    const params = date ? `?date=${date}` : '';
    return this.request<DailySignalsResponse>(`/signals/daily${params}`);
  }

  async generateSignals(): Promise<any> {
    return this.request('/signals/generate', {
      method: 'POST',
    });
  }

  async getGenerationStatus(taskId: string): Promise<any> {
    return this.request(`/signals/generation/${taskId}`);
  }

  // ==========================================================================
  // PORTFOLIO
  // ==========================================================================

  async getPortfolioSummary(): Promise<PortfolioSummary> {
    return this.request<PortfolioSummary>('/portfolio/summary');
  }

  async getPositions(): Promise<Position[]> {
    return this.request<Position[]>('/portfolio/positions');
  }

  async updatePosition(
    stockCode: string,
    quantity: number,
    averagePrice: number
  ): Promise<Position> {
    return this.request<Position>(`/portfolio/positions/${stockCode}`, {
      method: 'PUT',
      body: JSON.stringify({
        stock_code: stockCode,
        quantity,
        average_price: averagePrice,
      }),
    });
  }

  // ==========================================================================
  // ALERTS
  // ==========================================================================

  async getAlerts(params: {
    limit?: number;
    offset?: number;
    status?: string;
    priority?: string;
  } = {}): Promise<Alert[]> {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        queryParams.append(key, value.toString());
      }
    });

    const query = queryParams.toString() ? `?${queryParams}` : '';
    return this.request<Alert[]>(`/alerts${query}`);
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

  // ==========================================================================
  // RISK MANAGEMENT
  // ==========================================================================

  async getRiskOverview(): Promise<RiskOverview> {
    return this.request<RiskOverview>('/risk/overview');
  }

  async getRiskAlerts(limit: number = 20): Promise<any[]> {
    return this.request<any[]>(`/risk/alerts?limit=${limit}`);
  }

  // ==========================================================================
  // ANALYTICS
  // ==========================================================================

  async getPerformanceAnalytics(days: number = 30): Promise<PerformanceAnalytics> {
    return this.request<PerformanceAnalytics>(`/analytics/performance?days=${days}`);
  }

  async getStockAnalytics(stockCode: string, days: number = 30): Promise<any> {
    return this.request(`/analytics/stock/${stockCode}?days=${days}`);
  }

  async getBacktestingPerformance(): Promise<{ performance: any }> {
    return this.request('/backtesting/performance');
  }

  // ==========================================================================
  // AI RESEARCH
  // ==========================================================================

  async runAiResearch(
    stockCode: string,
    params: { tradeDate?: string; notes?: string } = {}
  ): Promise<AIResearchReport> {
    const query = new URLSearchParams();
    if (params.tradeDate) {
      query.append('trade_date', params.tradeDate);
    }
    if (params.notes) {
      query.append('notes', params.notes);
    }
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return this.request<AIResearchReport>(`/ai/research/${stockCode}${suffix}`, {
      method: 'POST'
    });
  }

  // ==========================================================================
  // AUCTION MARKET THEORY
  // ==========================================================================

  async getAuctionMarketProfiles(
    stockCode: string,
    limit: number = 10
  ): Promise<AuctionMarketProfile[]> {
    return this.request<AuctionMarketProfile[]>(`/market/amt/${stockCode}?limit=${limit}`);
  }

  async getAuctionMarketProfileByDate(
    stockCode: string,
    sessionDate: string
  ): Promise<AuctionMarketProfile> {
    return this.request<AuctionMarketProfile>(`/market/amt/${stockCode}/${sessionDate}`);
  }

  // ==========================================================================
  // DATA QUALITY
  // ==========================================================================

  async getDataQuality(): Promise<any> {
    return this.request('/data/quality');
  }

  async getAvailableStocks(activeOnly: boolean = true): Promise<any> {
    return this.request(`/data/stocks?active_only=${activeOnly}`);
  }

  // ==========================================================================
  // HEALTH
  // ==========================================================================

  async healthCheck(): Promise<any> {
    return this.request('/health');
  }

  async detailedHealthCheck(): Promise<any> {
    return this.request('/health/detailed');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing
export { ApiClient, ApiError };
