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
          <div className="flex items-center justify-between p-4 rounded-lg bg-secondary-50">
            <div className="flex items-center space-x-3">
              <Clock className="h-5 w-5 text-secondary-600" />
              <div>
                <p className="text-sm font-medium text-secondary-900">
                  Current Time (WIB)
                </p>
                <p className="text-lg font-bold text-secondary-900">
                  {formatWIBDateTime(currentTime)}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-secondary-600">Trading Hours</p>
              <p className="text-sm font-medium text-secondary-900">
                09:00 - 15:49 WIB
              </p>
            </div>
          </div>

          {/* Market Indices */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-secondary-700 uppercase tracking-wider">
              Major Indices
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {marketIndices.map((index, i) => {
                const isPositive = index.change >= 0;
                const Icon = isPositive ? TrendingUp : TrendingDown;

                return (
                  <div
                    key={index.name}
                    className="p-4 rounded-lg border border-secondary-200 bg-white"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h5 className="font-medium text-secondary-900">
                        {index.name}
                      </h5>
                      <Icon
                        className={`h-4 w-4 ${
                          isPositive ? 'text-success-600' : 'text-danger-600'
                        }`}
                      />
                    </div>
                    <p className="text-xl font-bold text-secondary-900 mb-1">
                      {index.value.toLocaleString('id-ID', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </p>
                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-sm font-medium ${
                          isPositive ? 'text-success-600' : 'text-danger-600'
                        }`}
                      >
                        {isPositive ? '+' : ''}{index.change.toFixed(2)}
                      </span>
                      <span
                        className={`text-sm ${
                          isPositive ? 'text-success-600' : 'text-danger-600'
                        }`}
                      >
                        ({isPositive ? '+' : ''}{index.changePercent.toFixed(2)}%)
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Market Session Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 rounded-lg bg-primary-50 border border-primary-200">
              <p className="text-sm font-medium text-primary-900 mb-1">
                Next Market Open
              </p>
              <p className="text-sm text-primary-700">
                {marketIsOpen ? 'Tomorrow 09:00 WIB' : 'Today 09:00 WIB'}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-secondary-50 border border-secondary-200">
              <p className="text-sm font-medium text-secondary-900 mb-1">
                Last Data Update
              </p>
              <p className="text-sm text-secondary-700">
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