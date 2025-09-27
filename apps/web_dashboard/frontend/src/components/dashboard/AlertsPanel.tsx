import React from 'react';
import { AlertTriangle, CheckCircle, X, Clock } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useDashboardStore } from '@/store/dashboard';
import { getAlertPriorityColor, getRelativeTime, formatStockCode } from '@/lib/utils';
import { AlertPriority } from '@/types/api';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const AlertsPanel: React.FC = () => {
  const { alerts, isLoading, acknowledgeAlert, dismissAlert } = useDashboardStore();

  const handleAcknowledge = async (alertId: number) => {
    try {
      await acknowledgeAlert(alertId);
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const handleDismiss = async (alertId: number) => {
    try {
      await dismissAlert(alertId);
    } catch (error) {
      console.error('Failed to dismiss alert:', error);
    }
  };

  const getPriorityIcon = (priority: AlertPriority) => {
    switch (priority) {
      case AlertPriority.CRITICAL:
        return <AlertTriangle className="h-4 w-4 text-danger-600" />;
      case AlertPriority.HIGH:
        return <AlertTriangle className="h-4 w-4 text-warning-600" />;
      case AlertPriority.MEDIUM:
        return <Clock className="h-4 w-4 text-primary-600" />;
      default:
        return <Clock className="h-4 w-4 text-secondary-600" />;
    }
  };

  const groupedAlerts = alerts.reduce((groups, alert) => {
    if (!groups[alert.priority]) {
      groups[alert.priority] = [];
    }
    groups[alert.priority].push(alert);
    return groups;
  }, {} as Record<AlertPriority, typeof alerts>);

  if (isLoading && alerts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5" />
            <span>Active Alerts</span>
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
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4" />
            <span>Active Alerts</span>
            {alerts.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {alerts.length}
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-secondary-600">
            <CheckCircle className="h-12 w-12 mx-auto mb-4 text-success-500" />
            <p>No active alerts</p>
            <p className="text-sm">All systems are running smoothly</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-80 overflow-y-auto scrollbar-thin">
            {Object.entries(groupedAlerts)
              .sort(([a], [b]) => {
                const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
                return priorityOrder[a as AlertPriority] - priorityOrder[b as AlertPriority];
              })
              .map(([priority, priorityAlerts]) => (
                <div key={priority} className="space-y-2">
                  <h4 className="text-xs font-medium text-secondary-700 uppercase tracking-wider px-1">
                    {priority} Priority
                  </h4>
                  {priorityAlerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-2 rounded-lg border ${getAlertPriorityColor(alert.priority)}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            {getPriorityIcon(alert.priority)}
                            <span className="text-xs font-medium truncate">
                              {alert.alert_type}
                            </span>
                            {alert.stock_code && (
                              <Badge variant="secondary" className="text-xs flex-shrink-0">
                                {formatStockCode(alert.stock_code)}
                              </Badge>
                            )}
                          </div>

                          <p className="text-xs text-secondary-900 mb-1 line-clamp-2">
                            {alert.message}
                          </p>

                          <p className="text-xs text-secondary-600">
                            {getRelativeTime(alert.created_at)}
                          </p>
                        </div>

                        <div className="flex items-center space-x-1 flex-shrink-0">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleAcknowledge(alert.id)}
                            className="h-6 w-6 p-0"
                            title="Acknowledge"
                          >
                            <CheckCircle className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDismiss(alert.id)}
                            className="h-6 w-6 p-0"
                            title="Dismiss"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AlertsPanel;