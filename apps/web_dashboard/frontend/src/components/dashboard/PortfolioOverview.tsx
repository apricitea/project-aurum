import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, PieChart } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { useDashboardStore } from '@/store/dashboard';
import { formatIDR, formatPercent, getPnLColorClass } from '@/lib/utils';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const PortfolioOverview: React.FC = () => {
  const { portfolio, isLoading } = useDashboardStore();

  if (isLoading && !portfolio) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="p-6">
            <div className="flex items-center justify-center h-20">
              <LoadingSpinner />
            </div>
          </Card>
        ))}
      </div>
    );
  }

  if (!portfolio) {
    return (
      <Card className="p-6">
        <div className="text-center text-secondary-600">
          <p>Portfolio data not available</p>
        </div>
      </Card>
    );
  }

  const metrics = [
    {
      title: 'Total Market Value',
      value: formatIDR(portfolio.total_market_value),
      icon: DollarSign,
      change: null,
    },
    {
      title: 'Unrealized P&L',
      value: formatIDR(portfolio.total_unrealized_pnl),
      icon: portfolio.total_unrealized_pnl >= 0 ? TrendingUp : TrendingDown,
      change: formatPercent(portfolio.total_unrealized_pnl_percent / 100),
      changeColor: getPnLColorClass(portfolio.total_unrealized_pnl),
    },
    {
      title: 'Total Positions',
      value: portfolio.total_positions?.toString() || '0',
      icon: PieChart,
      change: null,
    },
    {
      title: 'Cash Available',
      value: formatIDR(portfolio.cash_available || 0),
      icon: DollarSign,
      change: null,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric, index) => {
          const Icon = metric.icon;

          return (
            <Card key={index}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between h-20">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-secondary-600">
                      {metric.title}
                    </p>
                    <p className="text-2xl font-bold text-secondary-900 mt-1">
                      {metric.value}
                    </p>
                    {metric.change && (
                      <p className={`text-sm mt-1 ${metric.changeColor}`}>
                        {metric.change}
                      </p>
                    )}
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                    <Icon className="h-6 w-6 text-primary-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Sector Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Sector Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(portfolio.sector_breakdown).map(([sector, percentage]) => (
              <div key={sector} className="flex items-center justify-between p-3 rounded-lg bg-secondary-50">
                <span className="text-sm font-medium text-secondary-900">
                  {sector}
                </span>
                <span className="text-sm text-secondary-600">
                  {formatPercent(percentage / 100)}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      {(portfolio.sharpe_ratio || portfolio.max_drawdown || portfolio.portfolio_beta) && (
        <Card>
          <CardHeader>
            <CardTitle>Risk Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {portfolio.sharpe_ratio && (
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Sharpe Ratio</p>
                  <p className="text-2xl font-bold text-secondary-900 mt-1">
                    {portfolio.sharpe_ratio.toFixed(2)}
                  </p>
                </div>
              )}
              {portfolio.max_drawdown && (
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Max Drawdown</p>
                  <p className="text-2xl font-bold text-danger-600 mt-1">
                    {formatPercent(portfolio.max_drawdown)}
                  </p>
                </div>
              )}
              {portfolio.portfolio_beta && (
                <div className="text-center">
                  <p className="text-sm text-secondary-600">Portfolio Beta</p>
                  <p className="text-2xl font-bold text-secondary-900 mt-1">
                    {portfolio.portfolio_beta.toFixed(2)}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PortfolioOverview;