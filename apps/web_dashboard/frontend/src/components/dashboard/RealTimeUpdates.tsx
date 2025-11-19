import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Wifi, WifiOff, Activity, Clock } from 'lucide-react';
import { wsClient } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { formatTime } from '@/lib/utils';

interface RealtimeUpdate {
  id: string;
  type: 'signal' | 'alert' | 'portfolio' | 'market';
  message: string;
  timestamp: Date;
  data?: any;
}

const RealTimeUpdates: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [updates, setUpdates] = useState<RealtimeUpdate[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    // Subscribe to WebSocket connection status
    const handleOpen = () => {
      setIsConnected(true);
      addUpdate({
        id: Date.now().toString(),
        type: 'market',
        message: 'Real-time connection established',
        timestamp: new Date(),
      });
    };

    // Subscribe to real-time updates
    const unsubscribeSignal = wsClient.subscribe('signal_update', (data: any) => {
      addUpdate({
        id: Date.now().toString(),
        type: 'signal',
        message: `New trading signal: ${data.stock_code} - ${data.signal_type}`,
        timestamp: new Date(),
        data,
      });
    });

    const unsubscribeAlert = wsClient.subscribe('alert_update', (data: any) => {
      addUpdate({
        id: Date.now().toString(),
        type: 'alert',
        message: `${data.priority.toUpperCase()} alert: ${data.message}`,
        timestamp: new Date(),
        data,
      });
    });

    const unsubscribePortfolio = wsClient.subscribe('portfolio_update', (data: any) => {
      addUpdate({
        id: Date.now().toString(),
        type: 'portfolio',
        message: `Portfolio updated: ${data.stock_code || 'Summary'}`,
        timestamp: new Date(),
        data,
      });
    });

    // Simulate connection status (in real app, this would come from WebSocket events)
    const checkConnection = () => {
      // Simulate occasional connection status
      setIsConnected(Math.random() > 0.1); // 90% connected
    };

    const connectionInterval = setInterval(checkConnection, 5000);
    
    // Initial connection
    setTimeout(handleOpen, 1000);

    return () => {
      clearInterval(connectionInterval);
      unsubscribeSignal();
      unsubscribeAlert();
      unsubscribePortfolio();
    };
  }, []);

  const addUpdate = (update: RealtimeUpdate) => {
    setUpdates(prev => [update, ...prev.slice(0, 4)]); // Keep only last 5 updates
    setLastUpdate(new Date());
  };

  const getUpdateIcon = (type: RealtimeUpdate['type']) => {
    switch (type) {
      case 'signal':
        return '📈';
      case 'alert':
        return '⚠️';
      case 'portfolio':
        return '💼';
      case 'market':
        return '🔄';
      default:
        return '📢';
    }
  };

  const getUpdateColor = (type: RealtimeUpdate['type']) => {
    switch (type) {
      case 'signal':
        return 'bg-primary-50 border-primary-200';
      case 'alert':
        return 'bg-warning-50 border-warning-200';
      case 'portfolio':
        return 'bg-success-50 border-success-200';
      case 'market':
        return 'bg-info-50 border-info-200';
      default:
        return 'bg-secondary-50 border-secondary-200';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-secondary-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary-600" />
          <h3 className="font-medium text-secondary-900">Real-time Updates</h3>
        </div>
        
        <div className="flex items-center gap-3">
          {lastUpdate && (
            <div className="flex items-center gap-1 text-xs text-secondary-500">
              <Clock className="h-3 w-3" />
              {formatTime(lastUpdate)}
            </div>
          )}
          
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Wifi className="h-4 w-4 text-success-500" />
            ) : (
              <WifiOff className="h-4 w-4 text-danger-500" />
            )}
            <Badge 
              variant={isConnected ? 'success' : 'danger'}
              size="sm"
            >
              {isConnected ? 'Connected' : 'Disconnected'}
            </Badge>
          </div>
        </div>
      </div>

      {/* Updates List */}
      <div className="space-y-2">
        <AnimatePresence>
          {updates.length === 0 ? (
            <div className="text-center py-4 text-secondary-500 text-sm">
              Waiting for real-time updates...
            </div>
          ) : (
            updates.map((update) => (
              <motion.div
                key={update.id}
                initial={{ opacity: 0, x: -20, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 20, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                className={`flex items-center gap-3 p-3 rounded-lg border ${
                  getUpdateColor(update.type)
                }`}
              >
                <div className="text-lg">
                  {getUpdateIcon(update.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-secondary-900 truncate">
                    {update.message}
                  </p>
                  <p className="text-xs text-secondary-500">
                    {formatTime(update.timestamp)}
                  </p>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Connection Status Details */}
      {!isConnected && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-4 p-3 bg-warning-50 border border-warning-200 rounded-lg"
        >
          <p className="text-sm text-warning-700">
            Real-time updates are temporarily unavailable. Data will refresh automatically when connection is restored.
          </p>
        </motion.div>
      )}
    </div>
  );
};

export default RealTimeUpdates;
