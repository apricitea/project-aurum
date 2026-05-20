# Frontend Standalone Mode - Development & Testing

Run the complete Project Aurum frontend **without any backend required!** Perfect for frontend development, UI testing, demos, and presentations.

## 🎯 What You Get

✅ **Complete Indonesian Trading Dashboard** - Full frontend experience
✅ **Realistic Mock Data** - Indonesian stocks (BBCA, BBRI, TLKM, etc.)
✅ **Real-time Updates** - Simulated price movements and alerts
✅ **All Features Working** - Signals, portfolio, risk monitoring, analytics
✅ **Zero Setup Required** - No backend, database, or external APIs needed

---

## 🚀 Quick Start (2 Ways)

### **Method 1: Automated Script (Recommended)**
```bash
# From project root
./scripts/frontend-standalone.sh
```

### **Method 2: Manual Setup**
```bash
# From frontend directory
cd apps/web_dashboard/frontend

# Configure standalone mode
cp .env.standalone .env

# Start frontend
npm run dev
```

**Frontend will run on:** `http://localhost:3000`

---

## 🎮 Demo Login

Once the frontend is running, you can login with:

**Username:** `demo`
**Password:** `demo`

---

## 🌟 Features Available

### 📊 Trading Dashboard
- **Live Trading Signals** - Realistic BUY/SELL/HOLD signals for Indonesian stocks
- **Signal Analytics** - Confidence scores, performance metrics, daily summaries
- **Interactive Charts** - Price movements, signal distribution, portfolio trends

### 💼 Portfolio Management
- **Portfolio Overview** - Total value, P&L, performance analytics
- **Position Tracking** - Individual stock positions with real-time updates
- **Risk Metrics** - Value at Risk, beta, diversification scores

### ⚠️ Alert System
- **Real-time Alerts** - Price alerts, volume spikes, risk warnings
- **Alert Management** - Acknowledge, dismiss, prioritize alerts
- **Smart Notifications** - Priority-based alert handling

### 📈 Market Analysis
- **Indonesian Market Status** - IDX trading hours, session types
- **Stock Performance** - Realistic Indonesian stock data
- **Risk Analytics** - Portfolio risk monitoring and metrics

### 🔔 Real-time Features
- **WebSocket Simulation** - Live data updates every 3-5 seconds
- **Price Movements** - Simulated realistic price fluctuations
- **Dynamic Alerts** - New alerts generated periodically

---

## 📱 Data Available

### Indonesian Stocks (Mock Data)
- **BBCA** (Bank Central Asia)
- **BBRI** (Bank BRI)
- **BBNI** (Bank BNI)
- **TLKM** (Telkom Indonesia)
- **UNVR** (Unilever Indonesia)
- **ASII** (Astra International)
- **And 25+ more Indonesian stocks**

### Realistic Data
- **Stock Prices** - Realistic IDR pricing with volatility
- **Trading Signals** - BUY/SELL/HOLD with confidence scores
- **Portfolio Metrics** - P&L, position sizes, sector breakdowns
- **Risk Analytics** - Value at Risk, beta, correlation metrics
- **Market Data** - IDX market hours, trading sessions

---

## 🛠️ Development Features

### Hot Reloading
- All changes to frontend code auto-reload
- Mock data updates in real-time
- Instant UI/UX testing feedback

### TypeScript Support
- Full type checking and IntelliSense
- Mock API matches real API types
- Development-friendly error messages

### Responsive Design
- Mobile, tablet, and desktop layouts
- Tailwind CSS for rapid styling
- Dark/light theme support

---

## 🔧 Configuration Options

### Environment Variables (.env.standalone)
```env
VITE_MOCK_MODE=true                    # Enable mock data
VITE_MOCK_DATA_REFRESH_INTERVAL=5000   # Update every 5 seconds
VITE_REAL_TIME_UPDATES=true            # Enable real-time updates
VITE_APP_TITLE="Project Aurum - Demo" # App title
VITE_DEV_TOOLS=true                     # Enable dev tools
```

### Customizing Mock Data
Edit `src/lib/mock-api.ts` to:
- Add more stocks or modify existing ones
- Adjust data refresh intervals
- Customize alert types and priorities
- Modify portfolio initial values

---

## 🎯 Use Cases

### ✅ Perfect For:
- **Frontend Development** - UI/UX work without backend dependency
- **Presentations & Demos** - Show complete app functionality
- **Testing & QA** - Test frontend features independently
- **Design Reviews** - Visual and interaction testing
- **Stakeholder Demos** - Impress clients with full features

### ❌ Not For:
- **Real Trading** - Uses mock/simulated data only
- **Production Use** - No real market data or trading execution
- **Data Analysis** - All data is simulated
- **Real-time Trading** - No actual market connectivity

---

## 🔄 Switching Between Modes

### Standalone → Full Stack
```bash
# Restore production .env
rm .env
cp .env.example .env

# Start backend (Terminal 1)
./scripts/start-backend.sh

# Start frontend (Terminal 2)
./scripts/frontend-dev.sh dev
```

### Full Stack → Standalone
```bash
# Stop backend (CTRL+C)
# Configure standalone mode
./scripts/frontend-standalone.sh
```

---

## 📋 Troubleshooting

### Issue: Frontend won't start
**Solution:** Check Node.js version (needs 18+)
```bash
node --version  # Should be 18.x or higher
```

### Issue: Mock data not loading
**Solution:** Ensure `.env` has `VITE_MOCK_MODE=true`
```bash
cat .env | grep MOCK_MODE
```

### Issue: Real-time updates not working
**Solution:** Check browser console for errors and ensure WebSocket is not blocked

### Issue: Login not working
**Solution:** Use demo/demo credentials. They're hard-coded for mock mode.

---

## 🎨 Visual Indicators

When in standalone mode, you'll see:
- **Blue Banner** at top indicating "Standalone Mode"
- **Green pulsing dots** showing live mock data updates
- **"Demo Data" badges** throughout the interface
- **Login提示** showing demo credentials

---

## 📚 Technical Details

### Mock API Architecture
- **MockApiClient** - Mirrors real API with simulated responses
- **MockWebSocketClient** - Simulates real-time data updates
- **Realistic Data** - Indonesian stock prices, volumes, market data
- **Type Safety** - Full TypeScript compatibility with real types

### Data Simulation
- **Price Movements** - ±2% volatility with realistic patterns
- **Signal Generation** - BUY/SELL/HOLD with confidence scores
- **Portfolio Updates** - Real-time P&L and position changes
- **Alert Generation** - Periodic new alerts and notifications

---

## 🚀 Ready to Start!

**Just run one command:**
```bash
./scripts/frontend-standalone.sh
```

Then visit `http://localhost:3000` and login with `demo/demo`.

**Complete Indonesian trading dashboard ready in 60 seconds!** 🎉

---

## 📞 Support & Questions

For issues or questions about the standalone mode:
1. Check this guide first
2. Review `FRONTEND-SETUP.md` for general frontend setup
3. Check the browser console for specific error messages
4. Verify Node.js 18+ is installed

Happy frontend development! 🎨📈