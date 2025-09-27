import React from 'react';
import { Activity, Clock, TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useDashboardStore } from '@/store/dashboard';
import { formatWIBDateTime, isMarketOpen } from '@/lib/utils';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const MarketOverview: React.FC = () => {
  const { marketStatus, isLoading } = useDashboardStore();
  const [currentTime, setCurrentTime] = React.useState(new Date());

  // Update current time every 30 seconds (less aggressive for better performance)
  React.useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 30000);

    return () => clearInterval(timer);
  }, []);

  const marketIsOpen = isMarketOpen();

  // Mock market data (in real implementation, this would come from the API)
  const marketIndices = [
    {
      name: 'JCI',
      value: 7125.45,
      change: 45.23,
      changePercent: 0.64,
    },
    {
      name: 'LQ45',
      value: 985.67,
      change: -12.34,
      changePercent: -1.23,
    },
    {
      name: 'IDX30',
      value: 512.89,
      change: 8.45,
      changePercent: 1.68,
    },
  ];

  if (isLoading && !marketStatus) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Market Overview</span>
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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Market Overview</span>
          </div>
          <Badge
            variant={marketIsOpen ? 'success' : 'secondary'}
            className="flex items-center space-x-1"
          >
            <div
              className={`h-2 w-2 rounded-full ${
                marketIsOpen ? 'bg-success-500' : 'bg-secondary-500'
              }`}
            />
            <span>{marketIsOpen ? 'Open' : 'Closed'}</span>
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Market Status */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg bg-secondary-50 space-y-3 sm:space-y-0">
            <div className="flex items-center space-x-3 min-w-0 flex-1">
              <Clock className="h-5 w-5 text-secondary-600 flex-shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-secondary-900 truncate">
                  Current Time (WIB)
                </p>
                <p className="text-base sm:text-lg font-bold text-secondary-900 truncate">
                  {formatWIBDateTime(currentTime)}
                </p>
              </div>
            </div>
            <div className="text-left sm:text-right flex-shrink-0">
              <p className="text-sm text-secondary-600">Trading Hours</p>
              <p className="text-sm font-medium text-secondary-900">
                09:00 - 15:49
                <span className="hidden sm:inline"> WIB</span>
              </p>
            </div>
          </div>

          {/* Market Indices */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-secondary-700 uppercase tracking-wider">
              Major Indices
            </h4>
            <div className="grid grid-cols-1 gap-3">
              {marketIndices.map((index, i) => {
                const isPositive = index.change >= 0;
                const Icon = isPositive ? TrendingUp : TrendingDown;

                return (
                  <div
                    key={index.name}
                    className="flex items-center justify-between p-3 rounded-lg border border-secondary-200 bg-white"
                  >
                    <div className="flex items-center space-x-3 min-w-0 flex-1">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h5 className="font-semibold text-secondary-900 text-lg">
                            {index.name}
                          </h5>
                          <Icon
                            className={`h-4 w-4 flex-shrink-0 ${
                              isPositive ? 'text-success-600' : 'text-danger-600'
                            }`}
                          />
                        </div>
                        <p className="text-xl font-bold text-secondary-900">
                          {index.value.toLocaleString('id-ID', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </p>
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div
                        className={`text-sm font-medium ${
                          isPositive ? 'text-success-600' : 'text-danger-600'
                        }`}
                      >
                        {isPositive ? '+' : ''}{index.change.toFixed(2)}
                      </div>
                      <div
                        className={`text-sm ${
                          isPositive ? 'text-success-600' : 'text-danger-600'
                        }`}
                      >
                        ({isPositive ? '+' : ''}{index.changePercent.toFixed(2)}%)
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Market Session Info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-primary-50 border border-primary-200">
              <p className="text-xs font-medium text-primary-900 mb-1 uppercase tracking-wide">
                Next Market Open
              </p>
              <p className="text-sm font-semibold text-primary-700">
                {marketIsOpen ? 'Tomorrow 09:00' : 'Today 09:00'}
                <span className="text-xs ml-1">WIB</span>
              </p>
            </div>
            <div className="p-3 rounded-lg bg-secondary-50 border border-secondary-200">
              <p className="text-xs font-medium text-secondary-900 mb-1 uppercase tracking-wide">
                Last Update
              </p>
              <p className="text-sm font-semibold text-secondary-700 truncate">
                {marketStatus
                  ? formatWIBDateTime(marketStatus.current_time)
                  : 'Loading...'
                }
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default MarketOverview;