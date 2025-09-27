import React from 'react';
import { Menu, Bell, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useDashboardStore } from '@/store/dashboard';
import { formatWIBTime, isMarketOpen } from '@/lib/utils';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';

interface HeaderProps {
  onSidebarToggle: () => void;
}

const Header: React.FC<HeaderProps> = ({ onSidebarToggle }) => {
  const {
    alerts,
    marketStatus,
    lastUpdated,
    isLoading,
    loadDashboardData,
  } = useDashboardStore();

  const [isOnline, setIsOnline] = React.useState(navigator.onLine);
  const [currentTime, setCurrentTime] = React.useState(new Date());

  // Update current time every second
  React.useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Monitor online status
  React.useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const activeAlerts = alerts.filter(alert => alert.status === 'active');
  const criticalAlerts = activeAlerts.filter(alert => alert.priority === 'critical');
  const marketIsOpen = isMarketOpen();

  const handleRefresh = () => {
    if (!isLoading) {
      loadDashboardData();
    }
  };

  return (
    <header className="sticky top-0 z-30 h-16 w-full border-b border-secondary-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="flex h-16 items-center justify-between px-4 lg:px-6">
        {/* Left section */}
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={onSidebarToggle}
            className="lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="hidden sm:block">
            <h1 className="text-lg font-semibold text-secondary-900">
              Indonesian Stock Trading Dashboard
            </h1>
            <p className="text-xs text-secondary-600">
              Sistem Alert Quantitative IDX
            </p>
          </div>
        </div>

        {/* Right section */}
        <div className="flex items-center space-x-4">
          {/* Market status */}
          <div className="hidden md:flex items-center space-x-2">
            <div className="flex items-center space-x-1">
              <div
                className={cn(
                  'h-2 w-2 rounded-full',
                  marketIsOpen ? 'bg-success-500' : 'bg-danger-500'
                )}
              />
              <span className="text-sm font-medium text-secondary-900">
                {marketIsOpen ? 'Market Open' : 'Market Closed'}
              </span>
            </div>
            <span className="text-sm text-secondary-600">
              {formatWIBTime(currentTime)} WIB
            </span>
          </div>

          {/* Connection status */}
          <div className="flex items-center">
            {isOnline ? (
              <Wifi className="h-4 w-4 text-success-500" />
            ) : (
              <WifiOff className="h-4 w-4 text-danger-500" />
            )}
          </div>

          {/* Refresh button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
            className="relative"
          >
            <RefreshCw
              className={cn(
                'h-4 w-4',
                isLoading && 'animate-spin'
              )}
            />
            {lastUpdated && (
              <span className="hidden sm:inline-block ml-2 text-xs text-secondary-600">
                Updated: {formatWIBTime(lastUpdated)}
              </span>
            )}
          </Button>

          {/* Alerts */}
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              className="relative"
            >
              <Bell className="h-4 w-4" />
              {activeAlerts.length > 0 && (
                <Badge
                  variant={criticalAlerts.length > 0 ? 'danger' : 'warning'}
                  className="absolute -top-1 -right-1 h-5 w-5 text-xs p-0 flex items-center justify-center"
                >
                  {activeAlerts.length > 99 ? '99+' : activeAlerts.length}
                </Badge>
              )}
            </Button>

            {/* Alerts dropdown could be implemented here */}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;