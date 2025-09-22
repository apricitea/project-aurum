import React, { useState } from 'react';

const LoginPage: React.FC = () => {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState<any>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      localStorage.setItem('auth_token', data.access_token);
      setUser(data.user);
      setIsLoggedIn(true);
    } catch (err) {
      setError('Invalid username or password');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    setIsLoggedIn(false);
    setUser(null);
  };

  if (isLoggedIn) {
    return (
      <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
          <h1 style={{ color: '#2563eb', margin: 0 }}>Project Aurum - Indonesian Trading System</h1>
          <button
            onClick={handleLogout}
            style={{
              padding: '8px 16px',
              backgroundColor: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Logout
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div style={{ padding: '20px', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
            <h2 style={{ color: '#374151', marginTop: 0 }}>Welcome, {user?.username}!</h2>
            <p>Role: <strong>{user?.role}</strong></p>
            <p>Email: <strong>{user?.email}</strong></p>
          </div>

          <div style={{ padding: '20px', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
            <h3 style={{ color: '#374151', marginTop: 0 }}>Portfolio Summary</h3>
            <p>Total Value: <strong>Rp 150,000,000</strong></p>
            <p>Daily P&L: <strong style={{ color: '#059669' }}>+Rp 2,500,000 (+1.67%)</strong></p>
            <p>Positions: <strong>8 stocks</strong></p>
          </div>
        </div>

        <div style={{ marginTop: '30px', padding: '20px', backgroundColor: '#f0f9ff', borderRadius: '8px' }}>
          <h3 style={{ color: '#1e40af', marginTop: 0 }}>Today's Top Signals 🇮🇩</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div style={{ padding: '15px', backgroundColor: 'white', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#059669' }}>BBCA.JK - BUY</h4>
              <p style={{ margin: '4px 0', fontSize: '14px' }}>Bank Central Asia Tbk</p>
              <p style={{ margin: '4px 0', fontSize: '14px' }}>Price: Rp 9,750 → Target: Rp 10,500</p>
              <p style={{ margin: '4px 0', fontSize: '14px' }}>Confidence: <strong>85%</strong></p>
            </div>
            <div style={{ padding: '15px', backgroundColor: 'white', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#d97706' }}>BMRI.JK - HOLD</h4>
              <p style={{ margin: '4px 0', fontSize: '14px' }}>Bank Mandiri Tbk</p>
              <p style={{ margin: '4px 0', fontSize: '14px' }}>Price: Rp 5,425 → Target: Rp 5,800</p>
              <p style={{ margin: '4px 0', fontSize: '14px' }}>Confidence: <strong>65%</strong></p>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '30px', padding: '20px', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
          <h3 style={{ color: '#374151', marginTop: 0 }}>Market Status</h3>
          <p>Jakarta Composite Index (JCI): <strong>7,234.56 (+0.87%)</strong></p>
          <p>LQ45 Index: <strong>985.23 (+0.86%)</strong></p>
          <p>Market Status: <strong style={{ color: '#059669' }}>OPEN</strong></p>
          <p>Time Zone: Asia/Jakarta (WIB)</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#f9fafb',
      fontFamily: 'Arial, sans-serif'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        padding: '40px',
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <h1 style={{ color: '#2563eb', margin: '0 0 8px 0' }}>Project Aurum</h1>
          <p style={{ color: '#6b7280', margin: 0 }}>Indonesian Quantitative Trading System</p>
        </div>

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', color: '#374151', fontWeight: '500' }}>
              Username
            </label>
            <input
              type="text"
              value={credentials.username}
              onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                fontSize: '16px',
                boxSizing: 'border-box'
              }}
              placeholder="Enter username (admin or trader)"
              required
            />
          </div>

          <div style={{ marginBottom: '25px' }}>
            <label style={{ display: 'block', marginBottom: '8px', color: '#374151', fontWeight: '500' }}>
              Password
            </label>
            <input
              type="password"
              value={credentials.password}
              onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                fontSize: '16px',
                boxSizing: 'border-box'
              }}
              placeholder="Enter password"
              required
            />
          </div>

          {error && (
            <div style={{
              padding: '12px',
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '4px',
              color: '#dc2626',
              marginBottom: '20px',
              fontSize: '14px'
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: isLoading ? '#9ca3af' : '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '16px',
              fontWeight: '500',
              cursor: isLoading ? 'not-allowed' : 'pointer'
            }}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div style={{ marginTop: '25px', padding: '15px', backgroundColor: '#f0f9ff', borderRadius: '4px' }}>
          <p style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: '500', color: '#1e40af' }}>Demo Credentials:</p>
          <p style={{ margin: '4px 0', fontSize: '13px', color: '#374151' }}>Username: <code>admin</code> Password: <code>admin123</code></p>
          <p style={{ margin: '4px 0', fontSize: '13px', color: '#374151' }}>Username: <code>trader</code> Password: <code>trader123</code></p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;