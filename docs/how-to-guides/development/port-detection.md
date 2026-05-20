# Automatic Port Detection Guide

## 🎯 **PORT CONFLICTS ARE NOW SOLVED!**

All startup scripts now automatically detect available ports and increment until they find an open one. No more manual port changes required!

---

## **🚀 HOW IT WORKS**

### **Port Detection Logic**
1. **Check Default Port** - Start with default (8000 for backend, 3000 for frontend)
2. **Port Test** - Check if port is available using system tools
3. **Increment** - If busy, try next port (8001, 8002, etc.)
4. **Found!** - Use the first available port
5. **Update Config** - Automatically update environment variables
6. **Start Service** - Launch with the detected port

### **Detection Methods**
- **Primary**: `nc` (netcat) - Most reliable
- **Secondary**: `lsof` - Linux port listing
- **Tertiary**: `ss` - Modern Linux socket stats
- **Fallback**: TCP connection attempt

---

## **📋 UPDATED SCRIPTS**

### **Backend Script** (`./scripts/start-backend.sh`)
```bash
# Automatically finds port starting from 8000
./scripts/start-backend.sh

# Output example:
# 🔍 Checking for available ports starting from 8000...
# ⏳ Port 8000 is in use, trying next...
# ✅ Found available port: 8001
# ✅ Backend starting on http://localhost:8001
```

### **Frontend Dev Script** (`./scripts/frontend-dev.sh dev`)
```bash
# Automatically finds port starting from 3000
./scripts/frontend-dev.sh dev

# Output example:
# 🔍 Checking for available ports starting from 3000...
# ✅ Found available port: 3000
# ✅ Frontend will be available at: http://localhost:3000
# ✅ Backend API detected at: http://localhost:8000
```

### **Frontend Standalone** (`./scripts/frontend-standalone.sh`)
```bash
# Automatically finds port starting from 3000
./scripts/frontend-standalone.sh

# Output example:
# 🔍 Checking for available ports starting from 3000...
# ⏳ Port 3000 is in use, trying next...
# ✅ Found available port: 3001
# ✅ Frontend will start on: http://localhost:3001
```

---

## **🎮 MULTIPLE INSTANCES**

### **Running Multiple Backends**
```bash
# Terminal 1 - Backend 1
./scripts/start-backend.sh
# Backend 1 starts on port 8000

# Terminal 2 - Backend 2
./scripts/start-backend.sh
# Backend 2 automatically starts on port 8001

# Terminal 3 - Backend 3
./scripts/start-backend.sh
# Backend 3 automatically starts on port 8002
```

### **Running Multiple Frontends**
```bash
# Terminal 1 - Frontend 1
./scripts/frontend-dev.sh dev
# Frontend 1 starts on port 3000

# Terminal 2 - Frontend 2
./scripts/frontend-dev.sh dev
# Frontend 2 automatically starts on port 3001

# Terminal 3 - Frontend 3
./scripts/frontend-standalone.sh
# Frontend 3 automatically starts on port 3002
```

### **Mixed Setup**
```bash
# Terminal 1 - Backend (auto port)
./scripts/start-backend.sh

# Terminal 2 - Frontend 1 (auto port)
./scripts/frontend-dev.sh dev

# Terminal 3 - Frontend 2 Standalone (auto port)
./scripts/frontend-standalone.sh
```

---

## **🔧 CONFIGURATION UPDATES**

### **Environment Variables Automatically Updated**
When ports differ from defaults:

**Backend Environment (`.env`):**
```env
# If backend starts on 8001:
API_PORT=8001
API_HOST=0.0.0.0
```

**Frontend Environment (passed via command line):**
```bash
# If frontend starts on 3001:
PORT=3001 npm run dev
```

### **Automatic Standalone Mode Detection**
The frontend script automatically detects if backend is available:

```bash
# If port 8000 is available → Full Stack Mode
✅ Backend API detected at: http://localhost:8000

# If port 8000 is NOT available → Standalone Mode
⚠️ Backend API not detected on default port 8000
💡 Frontend will run in standalone mode
📝 Configuring standalone mode...
✅ Standalone mode configured
```

---

## **🔧 ADVANCED CONFIGURATION**

### **Change Port Detection Settings**
Edit `scripts/port-utility.sh`:

```bash
# Change maximum port attempts
MAX_ATTEMPTS=50  # Try up to 50 ports

# Change default starting ports
DEFAULT_BACKEND_PORT=8080
DEFAULT_FRONTEND_PORT=8080
```

### **Manual Port Checking**
```bash
# Test port utility directly
source scripts/port-utility.sh

# Check specific port
is_port_available 8000 && echo "Available" || echo "Busy"

# Find next available port
find_available_port 8000
# Output: 8001 (if 8000 is busy)
```

### **Force Specific Port Range**
```bash
# Backend on specific port range
API_PORT=9000 ./scripts/start-backend.sh

# Frontend on specific port range
PORT=9001 ./scripts/frontend-dev.sh dev
```

---

## **🌟 INTELLIGENT FEATURES**

### **Smart Mode Switching**
- **Backend detected** → Full stack mode with real API
- **Backend missing** → Automatic standalone mode with mock data
- **No manual configuration required**

### **Cross-Platform Support**
- Works on Linux, macOS, and Windows
- Multiple port detection methods
- Graceful fallbacks for different systems

### **Error Handling**
- **Maximum attempts** - Fails gracefully after trying N ports
- **Clear messages** - Shows exactly which ports were tested
- **Cleanup** - Proper error messages and exit codes

---

## **🎯 USE CASES**

### **Development Teams**
- **Team members** can run scripts without port conflicts
- **Multiple environments** (dev, staging, testing) simultaneously
- **No coordination** required for port assignment

### **CI/CD Pipelines**
- **Automated testing** can run multiple instances
- **Parallel execution** without port management
- **Dynamic port allocation** for build agents

### **Local Development**
- **Quick restarts** without manual port changes
- **Multiple projects** running simultaneously
- **Zero configuration** for different setups

---

## **📊 EXAMPLE OUTPUTS**

### **Successful Port Detection**
```
🔍 Checking for available ports starting from 8000...
⏳ Port 8000 is in use, trying next...
⏳ Port 8001 is in use, trying next...
✅ Found available port: 8002
✅ Backend starting on http://localhost:8002
📖 API docs will be available at http://localhost:8002/docs
```

### **Port Not Found**
```
🔍 Checking for available ports starting from 8000...
⏳ Port 8000 is in use, trying next...
⏳ Port 8001 is in use, trying next...
...
⏳ Port 8019 is in use, trying next...
❌ No available ports found in range 8000-8019
```

### **Smart Mode Detection**
```
🔍 Checking for available ports starting from 3000...
✅ Found available port: 3000
✅ Frontend will be available at: http://localhost:3000
⚠️ Backend API not detected on default port 8000
💡 Frontend will run in standalone mode
📝 Configuring standalone mode...
✅ Standalone mode configured
```

---

## **🎉 SUCCESS!**

**Port conflicts are now completely automated!** 🎊

### **No More Manual Steps**
- ❌ No more editing `.env` files manually
- ❌ No more killing processes on ports
- ❌ No more checking what's running where
- ❌ No more coordination between team members

### **Just Run Your Scripts!**
```bash
./scripts/start-backend.sh        # Any number of instances
./scripts/frontend-dev.sh dev     # Any number of instances
./scripts/frontend-standalone.sh  # Any number of instances
```

**Everything works automatically!** 🚀