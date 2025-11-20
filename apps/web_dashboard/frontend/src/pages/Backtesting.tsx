import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Calendar,
  Award,
  AlertTriangle,
  BarChart3,
  PieChart,
  RefreshCw
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { apiClient } from '@/lib/api';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface BacktestOverview {
  total_trades: number;
  win_rate: number;
  total_profit: number;
  total_profit_formatted: string;
  avg_return: number;
  avg_holding_days: number;
  best_trade: number;
  worst_trade: number;
  sharpe_ratio: number;
}

interface ConfidenceAnalysis {
  [bucket: string]: {
    total_trades: number;
    win_rate: number;
    total_profit: number;
    avg_return: number;
    profit_formatted: string;
  };
}

interface SectorAnalysis {
  [sector: string]: {
    total_trades: number;
    win_rate: number;
    total_profit: number;
    avg_return: number;
  };
}

interface Trade {
  stock_code: string;
  profit: number;
  return_pct: number;
  confidence: number;
  date: string;
}

interface BacktestingData {
  overview: BacktestOverview;
  confidence_analysis: ConfidenceAnalysis;
  sector_analysis: SectorAnalysis;
  best_trades: Trade[];
  worst_trades: Trade[];
  monthly_performance: Array<{
    month: string;
    profit: number;
    trades: number;
  }>;
}

const Backtesting: React.FC = () => {
  const [backtestData, setBacktestData] = useState<BacktestingData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBacktestData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiClient.getBacktestingPerformance();
      setBacktestData(data.performance);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load backtest data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBacktestData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !backtestData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="p-6">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-danger-500 mx-auto mb-4" />
            <p className="text-danger-700 mb-4">{error || 'No backtest data available'}</p>
            <Button onClick={fetchBacktestData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const { overview, confidence_analysis, sector_analysis, best_trades, worst_trades } = backtestData;

  const formatCurrency = (amount: number) => {
    if (Math.abs(amount) >= 1_000_000_000) {
      return `Rp ${(amount / 1_000_000_000).toFixed(2)}B`;
    } else if (Math.abs(amount) >= 1_000_000) {
      return `Rp ${(amount / 1_000_000).toFixed(2)}M`;
    } else {
      return `Rp ${amount.toLocaleString()}`;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900 mb-2">
            Backtesting Performance
          </h1>
          <p className="text-secondary-600">
            Historical signal performance analysis over 2 years
          </p>
        </div>
        <Button onClick={fetchBacktestData} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Analysis
        </Button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="border-l-4 border-l-primary-500">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-secondary-600">Total Profit</p>
                  <p className="text-2xl font-bold text-primary-900 mt-1">
                    {overview.total_profit_formatted}
                  </p>
                  <p className="text-sm text-secondary-500 mt-1">
                    {overview.total_trades} trades
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-primary-600" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="border-l-4 border-l-success-500">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-secondary-600">Win Rate</p>
                  <p className="text-2xl font-bold text-success-900 mt-1">
                    {overview.win_rate}%
                  </p>
                  <p className="text-sm text-secondary-500 mt-1">
                    Successful trades
                  </p>
                </div>
                <Target className="h-8 w-8 text-success-600" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <Card className="border-l-4 border-l-warning-500">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-secondary-600">Avg Return</p>
                  <p className={`text-2xl font-bold mt-1 ${overview.avg_return >= 0 ? 'text-success-900' : 'text-danger-900'}`}>
                    {overview.avg_return > 0 ? '+' : ''}{overview.avg_return}%
                  </p>
                  <p className="text-sm text-secondary-500 mt-1">
                    Per trade
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-warning-600" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-secondary-600">Sharpe Ratio</p>
                  <p className="text-2xl font-bold text-blue-900 mt-1">
                    {overview.sharpe_ratio}
                  </p>
                  <p className="text-sm text-secondary-500 mt-1">
                    Risk-adjusted
                  </p>
                </div>
                <BarChart3 className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Confidence Analysis */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-5 w-5" />
              Performance by Confidence Level
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(confidence_analysis).map(([bucket, data]) => (
                <div key={bucket} className="p-4 rounded-lg bg-gradient-to-br from-slate-50 to-slate-100 border">
                  <div className="text-center">
                    <h4 className="font-semibold text-slate-900 mb-2">{bucket} Confidence</h4>
                    <div className="space-y-2">
                      <div>
                        <p className="text-2xl font-bold text-primary-900">{data.profit_formatted}</p>
                        <p className="text-xs text-slate-600">Total Profit</p>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Win Rate:</span>
                        <span className={`font-medium ${data.win_rate >= 70 ? 'text-success-600' : data.win_rate >= 60 ? 'text-warning-600' : 'text-danger-600'}`}>
                          {data.win_rate}%
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Trades:</span>
                        <span className="font-medium text-slate-900">{data.total_trades}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">Avg Return:</span>
                        <span className={`font-medium ${data.avg_return >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                          {data.avg_return > 0 ? '+' : ''}{data.avg_return}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Sector Performance & Best/Worst Trades */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sector Analysis */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 }}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChart className="h-5 w-5" />
                Sector Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {Object.entries(sector_analysis)
                  .sort(([,a], [,b]) => b.total_profit - a.total_profit)
                  .map(([sector, data]) => (
                  <div key={sector} className="flex items-center justify-between p-3 rounded-lg bg-secondary-50 border">
                    <div className="min-w-0 flex-1">
                      <h4 className="font-medium text-secondary-900 truncate">{sector}</h4>
                      <div className="flex items-center gap-4 text-sm text-secondary-600 mt-1">
                        <span>{data.total_trades} trades</span>
                        <span className={data.win_rate >= 70 ? 'text-success-600' : data.win_rate >= 60 ? 'text-warning-600' : 'text-danger-600'}>
                          {data.win_rate}% win
                        </span>
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className={`font-semibold ${data.total_profit >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                        {formatCurrency(data.total_profit)}
                      </p>
                      <p className={`text-sm ${data.avg_return >= 0 ? 'text-success-600' : 'text-danger-600'}`}>
                        {data.avg_return > 0 ? '+' : ''}{data.avg_return}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Best/Worst Trades */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.7 }}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Top Trades
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Best Trades */}
                <div>
                  <h4 className="font-medium text-success-900 mb-3 flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Best Trades
                  </h4>
                  <div className="space-y-2">
                    {best_trades.slice(0, 5).map((trade, index) => (
                      <div key={index} className="flex items-center justify-between p-2 rounded-lg bg-success-50 border border-success-200">
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">{trade.stock_code}</Badge>
                          <span className="text-sm text-secondary-600">{trade.date}</span>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-success-600">
                            {formatCurrency(trade.profit)}
                          </p>
                          <p className="text-xs text-success-600">
                            +{trade.return_pct}% ({trade.confidence * 100}%)
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Worst Trades */}
                <div>
                  <h4 className="font-medium text-danger-900 mb-3 flex items-center gap-2">
                    <TrendingDown className="h-4 w-4" />
                    Worst Trades
                  </h4>
                  <div className="space-y-2">
                    {worst_trades.slice(0, 5).map((trade, index) => (
                      <div key={index} className="flex items-center justify-between p-2 rounded-lg bg-danger-50 border border-danger-200">
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">{trade.stock_code}</Badge>
                          <span className="text-sm text-secondary-600">{trade.date}</span>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-danger-600">
                            {formatCurrency(trade.profit)}
                          </p>
                          <p className="text-xs text-danger-600">
                            {trade.return_pct}% ({trade.confidence * 100}%)
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Performance Summary */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }}>
        <Card>
          <CardHeader>
            <CardTitle>Performance Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 rounded-lg bg-secondary-50">
                <p className="text-sm text-secondary-600 mb-2">Best Single Trade</p>
                <p className="text-xl font-bold text-success-600">
                  {formatCurrency(overview.best_trade)}
                </p>
              </div>
              <div className="text-center p-4 rounded-lg bg-secondary-50">
                <p className="text-sm text-secondary-600 mb-2">Worst Single Trade</p>
                <p className="text-xl font-bold text-danger-600">
                  {formatCurrency(overview.worst_trade)}
                </p>
              </div>
              <div className="text-center p-4 rounded-lg bg-secondary-50">
                <p className="text-sm text-secondary-600 mb-2">Avg Holding Period</p>
                <p className="text-xl font-bold text-secondary-900">
                  {overview.avg_holding_days} days
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default Backtesting;