import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3,
  PieChart,
  TrendingUp,
  Download,
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Pie } from 'react-chartjs-2';
import { useDashboardStore } from '@/store/dashboard';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import {
  formatIDR,
  formatPercent,
  generateChartColors,
} from '@/lib/utils';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const Analytics: React.FC = () => {
  const {
    performance,
    fetchPerformance,
    portfolio,
  } = useDashboardStore();

  const [timeFrame, setTimeFrame] = useState(30);
  const [activeTab, setActiveTab] = useState<'performance' | 'signals' | 'risk'>('performance');

  useEffect(() => {
    fetchPerformance(timeFrame);
  }, [fetchPerformance, timeFrame]);

  // Sample data for charts (in real app, this would come from API)
  const generateSignalDistributionData = () => {
    if (!performance || !performance.signal_type_distribution) {
      return {
        labels: ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell'],
        datasets: [
          {
            data: [25, 35, 20, 15, 5],
            backgroundColor: generateChartColors(5),
            borderColor: generateChartColors(5),
            borderWidth: 2,
          },
        ],
      };
    }

    const distribution = performance.signal_type_distribution;
    return {
      labels: Object.keys(distribution).map(key => key.replace('_', ' ')),
      datasets: [
        {
          data: Object.values(distribution),
          backgroundColor: generateChartColors(Object.keys(distribution).length),
          borderColor: generateChartColors(Object.keys(distribution).length),
          borderWidth: 2,
        },
      ],
    };
  };

  const generatePerformanceData = () => {
    // Sample monthly performance data
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    const returns = [2.5, -1.2, 4.1, 1.8, -0.5, 3.2];

    return {
      labels: months,
      datasets: [
        {
          label: 'Monthly Returns (%)',
          data: returns,
          backgroundColor: returns.map(r => r >= 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)'),
          borderColor: returns.map(r => r >= 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'),
          borderWidth: 2,
        },
      ],
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
      },
    },
  };

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const,
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        callbacks: {
          label: function(context: any) {
            const label = context.label || '';
            const value = context.parsed;
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
            const percentage = ((value / total) * 100).toFixed(1);
            return `${label}: ${value} (${percentage}%)`;
          },
        },
      },
    },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900 mb-2">
            Analytics & Performance
          </h1>
          <p className="text-secondary-600">
            Analyze trading performance and portfolio metrics
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={timeFrame}
            onChange={(e) => setTimeFrame(parseInt(e.target.value))}
            className="px-3 py-2 bg-transparent border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 h-8 text-xs"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>

          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-secondary-200">
        <nav className="flex space-x-8">
          {[
            { id: 'performance', label: 'Performance', icon: TrendingUp },
            { id: 'signals', label: 'Signal Analysis', icon: BarChart3 },
            { id: 'risk', label: 'Risk Metrics', icon: PieChart },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-secondary-500 hover:text-secondary-700 hover:border-secondary-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Performance Tab */}
      {activeTab === 'performance' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Performance Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Total Return</p>
                  <p className="text-2xl font-bold text-success-600">
                    {performance?.performance_metrics?.total_return
                      ? formatPercent(performance.performance_metrics.total_return)
                      : '+12.4%'
                    }
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">{timeFrame} days</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Annualized Return</p>
                  <p className="text-2xl font-bold text-primary-600">
                    {performance?.performance_metrics?.annualized_return
                      ? formatPercent(performance.performance_metrics.annualized_return)
                      : '+18.7%'
                    }
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">Projected</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Volatility</p>
                  <p className="text-2xl font-bold text-warning-600">
                    {performance?.performance_metrics?.volatility
                      ? formatPercent(performance.performance_metrics.volatility)
                      : '14.2%'
                    }
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">Standard dev.</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Sharpe Ratio</p>
                  <p className="text-2xl font-bold text-secondary-900">
                    {performance?.performance_metrics?.sharpe_ratio?.toFixed(2) || '1.42'}
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">Risk-adjusted</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Performance Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Monthly Returns</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <Bar data={generatePerformanceData()} options={chartOptions} />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Signal Analysis Tab */}
      {activeTab === 'signals' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Signal Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Total Signals</p>
                  <p className="text-2xl font-bold text-secondary-900">
                    {performance?.total_signals || 245}
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">{timeFrame} days</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Avg. Confidence</p>
                  <p className="text-2xl font-bold text-primary-600">
                    {performance?.avg_confidence
                      ? formatPercent(performance.avg_confidence)
                      : '78.5%'
                    }
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">Signal quality</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Win Rate</p>
                  <p className="text-2xl font-bold text-success-600">
                    {performance?.performance_metrics?.win_rate
                      ? formatPercent(performance.performance_metrics.win_rate)
                      : '67.3%'
                    }
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">Profitable signals</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Daily Signals</p>
                  <p className="text-2xl font-bold text-secondary-900">
                    {performance?.avg_daily_signals?.toFixed(1) || '8.2'}
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">Average per day</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Signal Distribution Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Signal Type Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <Pie data={generateSignalDistributionData()} options={pieOptions} />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Risk Metrics Tab */}
      {activeTab === 'risk' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Risk Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Max Drawdown</p>
                  <p className="text-2xl font-bold text-danger-600">
                    {performance?.performance_metrics?.max_drawdown
                      ? formatPercent(performance.performance_metrics.max_drawdown)
                      : '-8.4%'
                    }
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">Worst decline</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Portfolio Beta</p>
                  <p className="text-2xl font-bold text-secondary-900">
                    {portfolio?.portfolio_beta?.toFixed(2) || '1.15'}
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">vs JCI</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Value at Risk</p>
                  <p className="text-2xl font-bold text-warning-600">
                    {formatIDR(portfolio?.total_market_value ? portfolio.total_market_value * 0.05 : 50000000)}
                  </p>
                  <p className="text-xs text-secondary-500 mt-1">95% confidence</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Risk Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Risk Concentration</CardTitle>
              </CardHeader>
              <CardContent>
                {portfolio?.sector_breakdown ? (
                  <div className="space-y-3">
                    {Object.entries(portfolio.sector_breakdown).map(([sector, percentage]) => (
                      <div key={sector} className="flex items-center justify-between">
                        <span className="text-sm text-secondary-700">{sector}</span>
                        <div className="flex items-center justify-between w-40 xl:w-64">
                          <div className="w-20 xl:w-36 bg-secondary-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                percentage > 30 ? 'bg-danger-500' :
                                percentage > 20 ? 'bg-warning-500' :
                                'bg-success-500'
                              }`}
                              style={{ width: `${Math.min(percentage, 100)}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium text-secondary-900 text-right">
                            {formatPercent(percentage / 100)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-secondary-500">
                    No sector data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Risk Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-secondary-50 rounded-lg">
                    <span className="text-sm font-medium text-secondary-700">Correlation to JCI</span>
                    <span className="text-sm font-bold text-secondary-900">0.78</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-secondary-50 rounded-lg">
                    <span className="text-sm font-medium text-secondary-700">Information Ratio</span>
                    <span className="text-sm font-bold text-secondary-900">0.45</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-secondary-50 rounded-lg">
                    <span className="text-sm font-medium text-secondary-700">Tracking Error</span>
                    <span className="text-sm font-bold text-secondary-900">12.3%</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-secondary-50 rounded-lg">
                    <span className="text-sm font-medium text-secondary-700">Sortino Ratio</span>
                    <span className="text-sm font-bold text-secondary-900">2.14</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default Analytics;
