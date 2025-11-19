/**
 * Mock API Client - Frontend Development Mode
 * Provides realistic dummy data for frontend development without backend dependency
 */

import type {
  TradingSignal,
  PortfolioSummary,
  Position,
  Alert,
  RiskOverview,
  MarketStatus,
  PerformanceAnalytics,
  User,
  LoginRequest,
  TokenResponse,
  DailySignalsResponse,
  AuctionMarketProfile,
  AlertPriority,
  AlertStatus
} from '@/types/api';

// Mock configuration
const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true' || !import.meta.env.VITE_API_URL;

// Helper function to simulate API delays
const delay = (ms: number = 500) => new Promise(resolve => setTimeout(resolve, ms));

// Helper function to simulate random price movements
const randomPriceChange = (basePrice: number, volatility: number = 0.02) => {
  const change = (Math.random() - 0.5) * 2 * volatility;
  return basePrice * (1 + change);
};

// Helper function to generate realistic Indonesian stock codes
const stockCodes = [
  'BBCA', 'BBRI', 'BBNI', 'BMRI', 'TLKM', 'UNVR', 'ASII', 'INDF', 'KLBF', 'HMSP',
  'GGRM', 'HMSP', 'ADRO', 'PGAS', 'JPFA', 'CPIN', 'SMGR', 'INTP', 'ANTM', 'PTBA',
  'MDKA', 'TINS', 'SILO', 'AALI', 'IFF', 'KAEF', 'MEDC', 'PWON', 'WSBP', 'PTPP'
];

const sectors = [
  'Banking', 'Infrastructure', 'Telecommunications', 'Consumer Goods', 'Mining',
  'Energy', 'Agriculture', 'Manufacturing', 'Property', 'Healthcare'
];

// Mock user
const mockUser: User = {
  id: '1',
  username: 'demo_user',
  email: 'demo@project-aurum.com',
  role: 'trader',
  permissions: {
    view_signals: true,
    view_portfolio: true,
    manage_alerts: true,
    trade: false
  },
  created_at: '2024-01-15T10:30:00Z',
  last_login: new Date().toISOString()
};

// Mock trading signals
const generateMockSignals = (): TradingSignal[] => {
  return stockCodes.slice(0, 15).map((stockCode, index) => ({
    id: index + 1,
    date: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(),
    stock_code: stockCode,
    sector: sectors[Math.floor(Math.random() * sectors.length)],
    signal_type: ['BUY', 'SELL', 'HOLD', 'STRONG_BUY', 'STRONG_SELL'][Math.floor(Math.random() * 5)] as any,
    signal: ['BUY', 'SELL', 'HOLD', 'STRONG_BUY', 'STRONG_SELL'][Math.floor(Math.random() * 5)],
    composite_score: Math.random() * 100,
    confidence: Math.random() * 0.4 + 0.6, // 0.6 to 1.0
    position_size: Math.random() * 10000 + 1000,
    current_price: Math.random() * 5000 + 100,
    target_price: Math.random() * 5500 + 150,
    company_name: `PT ${stockCode} Indonesia Tbk`,
    volume: Math.floor(Math.random() * 1000000) + 100000,
    technical_score: Math.random() * 100,
    fundamental_score: Math.random() * 100,
    sentiment_score: Math.random() * 100,
    risk_adjusted: Math.random() > 0.5,
    metadata: {
      analyst_confidence: Math.random() * 0.3 + 0.7,
      market_cap: Math.random() * 1000000000 + 100000000,
      pe_ratio: Math.random() * 30 + 5
    },
    generated_at: new Date().toISOString()
  }));
};

// Mock portfolio summary
const generateMockPortfolio = (): PortfolioSummary => ({
  total_positions: Math.floor(Math.random() * 20) + 5,
  total_market_value: Math.random() * 500000000 + 100000000,
  total_cost_basis: Math.random() * 450000000 + 95000000,
  total_unrealized_pnl: (Math.random() - 0.3) * 100000000,
  total_unrealized_pnl_percent: (Math.random() - 0.3) * 20,
  sector_breakdown: sectors.slice(0, 6).reduce((acc, sector) => {
    acc[sector] = Math.random() * 100000000 + 10000000;
    return acc;
  }, {} as Record<string, number>),
  cash_available: Math.random() * 50000000 + 10000000,
  portfolio_beta: Math.random() * 2 + 0.5,
  sharpe_ratio: Math.random() * 2 + 0.5,
  max_drawdown: Math.random() * 20 + 5,
  last_updated: new Date().toISOString(),
  total_value: Math.random() * 500000000 + 100000000,
  daily_pnl: (Math.random() - 0.3) * 10000000,
  positions_count: Math.floor(Math.random() * 20) + 5
});

// Mock positions
const generateMockPositions = (): Position[] => {
  return stockCodes.slice(0, 12).map((stockCode, index) => ({
    id: index + 1,
    stock_code: stockCode,
    quantity: Math.floor(Math.random() * 10000) + 100,
    average_price: Math.random() * 3000 + 100,
    current_price: randomPriceChange(Math.random() * 3000 + 100),
    sector: sectors[Math.floor(Math.random() * sectors.length)],
    market_value: Math.random() * 50000000 + 5000000,
    unrealized_pnl: (Math.random() - 0.3) * 5000000,
    unrealized_pnl_percent: (Math.random() - 0.3) * 15,
    position_size_percent: Math.random() * 10 + 1,
    last_updated: new Date().toISOString()
  }));
};

// Mock alerts
const generateMockAlerts = (): Alert[] => {
  const alertTypes = ['PRICE_ALERT', 'VOLUME_SPIKE', 'RISK_LIMIT', 'MARKET_EVENT', 'SIGNAL_TRIGGER'];
  const priorities = ['critical', 'high', 'medium', 'low'] as const;
  const statuses = ['active', 'acknowledged', 'dismissed'] as const;

  return Array.from({ length: 8 }, (_, index) => ({
    id: index + 1,
    alert_type: alertTypes[Math.floor(Math.random() * alertTypes.length)],
    message: [
      'BBCA price increased by 5% in the last hour',
      'Unusual volume detected in TLKM',
      'Portfolio risk approaching maximum limit',
      'IDX Composite Index broke resistance level',
      'Strong BUY signal generated for BBRI',
      'Market volatility increased significantly',
      'Quarterly earnings beat expectations',
      'Technical indicator suggests trend reversal'
    ][index],
    priority: priorities[Math.floor(Math.random() * priorities.length)] as AlertPriority,
    status: statuses[Math.floor(Math.random() * statuses.length)],
    stock_code: stockCodes[index % stockCodes.length],
    metadata: {
      trigger_value: Math.random() * 100,
      threshold: Math.random() * 80 + 20,
      duration: Math.floor(Math.random() * 3600) + 300
    },
    created_at: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - Math.random() * 12 * 60 * 60 * 1000).toISOString(),
    acknowledged_at: Math.random() > 0.5 ? new Date(Date.now() - Math.random() * 6 * 60 * 60 * 1000).toISOString() : undefined,
    acknowledged_by: Math.random() > 0.5 ? 'demo_user' : undefined,
    expires_at: new Date(Date.now() + Math.random() * 24 * 60 * 60 * 1000).toISOString()
  }));
};

// Mock risk overview
const generateMockRiskOverview = (): RiskOverview => ({
  risk_metrics: {
    portfolio_volatility: {
      current_value: Math.random() * 0.3 + 0.1,
      limit_value: 0.25,
      warning_threshold: 0.2,
      critical_threshold: 0.24,
      status: Math.random() > 0.7 ? 'warning' : 'normal',
      description: 'Portfolio volatility measure'
    },
    value_at_risk: {
      current_value: Math.random() * 50000000 + 10000000,
      limit_value: 50000000,
      warning_threshold: 40000000,
      critical_threshold: 48000000,
      status: Math.random() > 0.6 ? 'normal' : 'warning',
      description: 'Value at Risk (95% confidence)'
    },
    beta: {
      current_value: Math.random() * 1.5 + 0.5,
      limit_value: 1.2,
      warning_threshold: 1.0,
      critical_threshold: 1.15,
      status: Math.random() > 0.5 ? 'normal' : 'warning',
      description: 'Portfolio beta relative to market'
    }
  },
  alert_counts: {
    critical: Math.floor(Math.random() * 3),
    high: Math.floor(Math.random() * 5) + 1,
    medium: Math.floor(Math.random() * 10) + 2,
    low: Math.floor(Math.random() * 15) + 3
  },
  monitoring_status: 'active',
  last_check: new Date().toISOString(),
  portfolio_risk_score: Math.random() * 100,
  overall_risk_level: ['Low', 'Medium', 'High'][Math.floor(Math.random() * 3)],
  value_at_risk: Math.random() * 50000000 + 10000000,
  beta: Math.random() * 1.5 + 0.5,
  diversification_score: Math.random() * 100,
  position_risks: stockCodes.slice(0, 5).map((code, index) => ({
    stock_code: code,
    risk_score: Math.random() * 100,
    allocation_percent: Math.random() * 20 + 2
  })),
  max_drawdown: Math.random() * 25 + 5,
  sharpe_ratio: Math.random() * 2 + 0.5,
  volatility: Math.random() * 0.3 + 0.1,
  correlation: Math.random() * 0.8 + 0.2,
  last_updated: new Date().toISOString()
});

// Mock market status
const generateMockMarketStatus = (): MarketStatus => {
  const now = new Date();
  const jakartaTime = new Date(now.toLocaleString("en-US", {timeZone: "Asia/Jakarta"}));
  const hour = jakartaTime.getHours();
  const day = jakartaTime.getDay();

  const isWeekday = day >= 1 && day <= 5;
  const isMarketHours = isWeekday && hour >= 9 && hour <= 15;
  const isLunchBreak = isWeekday && hour >= 12 && hour < 13;

  return {
    is_open: isMarketHours && !isLunchBreak,
    current_time: jakartaTime.toISOString(),
    next_open: isMarketHours ?
      jakartaTime.toDateString() + ' 09:00:00' :
      jakartaTime.toDateString() + ' 09:00:00',
    next_close: isMarketHours ?
      jakartaTime.toDateString() + ' 15:50:00' :
      jakartaTime.toDateString() + ' 15:50:00',
    session_type: isLunchBreak ? 'lunch_break' : isMarketHours ? 'trading' : 'closed'
  };
};

// Mock performance analytics
const generateMockPerformanceAnalytics = (): PerformanceAnalytics => ({
  period_days: 30,
  total_signals: Math.floor(Math.random() * 500) + 100,
  signal_type_distribution: {
    'BUY': Math.floor(Math.random() * 200) + 50,
    'SELL': Math.floor(Math.random() * 150) + 30,
    'HOLD': Math.floor(Math.random() * 100) + 20,
    'STRONG_BUY': Math.floor(Math.random() * 80) + 15,
    'STRONG_SELL': Math.floor(Math.random() * 60) + 10
  },
  avg_confidence: Math.random() * 0.3 + 0.7,
  avg_position_size: Math.random() * 5000 + 1000,
  avg_daily_signals: Math.floor(Math.random() * 20) + 5,
  daily_signal_counts: Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    count: Math.floor(Math.random() * 25) + 5
  })).reduce((acc, day) => {
    acc[day.date] = day.count;
    return acc;
  }, {} as Record<string, number>),
  performance_metrics: {
    period_days: 30,
    total_return: (Math.random() - 0.2) * 0.2, // -20% to +20%
    annualized_return: (Math.random() - 0.1) * 0.5,
    volatility: Math.random() * 0.3 + 0.1,
    sharpe_ratio: Math.random() * 2 + 0.5,
    max_drawdown: Math.random() * 20 + 5,
    win_rate: Math.random() * 0.4 + 0.4, // 40% to 80%
    avg_trade_return: (Math.random() - 0.1) * 0.1 // -10% to +10%
  },
  analysis_date: new Date().toISOString()
});

// Mock auction market profiles
const generateMockAuctionProfiles = (): AuctionMarketProfile[] => {
  return stockCodes.slice(0, 10).map((stockCode, index) => ({
    stock_code: stockCode,
    session_date: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    point_of_control: Math.random() * 5000 + 100,
    value_area_high: Math.random() * 5500 + 150,
    value_area_low: Math.random() * 4500 + 50,
    initial_balance_high: Math.random() * 5200 + 120,
    initial_balance_low: Math.random() * 4800 + 80,
    profile_type: ['normal', 'trend', 'balanced'][Math.floor(Math.random() * 3)],
    total_volume: Math.floor(Math.random() * 5000000) + 500000,
    vwap: Math.random() * 5000 + 100,
    session_range: Math.random() * 200 + 50,
    open_price: Math.random() * 5000 + 100,
    close_price: Math.random() * 5000 + 100,
    single_prints: Array.from({ length: Math.floor(Math.random() * 5) }, (_, i) =>
      Math.random() * 5000 + 100
    ),
    metrics: {
      profile_height: Math.random() * 1000 + 200,
      range_extension: Math.random() * 0.3,
      tpo_count: Math.floor(Math.random() * 50) + 10
    }
  }));
};

// Mock API Client Class
class MockApiClient {
  private mockSignals: TradingSignal[] = generateMockSignals();
  private mockPortfolio: PortfolioSummary = generateMockPortfolio();
  private mockPositions: Position[] = generateMockPositions();
  private mockAlerts: Alert[] = generateMockAlerts();
  private mockRiskOverview: RiskOverview = generateMockRiskOverview();
  private mockPerformanceAnalytics: PerformanceAnalytics = generateMockPerformanceAnalytics();

  // Simulate real-time data updates
  private startRealTimeSimulation() {
    setInterval(() => {
      // Update prices
      this.mockSignals.forEach(signal => {
        signal.current_price = randomPriceChange(signal.current_price);
        signal.confidence = Math.max(0.5, Math.min(1.0, signal.confidence + (Math.random() - 0.5) * 0.05));
      });

      // Update portfolio
      this.mockPortfolio.total_unrealized_pnl = (Math.random() - 0.3) * 100000000;
      this.mockPortfolio.total_unrealized_pnl_percent = (Math.random() - 0.3) * 20;
      this.mockPortfolio.last_updated = new Date().toISOString();

      // Update positions
      this.mockPositions.forEach(position => {
        position.current_price = randomPriceChange(position.current_price);
        position.market_value = position.quantity * position.current_price;
        position.unrealized_pnl = (position.current_price - position.average_price) * position.quantity;
        position.unrealized_pnl_percent = ((position.current_price - position.average_price) / position.average_price) * 100;
        position.last_updated = new Date().toISOString();
      });

      // Occasionally add new alerts
      if (Math.random() < 0.1) {
        const newAlert: Alert = {
          id: this.mockAlerts.length + 1,
          alert_type: 'SIGNAL_TRIGGER',
          message: `New signal for ${stockCodes[Math.floor(Math.random() * stockCodes.length)]}`,
          priority: ['high', 'medium', 'low'][Math.floor(Math.random() * 3)] as any,
          status: 'active',
          stock_code: stockCodes[Math.floor(Math.random() * stockCodes.length)],
          metadata: {},
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
        };
        this.mockAlerts.unshift(newAlert);
        if (this.mockAlerts.length > 10) {
          this.mockAlerts.pop();
        }
      }
    }, 5000); // Update every 5 seconds
  }

  constructor() {
    this.startRealTimeSimulation();
  }

  // Authentication endpoints
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    await delay(800);

    if (credentials.username === 'demo' && credentials.password === 'demo') {
      return {
        access_token: 'mock_access_token_' + Math.random().toString(36).substr(2, 9),
        refresh_token: 'mock_refresh_token_' + Math.random().toString(36).substr(2, 9),
        token_type: 'Bearer',
        expires_in: 3600,
        user: mockUser
      };
    }

    throw new Error('Invalid credentials. Use demo/demo');
  }

  async refreshToken(token: string): Promise<TokenResponse> {
    await delay(300);

    return {
      access_token: 'mock_access_token_' + Math.random().toString(36).substr(2, 9),
      refresh_token: 'mock_refresh_token_' + Math.random().toString(36).substr(2, 9),
      token_type: 'Bearer',
      expires_in: 3600,
      user: mockUser
    };
  }

  // Trading signals endpoints
  async getSignals(date?: string): Promise<DailySignalsResponse> {
    await delay(600);

    const targetDate = date || new Date().toISOString().split('T')[0];
    return {
      date: targetDate,
      signals: this.mockSignals,
      generated_at: new Date().toISOString(),
      total_signals: this.mockSignals.length
    };
  }

  async getSignalById(signalId: number): Promise<TradingSignal> {
    await delay(300);

    const signal = this.mockSignals.find(s => s.id === signalId);
    if (!signal) {
      throw new Error('Signal not found');
    }
    return signal;
  }

  // Portfolio endpoints
  async getPortfolio(): Promise<PortfolioSummary> {
    await delay(400);
    return this.mockPortfolio;
  }

  async getPositions(): Promise<Position[]> {
    await delay(500);
    return this.mockPositions;
  }

  async updatePosition(positionId: number, updates: Partial<Position>): Promise<Position> {
    await delay(600);

    const positionIndex = this.mockPositions.findIndex(p => p.id === positionId);
    if (positionIndex === -1) {
      throw new Error('Position not found');
    }

    this.mockPositions[positionIndex] = { ...this.mockPositions[positionIndex], ...updates };
    return this.mockPositions[positionIndex];
  }

  // Alerts endpoints
  async getAlerts(): Promise<Alert[]> {
    await delay(300);
    return this.mockAlerts;
  }

  async acknowledgeAlert(alertId: number): Promise<void> {
    await delay(400);

    const alert = this.mockAlerts.find(a => a.id === alertId);
    if (alert) {
      alert.status = 'acknowledged';
      alert.acknowledged_at = new Date().toISOString();
      alert.acknowledged_by = mockUser.username;
    }
  }

  async dismissAlert(alertId: number): Promise<void> {
    await delay(300);

    const alertIndex = this.mockAlerts.findIndex(a => a.id === alertId);
    if (alertIndex !== -1) {
      this.mockAlerts[alertIndex].status = 'dismissed';
    }
  }

  // Risk management endpoints
  async getRiskOverview(): Promise<RiskOverview> {
    await delay(500);
    return this.mockRiskOverview;
  }

  // Market data endpoints
  async getMarketStatus(): Promise<MarketStatus> {
    await delay(200);
    return generateMockMarketStatus();
  }

  // Analytics endpoints
  async getPerformanceAnalytics(days: number = 30): Promise<PerformanceAnalytics> {
    await delay(700);
    return { ...this.mockPerformanceAnalytics, period_days: days };
  }

  async getBacktestingPerformance(strategy: string, startDate: string, endDate: string): Promise<any> {
    await delay(1000);

    return {
      strategy,
      period: { startDate, endDate },
      total_return: (Math.random() - 0.2) * 0.5,
      sharpe_ratio: Math.random() * 2 + 0.5,
      max_drawdown: Math.random() * 20 + 5,
      win_rate: Math.random() * 0.4 + 0.4,
      total_trades: Math.floor(Math.random() * 500) + 100,
      monthly_performance: Array.from({ length: 12 }, (_, i) => ({
        month: new Date(2024, i, 1).toLocaleString('default', { month: 'short' }),
        return: (Math.random() - 0.2) * 0.15
      }))
    };
  }

  // Auction market profile endpoints
  async getAuctionMarketProfiles(date: string): Promise<AuctionMarketProfile[]> {
    await delay(600);
    return generateMockAuctionProfiles();
  }

  // Additional methods expected by the stores
  async getCurrentUser(): Promise<User> {
    await delay(200);
    return mockUser;
  }

  async logout(): Promise<void> {
    await delay(200);
    // Mock logout - just clear the token
    console.log('Mock logout completed');
  }

  async clearAuth(): Promise<void> {
    await delay(100);
    // Mock clear auth
    console.log('Mock auth cleared');
  }

  async getDailySignals(date?: string): Promise<DailySignalsResponse> {
    await delay(600);
    const targetDate = date || new Date().toISOString().split('T')[0];
    return {
      date: targetDate,
      signals: this.mockSignals,
      generated_at: new Date().toISOString(),
      total_signals: this.mockSignals.length
    };
  }

  async getPortfolioSummary(): Promise<PortfolioSummary> {
    await delay(400);
    return this.mockPortfolio;
  }

  async updateAlertStatus(alertId: number, status: AlertStatus, notes?: string): Promise<Alert> {
    await delay(600);

    const alert = this.mockAlerts.find(a => a.id === alertId);
    if (alert) {
      alert.status = status;
      alert.updated_at = new Date().toISOString();
    }

    if (!alert) {
      throw new Error('Alert not found');
    }

    return alert;
  }

  async addPosition(position: Omit<Position, 'id' | 'last_updated'>): Promise<Position> {
    await delay(600);

    const newPosition: Position = {
      ...position,
      id: Math.max(...this.mockPositions.map(p => p.id)) + 1,
      last_updated: new Date().toISOString()
    };

    this.mockPositions.push(newPosition);
    return newPosition;
  }
}

// WebSocket Mock Client
class MockWebSocketClient {
  private subscribers: Map<string, ((data: any) => void)[]> = new Map();
  private intervalId: number | null = null;

  subscribe(eventType: string, callback: (data: any) => void): () => void {
    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, []);
    }

    this.subscribers.get(eventType)!.push(callback);

    // Start real-time updates if not already running
    if (!this.intervalId) {
      this.startRealTimeUpdates();
    }

    // Return unsubscribe function
    return () => {
      const callbacks = this.subscribers.get(eventType);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }

  private startRealTimeUpdates() {
    this.intervalId = window.setInterval(() => {
      // Emit real-time updates
      this.emit('signal_update', {
        type: 'signal_update',
        data: {
          id: Math.floor(Math.random() * 15) + 1,
          confidence: Math.random() * 0.4 + 0.6,
          current_price: Math.random() * 5000 + 100
        },
        timestamp: new Date().toISOString()
      });

      this.emit('portfolio_update', {
        type: 'portfolio_update',
        data: {
          total_unrealized_pnl: (Math.random() - 0.3) * 100000000,
          total_unrealized_pnl_percent: (Math.random() - 0.3) * 20
        },
        timestamp: new Date().toISOString()
      });

      this.emit('alert', {
        type: 'alert',
        data: {
          id: Math.floor(Math.random() * 1000) + 1,
          message: `Real-time update: ${['Price movement detected', 'Volume spike alert', 'Risk threshold warning'][Math.floor(Math.random() * 3)]}`,
          priority: ['high', 'medium', 'low'][Math.floor(Math.random() * 3)]
        },
        timestamp: new Date().toISOString()
      });
    }, 3000); // Update every 3 seconds
  }

  private emit(eventType: string, data: any) {
    const callbacks = this.subscribers.get(eventType);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }

  disconnect() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.subscribers.clear();
  }
}

// Export instances
export const mockApiClient = new MockApiClient();
export const mockWebSocketClient = new MockWebSocketClient();

// Detect if we should use mock API
export const useMockApi = (): boolean => {
  return MOCK_MODE || import.meta.env.DEV;
};

export default mockApiClient;