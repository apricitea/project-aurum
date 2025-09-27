import React from 'react';
import { ArrowUp, ArrowDown, Minus, TrendingUp, Star } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useDashboardStore } from '@/store/dashboard';
import { formatIDR, formatPercent, getPnLColorClass, formatStockCode } from '@/lib/utils';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const TradingSignals: React.FC = () => {
  const { signals, isLoadingSignals } = useDashboardStore();

  const getSignalIcon = (signalType: string) => {
    switch (signalType) {
      case 'STRONG_BUY':
      case 'BUY':
        return <ArrowUp className="h-4 w-4" />;
      case 'STRONG_SELL':
      case 'SELL':
        return <ArrowDown className="h-4 w-4" />;
      case 'HOLD':
      default:
        return <Minus className="h-4 w-4" />;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-success-600';
    if (confidence >= 0.6) return 'text-warning-600';
    return 'text-secondary-600';
  };

  if (isLoadingSignals && signals.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5" />
            <span>Trading Signals</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32">
            <LoadingSpinner />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <TrendingUp className="h-8 w-8 text-primary-600 mx-auto mb-3" />
              <p className="text-sm text-secondary-600 mb-2">Total Signals</p>
              <p className="text-2xl font-bold text-secondary-900">
                {signals.length}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <ArrowUp className="h-8 w-8 text-success-600 mx-auto mb-3" />
              <p className="text-sm text-secondary-600 mb-2">Buy Signals</p>
              <p className="text-2xl font-bold text-success-600">
                {signals.filter(s => s.signal === 'BUY' || s.signal === 'STRONG_BUY').length}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <ArrowDown className="h-8 w-8 text-danger-600 mx-auto mb-3" />
              <p className="text-sm text-secondary-600 mb-2">Sell Signals</p>
              <p className="text-2xl font-bold text-danger-600">
                {signals.filter(s => s.signal === 'SELL' || s.signal === 'STRONG_SELL').length}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <Star className="h-8 w-8 text-warning-500 mx-auto mb-3" />
              <p className="text-sm text-secondary-600 mb-2">Avg Confidence</p>
              <p className="text-2xl font-bold text-secondary-900">
                {signals.length > 0
                  ? formatPercent(
                      signals.reduce((sum, s) => sum + (s.confidence || 0), 0) / signals.length
                    )
                  : '76.00%'
                }
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Signals */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5" />
            <span>Top Trading Signals Today</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {signals.length === 0 ? (
            <div className="text-center py-8 text-secondary-600">
              <p>No signals available for today</p>
            </div>
          ) : (
            <div className="space-y-4">
              {signals.slice(0, 8).map((signal, index) => (
                <div
                  key={index}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg border border-secondary-200 hover:bg-secondary-50 transition-colors space-y-3 sm:space-y-0"
                >
                  <div className="flex items-center space-x-3 min-w-0 flex-1">
                    <div className="flex items-center justify-center w-6 h-6 rounded-full bg-secondary-100 text-secondary-600 text-xs font-medium flex-shrink-0">
                      {index + 1}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="font-semibold text-secondary-900 text-lg">
                          {signal.stock_code}
                        </h4>
                        <Badge
                          variant={
                            signal.signal?.includes('BUY') ? 'success' :
                            signal.signal?.includes('SELL') ? 'danger' : 'secondary'
                          }
                          className="flex items-center space-x-1 text-xs"
                        >
                          {getSignalIcon(signal.signal)}
                          <span className="hidden sm:inline">{signal.signal}</span>
                        </Badge>
                      </div>
                      <div className="space-y-1">
                        {signal.sector && (
                          <p className="text-xs text-secondary-600 truncate">
                            {signal.sector}
                          </p>
                        )}
                        <p className="text-xs text-secondary-500 truncate">
                          {signal.company_name}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-between sm:justify-end sm:space-x-4 text-xs flex-shrink-0">
                    <div className="text-center sm:text-right">
                      <p className="text-secondary-600 mb-1">Price</p>
                      <p className="font-semibold text-secondary-900">
                        Rp {signal.current_price?.toLocaleString() || 'N/A'}
                      </p>
                    </div>

                    <div className="text-center sm:text-right">
                      <p className="text-secondary-600 mb-1">Target</p>
                      <p className="font-semibold text-secondary-900">
                        Rp {signal.target_price?.toLocaleString() || 'N/A'}
                      </p>
                    </div>

                    <div className="text-center sm:text-right">
                      <p className="text-secondary-600 mb-1">Confidence</p>
                      <p className={`font-semibold ${getConfidenceColor(signal.confidence || 0)}`}>
                        {formatPercent(signal.confidence || 0)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default TradingSignals;