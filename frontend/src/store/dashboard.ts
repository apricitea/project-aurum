import { create } from 'zustand';
import type {
  TradingSignal,
  PortfolioSummary,
  Position,
  Alert,
  RiskOverview,
  MarketStatus,
  PerformanceAnalytics
} from '../types/api';
import { apiClient } from '../lib/api';

interface DashboardState {
  // Data
  signals: TradingSignal[];
  portfolio: PortfolioSummary | null;
  positions: Position[];
  alerts: Alert[];
  riskOverview: RiskOverview | null;
  marketStatus: MarketStatus | null;
  performance: PerformanceAnalytics | null;

  // Loading states
  isLoading: boolean;
  isLoadingSignals: boolean;
  isLoadingPortfolio: boolean;
  isLoadingPositions: boolean;
  isLoadingAlerts: boolean;
  isLoadingRisk: boolean;
  isLoadingMarket: boolean;
  isLoadingPerformance: boolean;

  // Error and status
  error: string | null;
  lastUpdated: string | null;
  topSignals: TradingSignal[];

  // Actions
  loadDashboardData: () => Promise<void>;
  fetchSignals: () => Promise<void>;
  fetchPortfolio: () => Promise<void>;
  fetchPositions: () => Promise<void>;
  fetchAlerts: () => Promise<void>;
  fetchRiskOverview: () => Promise<void>;
  fetchMarketStatus: () => Promise<void>;
  fetchPerformance: (days?: number) => Promise<void>;
  updateAlertStatus: (alertId: number, status: string, notes?: string) => Promise<void>;
  clearError: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  // Initial state
  signals: [],
  portfolio: null,
  positions: [],
  alerts: [],
  riskOverview: null,
  marketStatus: null,
  performance: null,

  // Loading states
  isLoading: false,
  isLoadingSignals: false,
  isLoadingPortfolio: false,
  isLoadingPositions: false,
  isLoadingAlerts: false,
  isLoadingRisk: false,
  isLoadingMarket: false,
  isLoadingPerformance: false,

  // Error and status
  error: null,
  lastUpdated: null,
  topSignals: [],

  // Actions
  fetchSignals: async () => {
    set({ isLoadingSignals: true });
    try {
      const data = await apiClient.getDailySignals();
      set({ signals: data.signals || [], isLoadingSignals: false });
    } catch (error) {
      console.error('Failed to fetch signals:', error);
      set({ isLoadingSignals: false });
    }
  },

  fetchPortfolio: async () => {
    set({ isLoadingPortfolio: true });
    try {
      const data = await apiClient.getPortfolioSummary();
      set({ portfolio: data, isLoadingPortfolio: false });
    } catch (error) {
      console.error('Failed to fetch portfolio:', error);
      set({ isLoadingPortfolio: false });
    }
  },

  fetchPositions: async () => {
    set({ isLoadingPositions: true });
    try {
      const data = await apiClient.getPositions();
      set({ positions: data, isLoadingPositions: false });
    } catch (error) {
      console.error('Failed to fetch positions:', error);
      set({ isLoadingPositions: false });
    }
  },

  fetchAlerts: async () => {
    set({ isLoadingAlerts: true });
    try {
      const data = await apiClient.getAlerts({ limit: 20 });
      set({ alerts: data, isLoadingAlerts: false });
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
      set({ isLoadingAlerts: false });
    }
  },

  fetchRiskOverview: async () => {
    set({ isLoadingRisk: true });
    try {
      const data = await apiClient.getRiskOverview();
      set({ riskOverview: data, isLoadingRisk: false });
    } catch (error) {
      console.error('Failed to fetch risk overview:', error);
      set({ isLoadingRisk: false });
    }
  },

  fetchMarketStatus: async () => {
    set({ isLoadingMarket: true });
    try {
      const data = await apiClient.getMarketStatus();
      set({ marketStatus: data, isLoadingMarket: false });
    } catch (error) {
      console.error('Failed to fetch market status:', error);
      set({ isLoadingMarket: false });
    }
  },

  fetchPerformance: async (days = 30) => {
    set({ isLoadingPerformance: true });
    try {
      const data = await apiClient.getPerformanceAnalytics(days);
      set({ performance: data, isLoadingPerformance: false });
    } catch (error) {
      console.error('Failed to fetch performance:', error);
      set({ isLoadingPerformance: false });
    }
  },

  updateAlertStatus: async (alertId: number, status: string, notes?: string) => {
    try {
      const updatedAlert = await apiClient.updateAlertStatus(alertId, status, notes);
      const alerts = get().alerts.map(alert =>
        alert.id === alertId ? updatedAlert : alert
      );
      set({ alerts });
    } catch (error) {
      console.error('Failed to update alert status:', error);
    }
  },

  loadDashboardData: async () => {
    set({ isLoading: true, error: null });
    try {
      // Load all dashboard data in parallel
      await Promise.all([
        get().fetchSignals(),
        get().fetchPortfolio(),
        get().fetchPositions(),
        get().fetchAlerts(),
        get().fetchRiskOverview(),
        get().fetchMarketStatus(),
        get().fetchPerformance()
      ]);

      // Update topSignals and lastUpdated
      const signals = get().signals;
      const topSignals = signals
        .filter(signal => signal.signal === 'BUY' || signal.signal === 'SELL')
        .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
        .slice(0, 5);

      set({
        topSignals,
        lastUpdated: new Date().toISOString(),
        isLoading: false
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      set({
        error: error instanceof Error ? error.message : 'Failed to load dashboard data',
        isLoading: false
      });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));