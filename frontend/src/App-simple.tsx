import React from 'react';

const App: React.FC = () => {
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#2563eb' }}>Project Aurum - Indonesian Trading System</h1>
      <p>Frontend is working! 🎉</p>
      <div style={{ marginTop: '20px', padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
        <h2>System Status</h2>
        <ul>
          <li>✅ Frontend Server: Running on port 3001</li>
          <li>✅ Backend API: Running on port 8000</li>
          <li>✅ React Application: Loaded successfully</li>
        </ul>
      </div>
      <div style={{ marginTop: '20px', padding: '20px', backgroundColor: '#f0f9ff', borderRadius: '8px' }}>
        <h3>Next Steps</h3>
        <p>Navigate to the login page to access the trading dashboard.</p>
        <button
          style={{
            padding: '10px 20px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
          onClick={() => window.location.href = '/login'}
        >
          Go to Login
        </button>
      </div>
    </div>
  );
};

export default App;