import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, AlertTriangle, TrendingUp, Activity } from 'lucide-react';
import { useDashboardStore } from '@/store/dashboard';
import PortfolioOverview from '@/components/dashboard/PortfolioOverview';
import TradingSignals from '@/components/dashboard/TradingSignals';
import MarketOverview from '@/components/dashboard/MarketOverview';
import AlertsPanel from '@/components/dashboard/AlertsPanel';
import PerformanceChart from '@/components/dashboard/PerformanceChart';
import RealTimeUpdates from '@/components/dashboard/RealTimeUpdates';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { formatDateTime } from '@/lib/utils';

const Dashboard: React.FC = () => {
  const {
    loadDashboardData,
    isLoading,
    error,
    lastUpdated,
    marketStatus,
    alerts,
    topSignals,
    portfolio,
    riskOverview,
    clearError,
  } = useDashboardStore();

  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Auto-refresh every 30 seconds during market hours
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      if (marketStatus?.is_open) {
        loadDashboardData();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [autoRefresh, marketStatus?.is_open, loadDashboardData]);

  const handleRefresh = () => {
    loadDashboardData();
  };

  const criticalAlerts = alerts.filter(alert => alert.priority === 'critical').length;
  const highAlerts = alerts.filter(alert => alert.priority === 'high').length;

  return (
    <div className="space-y-6">
      {/* Header with Market Status and Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900 mb-2">
            Trading Dashboard
          </h1>
          <div className="flex items-center gap-4 text-sm text-secondary-600">
            {marketStatus && (
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  marketStatus.is_open ? 'bg-success-500' : 'bg-danger-500'
                }`} />
                <span>
                  Market {marketStatus.is_open ? 'Open' : 'Closed'} • {marketStatus.session_type}
                </span>
              </div>
            )}
            {lastUpdated && (
              <span>Last updated: {formatDateTime(lastUpdated)}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {(criticalAlerts > 0 || highAlerts > 0) && (
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-warning-500" />
              <span className="text-sm text-secondary-600">
                {criticalAlerts} critical, {highAlerts} high alerts
              </span>
            </div>
          )}
          
          <Button
            variant={autoRefresh ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Activity className={`h-4 w-4 mr-2 ${
              autoRefresh ? 'animate-pulse' : ''
            }`} />
            Auto-refresh
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${
              isLoading ? 'animate-spin' : ''
            }`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-danger-50 border border-danger-200 rounded-lg p-4"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-danger-500" />
              <p className="text-danger-700">{error}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={clearError}>
              Dismiss
            </Button>
          </div>
        </motion.div>
      )}

      {/* Top Summary Section - Quick Stats & Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Compact Quick Stats */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4" />
              Quick Stats
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3">
            <div className="grid grid-cols-2 gap-2">
              <div className="text-center p-2 rounded-lg bg-primary-50">
                <p className="text-lg font-bold text-primary-900 mb-1">
                  {topSignals.length}
                </p>
                <p className="text-xs text-primary-600">Signals</p>
              </div>
              <div className="text-center p-2 rounded-lg bg-success-50">
                <p className="text-lg font-bold text-success-900 mb-1">
                  {portfolio?.total_positions || 0}
                </p>
                <p className="text-xs text-success-600">Positions</p>
              </div>
              <div className="text-center p-2 rounded-lg bg-warning-50">
                <p className="text-lg font-bold text-warning-900 mb-1">
                  {alerts.length}
                </p>
                <p className="text-xs text-warning-600">Alerts</p>
              </div>
              <div className="text-center p-2 rounded-lg bg-secondary-50">
                {riskOverview?.portfolio_risk_score ? (
                  <>
                    <p className="text-lg font-bold text-secondary-900 mb-1">
                      {(riskOverview.portfolio_risk_score * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs text-secondary-600">Risk</p>
                  </>
                ) : (
                  <>
                    <p className="text-lg font-bold text-secondary-400 mb-1">0%</p>
                    <p className="text-xs text-secondary-600">Risk</p>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Performance Chart - Expanded */}
        <div className="lg:col-span-2">
          <PerformanceChart />
        </div>
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Market Overview & Alerts */}
        <div className="space-y-6">
          <MarketOverview />
          <AlertsPanel />
        </div>

        {/* Middle & Right Columns - Trading Signals (Expanded) */}
        <div className="lg:col-span-2 space-y-6">
          <TradingSignals />
        </div>
      </div>

      {/* Portfolio Overview - Full Width */}
      <div className="mt-8">
        <PortfolioOverview />
      </div>
    </div>
  );
};

export default Dashboard;
