import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, AlertTriangle, TrendingUp, Activity, CheckCircle, Minus } from 'lucide-react';
import { useDashboardStore } from '@/store/dashboard';
import PortfolioOverview from '@/components/dashboard/PortfolioOverview';
import TradingSignals from '@/components/dashboard/TradingSignals';
import MarketOverview from '@/components/dashboard/MarketOverview';
import AlertsPanel from '@/components/dashboard/AlertsPanel';
import PerformanceChart from '@/components/dashboard/PerformanceChart';
import MarketStructureInsights from '@/components/dashboard/MarketStructureInsights';
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
        {/* Enhanced Quick Stats with Trends */}
        <Card className="border-l-4 border-l-primary-500">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-base">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary-600" />
                Market Pulse
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-success-500 animate-pulse"></div>
                <span className="text-xs text-success-600 font-medium">Live</span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="group relative p-3 rounded-xl bg-gradient-to-br from-primary-50 to-primary-100 border border-primary-200 hover:shadow-md transition-all duration-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-primary-700 uppercase tracking-wide">Signals Today</span>
                  <div className="flex items-center gap-1">
                    <TrendingUp className="h-3 w-3 text-success-500" />
                    <span className="text-xs text-success-600">+{Math.max(0, topSignals.length - 3)}</span>
                  </div>
                </div>
                <p className="text-2xl font-bold text-primary-900 mb-1">
                  {topSignals.length}
                </p>
                <div className="w-full bg-primary-200 rounded-full h-1.5">
                  <div className="bg-primary-600 h-1.5 rounded-full transition-all duration-500" style={{width: `${Math.min(100, (topSignals.length / 10) * 100)}%`}}></div>
                </div>
              </div>

              <div className="group relative p-3 rounded-xl bg-gradient-to-br from-success-50 to-success-100 border border-success-200 hover:shadow-md transition-all duration-200">
                <div className="flex items-center justify-between mb-2">
                  {/* Sebelumnya Active Positions karna kelebihan sementara dijadikan positions dulu */}
                  <span className="text-xs font-medium text-success-700 uppercase tracking-wide">Positions</span>
                  <div className="flex items-center gap-1">
                    <Activity className="h-3 w-3 text-success-500" />
                    <span className="text-xs text-success-600">
                      {portfolio?.total_positions ? (portfolio.total_positions > 5 ? 'High' : 'Low') : 'None'}
                    </span>
                  </div>
                </div>
                <p className="text-2xl font-bold text-success-900 mb-1">
                  {portfolio?.total_positions || 0}
                </p>
                <div className="w-full bg-success-200 rounded-full h-1.5">
                  <div className="bg-success-600 h-1.5 rounded-full transition-all duration-500" style={{width: `${Math.min(100, ((portfolio?.total_positions || 0) / 15) * 100)}%`}}></div>
                </div>
              </div>

              <div className="group relative p-3 rounded-xl bg-gradient-to-br from-warning-50 to-warning-100 border border-warning-200 hover:shadow-md transition-all duration-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-warning-700 uppercase tracking-wide">Active Alerts</span>
                  <div className="flex items-center gap-1">
                    {alerts.length > 0 ? (
                      <>
                        <AlertTriangle className="h-3 w-3 text-warning-500" />
                        <span className="text-xs text-warning-600">
                          {alerts.length > 5 ? 'High' : 'Normal'}
                        </span>
                      </>
                    ) : (
                      <>
                        <CheckCircle className="h-3 w-3 text-success-500" />
                        <span className="text-xs text-success-600">Clear</span>
                      </>
                    )}
                  </div>
                </div>
                <p className="text-2xl font-bold text-warning-900 mb-1">
                  {alerts.length}
                </p>
                <div className="w-full bg-warning-200 rounded-full h-1.5">
                  <div className="bg-warning-600 h-1.5 rounded-full transition-all duration-500" style={{width: `${Math.min(100, (alerts.length / 8) * 100)}%`}}></div>
                </div>
              </div>

              <div className="group relative p-3 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 hover:shadow-md transition-all duration-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-slate-700 uppercase tracking-wide">Risk Level</span>
                  <div className="flex items-center gap-1">
                    {riskOverview?.portfolio_risk_score ? (
                      riskOverview.portfolio_risk_score > 0.7 ? (
                        <>
                          <AlertTriangle className="h-3 w-3 text-danger-500" />
                          <span className="text-xs text-danger-600">High</span>
                        </>
                      ) : riskOverview.portfolio_risk_score > 0.4 ? (
                        <>
                          <Minus className="h-3 w-3 text-warning-500" />
                          <span className="text-xs text-warning-600">Medium</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle className="h-3 w-3 text-success-500" />
                          <span className="text-xs text-success-600">Low</span>
                        </>
                      )
                    ) : (
                      <>
                        <Minus className="h-3 w-3 text-slate-500" />
                        <span className="text-xs text-slate-600">N/A</span>
                      </>
                    )}
                  </div>
                </div>
                <p className="text-2xl font-bold text-slate-900 mb-1">
                  {riskOverview?.portfolio_risk_score
                    ? `${Math.min(100, (riskOverview.portfolio_risk_score * 100)).toFixed(0)}%`
                    : '0%'
                  }
                </p>
                <div className="w-full bg-slate-200 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${
                      riskOverview?.portfolio_risk_score
                        ? riskOverview.portfolio_risk_score > 0.7
                          ? 'bg-danger-600'
                          : riskOverview.portfolio_risk_score > 0.4
                            ? 'bg-warning-600'
                            : 'bg-success-600'
                        : 'bg-slate-400'
                    }`}
                    style={{width: `${Math.min(100, (riskOverview?.portfolio_risk_score || 0) * 100)}%`}}
                  ></div>
                </div>
              </div>
            </div>

            {/* Market Status Banner */}
            <div className="mt-4 p-3 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${marketStatus?.is_open ? 'bg-success-500' : 'bg-danger-500'}`}></div>
                  <span className="text-sm font-medium text-blue-900">
                    Market {marketStatus?.is_open ? 'Open' : 'Closed'}
                  </span>
                  <span className="text-xs text-blue-600">
                    • {marketStatus?.session_type || 'Regular Session'}
                  </span>
                </div>
                <div className="text-right">
                  <p className="text-xs text-blue-600">Next Session</p>
                  <p className="text-sm font-semibold text-blue-900">
                    {marketStatus?.is_open ? 'Tomorrow 09:00' : 'Today 09:00'}
                  </p>
                </div>
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

      {/* Portfolio & Market Structure Insights */}
      <div className="mt-8 space-y-6">
        <PortfolioOverview />
        <MarketStructureInsights />
      </div>
    </div>
  );
};

export default Dashboard;
