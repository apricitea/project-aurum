import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Bell,
  Shield,
  User,
  Database,
  Moon,
  Sun,
  Monitor,
  Save,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { storage } from '@/lib/utils';

interface Settings {
  theme: 'light' | 'dark' | 'system';
  notifications: {
    alerts: boolean;
    signals: boolean;
    portfolio: boolean;
    email: boolean;
    push: boolean;
  };
  risk: {
    maxPositionSize: number;
    maxDrawdown: number;
    stopLoss: number;
    alertThreshold: number;
  };
  trading: {
    autoTrading: boolean;
    confirmTrades: boolean;
    marketHoursOnly: boolean;
  };
  profile: {
    name: string;
    email: string;
    timezone: string;
  };
}

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'profile' | 'notifications' | 'risk' | 'trading'>('profile');
  const [settings, setSettings] = useState<Settings>(
    storage.get('userSettings', {
      theme: 'system' as const,
      notifications: {
        alerts: true,
        signals: true,
        portfolio: true,
        email: true,
        push: false,
      },
      risk: {
        maxPositionSize: 10,
        maxDrawdown: 15,
        stopLoss: 5,
        alertThreshold: 80,
      },
      trading: {
        autoTrading: false,
        confirmTrades: true,
        marketHoursOnly: true,
      },
      profile: {
        name: 'Trader User',
        email: 'trader@example.com',
        timezone: 'Asia/Jakarta',
      },
    })
  );
  const [hasChanges, setHasChanges] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const updateSettings = (section: keyof Settings, key: string, value: any) => {
    setSettings(prev => {
      const sectionData = prev[section] as Record<string, any>;
      return {
        ...prev,
        [section]: {
          ...sectionData,
          [key]: value,
        },
      };
    });
    setHasChanges(true);
  };

  const saveSettings = async () => {
    setSaveStatus('saving');
    try {
      storage.set('userSettings', settings);
      // In real app, would also save to backend
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      setSaveStatus('saved');
      setHasChanges(false);
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'risk', label: 'Risk Management', icon: Shield },
    { id: 'trading', label: 'Trading', icon: Database },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900 mb-2">
            Settings
          </h1>
          <p className="text-secondary-600">
            Configure your trading preferences and system settings
          </p>
        </div>

        <Button
          onClick={saveSettings}
          disabled={!hasChanges || saveStatus === 'saving'}
          className="flex items-center gap-2"
        >
          <Save className={`h-4 w-4 ${
            saveStatus === 'saving' ? 'animate-spin' : ''
          }`} />
          {saveStatus === 'saving' ? 'Saving...' :
           saveStatus === 'saved' ? 'Saved!' :
           saveStatus === 'error' ? 'Error' :
           'Save Changes'}
        </Button>
      </div>

      {/* Save Status Alert */}
      {saveStatus === 'error' && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-danger-50 border border-danger-200 rounded-lg p-4"
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-danger-500" />
            <p className="text-danger-700">Failed to save settings. Please try again.</p>
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Tab Navigation */}
        <div className="lg:col-span-1">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`w-full flex items-center gap-3 px-3 py-2 text-left rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary-50 text-primary-700 border border-primary-200'
                      : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-3">
          {/* Profile Settings */}
          {activeTab === 'profile' && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-6"
            >
              <Card>
                <CardHeader>
                  <CardTitle>Profile Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Full Name
                    </label>
                    <input
                      type="text"
                      value={settings.profile.name}
                      onChange={(e) => updateSettings('profile', 'name', e.target.value)}
                      className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Email Address
                    </label>
                    <input
                      type="email"
                      value={settings.profile.email}
                      onChange={(e) => updateSettings('profile', 'email', e.target.value)}
                      className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Timezone
                    </label>
                    <select
                      value={settings.profile.timezone}
                      onChange={(e) => updateSettings('profile', 'timezone', e.target.value)}
                      className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="Asia/Jakarta">Asia/Jakarta (WIB)</option>
                      <option value="Asia/Singapore">Asia/Singapore (SGT)</option>
                      <option value="Asia/Hong_Kong">Asia/Hong Kong (HKT)</option>
                    </select>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Theme Preferences</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { value: 'light', label: 'Light', icon: Sun },
                      { value: 'dark', label: 'Dark', icon: Moon },
                      { value: 'system', label: 'System', icon: Monitor },
                    ].map((theme) => {
                      const Icon = theme.icon;
                      return (
                        <button
                          key={theme.value}
                          onClick={() => updateSettings('theme', 'theme', theme.value)}
                          className={`p-4 rounded-lg border-2 transition-colors ${
                            settings.theme === theme.value
                              ? 'border-primary-500 bg-primary-50'
                              : 'border-secondary-200 hover:border-secondary-300'
                          }`}
                        >
                          <Icon className="h-6 w-6 mx-auto mb-2 text-secondary-600" />
                          <div className="text-sm font-medium text-secondary-900">
                            {theme.label}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Notification Settings */}
          {activeTab === 'notifications' && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-6"
            >
              <Card>
                <CardHeader>
                  <CardTitle>Notification Preferences</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {[
                    { key: 'alerts', label: 'Risk Alerts', description: 'Critical portfolio alerts and risk warnings' },
                    { key: 'signals', label: 'Trading Signals', description: 'New buy/sell recommendations' },
                    { key: 'portfolio', label: 'Portfolio Updates', description: 'Position changes and performance updates' },
                    { key: 'email', label: 'Email Notifications', description: 'Send notifications to your email' },
                    { key: 'push', label: 'Push Notifications', description: 'Browser push notifications' },
                  ].map((item) => (
                    <div key={item.key} className="flex items-center justify-between p-4 bg-secondary-50 rounded-lg">
                      <div>
                        <div className="font-medium text-secondary-900">{item.label}</div>
                        <div className="text-sm text-secondary-600">{item.description}</div>
                      </div>
                      <button
                        onClick={() => updateSettings('notifications', item.key, !settings.notifications[item.key as keyof typeof settings.notifications])}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          settings.notifications[item.key as keyof typeof settings.notifications]
                            ? 'bg-primary-600'
                            : 'bg-secondary-300'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            settings.notifications[item.key as keyof typeof settings.notifications]
                              ? 'translate-x-6'
                              : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Risk Management Settings */}
          {activeTab === 'risk' && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-6"
            >
              <Card>
                <CardHeader>
                  <CardTitle>Risk Parameters</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Maximum Position Size (% of portfolio)
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="1"
                        max="50"
                        value={settings.risk.maxPositionSize}
                        onChange={(e) => updateSettings('risk', 'maxPositionSize', parseInt(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-medium text-secondary-900 w-12">
                        {settings.risk.maxPositionSize}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Maximum Drawdown Threshold (%)
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="5"
                        max="30"
                        value={settings.risk.maxDrawdown}
                        onChange={(e) => updateSettings('risk', 'maxDrawdown', parseInt(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-medium text-secondary-900 w-12">
                        {settings.risk.maxDrawdown}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Stop Loss Level (%)
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="1"
                        max="20"
                        value={settings.risk.stopLoss}
                        onChange={(e) => updateSettings('risk', 'stopLoss', parseInt(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-medium text-secondary-900 w-12">
                        {settings.risk.stopLoss}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Alert Threshold - Signal Confidence (%)
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min="50"
                        max="95"
                        value={settings.risk.alertThreshold}
                        onChange={(e) => updateSettings('risk', 'alertThreshold', parseInt(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-sm font-medium text-secondary-900 w-12">
                        {settings.risk.alertThreshold}%
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Trading Settings */}
          {activeTab === 'trading' && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="space-y-6"
            >
              <Card>
                <CardHeader>
                  <CardTitle>Trading Preferences</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {[
                    {
                      key: 'autoTrading',
                      label: 'Auto Trading',
                      description: 'Automatically execute high-confidence signals',
                      warning: true,
                    },
                    {
                      key: 'confirmTrades',
                      label: 'Confirm Trades',
                      description: 'Require confirmation before executing trades',
                    },
                    {
                      key: 'marketHoursOnly',
                      label: 'Market Hours Only',
                      description: 'Only generate signals during market hours',
                    },
                  ].map((item) => (
                    <div key={item.key} className="flex items-center justify-between p-4 bg-secondary-50 rounded-lg">
                      <div>
                        <div className="flex items-center gap-2">
                          <div className="font-medium text-secondary-900">{item.label}</div>
                          {item.warning && (
                            <Badge variant="warning" size="sm">
                              High Risk
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm text-secondary-600">{item.description}</div>
                      </div>
                      <button
                        onClick={() => updateSettings('trading', item.key, !settings.trading[item.key as keyof typeof settings.trading])}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          settings.trading[item.key as keyof typeof settings.trading]
                            ? 'bg-primary-600'
                            : 'bg-secondary-300'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            settings.trading[item.key as keyof typeof settings.trading]
                              ? 'translate-x-6'
                              : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {settings.trading.autoTrading && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-warning-500" />
                      Auto Trading Warning
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="bg-warning-50 border border-warning-200 rounded-lg p-4">
                      <p className="text-warning-700 text-sm">
                        Auto trading is enabled. This means the system will automatically execute trades
                        based on AI recommendations. Please ensure you understand the risks and have
                        appropriate risk management settings in place.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </motion.div>
          )}
        </div>
      </div>

      {/* Changes Indicator */}
      {hasChanges && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="fixed bottom-6 right-6 bg-primary-600 text-white px-4 py-2 rounded-lg shadow-lg"
        >
          You have unsaved changes
        </motion.div>
      )}
    </div>
  );
};

export default Settings;
