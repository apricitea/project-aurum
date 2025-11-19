import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useAuthStore } from './store/auth';
import { useDashboardStore } from './store/dashboard';

const MinimalDashboard: React.FC = () => {
  const { loadDashboardData, signals, portfolio, isLoading, error } = useDashboardStore();
  const [debugInfo, setDebugInfo] = React.useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        setDebugInfo('Starting to load dashboard data...');
        await loadDashboardData();
        setDebugInfo('Dashboard data loaded successfully');
      } catch (err) {
        setDebugInfo(`Error loading data: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    };
    loadData();
  }, [loadDashboardData]);

  // Always show debug info for troubleshooting
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Project Aurum Dashboard</h1>

      <div className="mb-4 p-4 bg-gray-100 rounded">
        <h3 className="font-bold">Debug Info:</h3>
        <p>Loading: {isLoading ? 'Yes' : 'No'}</p>
        <p>Error: {error || 'None'}</p>
        <p>Signals count: {signals?.length || 0}</p>
        <p>Portfolio: {portfolio ? 'Loaded' : 'Not loaded'}</p>
        <p>Debug: {debugInfo}</p>
      </div>

      {isLoading && (
        <div className="text-blue-600">Loading dashboard data...</div>
      )}

      {error && (
        <div className="text-red-600 mb-4">Error: {error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Portfolio Summary</h2>
          {portfolio ? (
            <div>
              <p>Total Value: Rp {portfolio.total_value?.toLocaleString() || 'N/A'}</p>
              <p>Daily P&L: Rp {portfolio.daily_pnl?.toLocaleString() || 'N/A'}</p>
              <p>Positions: {portfolio.positions_count || 0}</p>
            </div>
          ) : (
            <p>No portfolio data available</p>
          )}
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Trading Signals</h2>
          {signals && signals.length > 0 ? (
            <div className="space-y-2">
              {signals.slice(0, 3).map((signal, index) => (
                <div key={index} className="border-l-4 border-blue-500 pl-3">
                  <p className="font-medium">{signal.stock_code}</p>
                  <p className="text-sm text-gray-600">{signal.signal} - {(signal.confidence * 100).toFixed(0)}%</p>
                </div>
              ))}
            </div>
          ) : (
            <p>No signals available</p>
          )}
        </div>
      </div>
    </div>
  );
};

const Login: React.FC = () => {
  const { login, isLoading, error } = useAuthStore();
  const [credentials, setCredentials] = React.useState({ username: '', password: '' });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(credentials);
    } catch (err) {
      console.error('Login failed:', err);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white p-8 rounded-lg shadow">
        <h1 className="text-2xl font-bold text-center mb-6">Project Aurum Login</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Username</label>
            <input
              type="text"
              value={credentials.username}
              onChange={(e) => setCredentials({...credentials, username: e.target.value})}
              className="w-full px-3 py-2 border rounded-md"
              placeholder="admin or trader"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Password</label>
            <input
              type="password"
              value={credentials.password}
              onChange={(e) => setCredentials({...credentials, password: e.target.value})}
              className="w-full px-3 py-2 border rounded-md"
              placeholder="admin123 or trader123"
              required
            />
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const { isAuthenticated, loadUser, isLoading } = useAuthStore();

  useEffect(() => {
    if (localStorage.getItem('auth_token')) {
      loadUser();
    }
  }, [loadUser]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        {isAuthenticated ? (
          <Route path="*" element={<MinimalDashboard />} />
        ) : (
          <Route path="*" element={<Login />} />
        )}
      </Routes>
    </Router>
  );
};

export default App;