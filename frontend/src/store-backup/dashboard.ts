import { create } from 'zustand';
import type {
  TradingSignal,
  DailySignalsResponse,
  Position,
  PortfolioSummary,
  Alert,
  RiskOverview,
  MarketStatus,
  PerformanceAnalytics,
} from '@/types/api';
import { apiClient, wsClient } from '@/lib/api';

interface DashboardState {
  // Data
  dailySignals: TradingSignal[];
  topSignals: TradingSignal[];
  portfolio: PortfolioSummary | null;
  positions: Position[];
  alerts: Alert[];
  riskOverview: RiskOverview | null;
  marketStatus: MarketStatus | null;
  performanceAnalytics: PerformanceAnalytics | null;

  // UI State
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;

  // Actions
  loadDashboardData: () => Promise<void>;
  loadDailySignals: (date?: string) => Promise<void>;
  loadPortfolio: () => Promise<void>;
  loadAlerts: () => Promise<void>;
  loadRiskOverview: () => Promise<void>;
  loadMarketStatus: () => Promise<void>;
  loadPerformanceAnalytics: (days?: number) => Promise<void>;

  updatePosition: (position: { stock_code: string; quantity: number; average_price: number }) => Promise<void>;
  acknowledgeAlert: (alertId: number, notes?: string) => Promise<void>;
  dismissAlert: (alertId: number, notes?: string) => Promise<void>;

  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  // Initial state
  dailySignals: [],
  topSignals: [],
  portfolio: null,
  positions: [],
  alerts: [],
  riskOverview: null,
  marketStatus: null,
  performanceAnalytics: null,
  isLoading: false,
  error: null,
  lastUpdated: null,

  // Actions
  loadDashboardData: async () => {
    set({ isLoading: true, error: null });

    try {
      await Promise.all([
        get().loadDailySignals(),
        get().loadPortfolio(),
        get().loadAlerts(),
        get().loadRiskOverview(),
        get().loadMarketStatus(),
        get().loadPerformanceAnalytics(),
      ]);

      set({
        isLoading: false,
        lastUpdated: new Date(),
        error: null,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load dashboard data',
      });
    }
  },

  loadDailySignals: async (date?: string) => {
    try {
      const response = await apiClient.getDailySignals(date);
      const signals = response.signals || [];

      // Sort by composite score and get top signals
      const sortedSignals = [...signals].sort((a, b) =>
        Math.abs(b.composite_score) - Math.abs(a.composite_score)
      );

      const topSignals = sortedSignals.slice(0, 10);

      set({
        dailySignals: signals,
        topSignals,
        error: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load signals',
      });
    }
  },

  loadPortfolio: async () => {
    try {
      const [portfolio, positions] = await Promise.all([
        apiClient.getPortfolioSummary(),
        apiClient.getPositions(),
      ]);

      set({
        portfolio,
        positions,
        error: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load portfolio',
      });
    }
  },

  loadAlerts: async () => {
    try {
      const alerts = await apiClient.getAlerts({
        limit: 50,
        status: 'active',
      });

      set({
        alerts,
        error: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load alerts',
      });
    }
  },

  loadRiskOverview: async () => {
    try {
      const riskOverview = await apiClient.getRiskOverview();

      set({
        riskOverview,
        error: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load risk overview',
      });
    }
  },

  loadMarketStatus: async () => {
    try {
      const marketStatus = await apiClient.getMarketStatus();

      set({
        marketStatus,
        error: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load market status',
      });
    }
  },

  loadPerformanceAnalytics: async (days: number = 30) => {
    try {
      const performanceAnalytics = await apiClient.getPerformanceAnalytics(days);

      set({
        performanceAnalytics,
        error: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load performance analytics',
      });
    }
  },

  updatePosition: async (position) => {
    try {
      const updatedPosition = await apiClient.updatePosition(position);

      set((state) => ({
        positions: state.positions.map((p) =>
          p.stock_code === updatedPosition.stock_code ? updatedPosition : p
        ),
        error: null,
      }));

      // Reload portfolio summary to update totals
      await get().loadPortfolio();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update position',
      });
    }
  },

  acknowledgeAlert: async (alertId: number, notes?: string) => {
    try {
      await apiClient.updateAlertStatus(alertId, 'acknowledged', notes);

      set((state) => ({
        alerts: state.alerts.filter((alert) => alert.id !== alertId),
        error: null,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to acknowledge alert',
      });
    }
  },

  dismissAlert: async (alertId: number, notes?: string) => {
    try {
      await apiClient.updateAlertStatus(alertId, 'dismissed', notes);

      set((state) => ({
        alerts: state.alerts.filter((alert) => alert.id !== alertId),
        error: null,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to dismiss alert',
      });
    }
  },

  clearError: () => {
    set({ error: null });
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },
}));

// Set up WebSocket listeners for real-time updates
wsClient.subscribe('alert_update', (data: any) => {
  const store = useDashboardStore.getState();
  store.loadAlerts();
});

wsClient.subscribe('signal_update', (data: any) => {
  const store = useDashboardStore.getState();
  store.loadDailySignals();
});

wsClient.subscribe('portfolio_update', (data: any) => {
  const store = useDashboardStore.getState();
  store.loadPortfolio();
});

wsClient.subscribe('risk_update', (data: any) => {
  const store = useDashboardStore.getState();
  store.loadRiskOverview();
});