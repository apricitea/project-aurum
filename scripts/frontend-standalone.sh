#!/bin/bash

# Frontend Standalone Mode Script
# Runs frontend with mock data - no backend required!

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/apps/web_dashboard/frontend"

echo -e "${BLUE}🚀 Project Aurum Frontend - Standalone Mode${NC}"
echo "========================================"
echo -e "${CYAN}Frontend with Mock Data (No Backend Required!)${NC}"
echo ""

# Check if we're in the project root
if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    echo -e "${RED}❌ Error: pyproject.toml not found. Make sure you're in the project root.${NC}"
    exit 1
fi

# Function to check if Node.js is installed
check_nodejs() {
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js is not installed${NC}"
        echo "Please install Node.js 18+ from https://nodejs.org/"
        exit 1
    fi

    local node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ "$node_version" -lt 18 ]]; then
        echo -e "${RED}❌ Node.js version $node_version is too old. Requires 18+${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Node.js $(node --version) detected${NC}"
}

# Function to setup standalone environment
setup_standalone_env() {
    cd "$FRONTEND_DIR"

    echo -e "${YELLOW}📋 Setting up standalone environment...${NC}"

    # Create standalone .env file if it doesn't exist
    if [[ ! -f ".env" ]]; then
        echo -e "${YELLOW}Creating .env file for standalone mode...${NC}"
        cp .env.standalone .env
    else
        # Check if current .env has mock mode enabled
        if ! grep -q "VITE_MOCK_MODE=true" .env; then
            echo -e "${YELLOW}Updating .env for standalone mode...${NC}"
            # Backup current .env
            cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
            # Update with standalone config
            cp .env.standalone .env
        fi
    fi

    echo -e "${GREEN}✓ Standalone environment configured${NC}"
    echo -e "${CYAN}📁 .env file configured with mock data settings${NC}"
}

# Function to install dependencies
install_dependencies() {
    cd "$FRONTEND_DIR"

    echo -e "${YELLOW}📦 Checking dependencies...${NC}"

    if [[ ! -d "node_modules" ]]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        npm install
    else
        echo -e "${GREEN}✓ Dependencies already installed${NC}"

        # Check if package-lock.json has changed
        if [[ "package-lock.json" -nt "node_modules" ]]; then
            echo -e "${YELLOW}Dependencies may be outdated, updating...${NC}"
            npm install
        fi
    fi

    echo -e "${GREEN}✓ Dependencies ready${NC}"
}

# Function to display standalone mode information
show_standalone_info() {
    echo ""
    echo -e "${CYAN}🎯 Standalone Mode Features:${NC}"
    echo "  • 🎨 Real-time mock trading data"
    echo "  • 📊 Portfolio with realistic performance"
    echo "  • ⚠️  Risk monitoring and alerts"
    echo "  • 📈 Trading signals with Indonesian stocks"
    echo "  • 🔄 Live data updates (simulated)"
    echo "  • 🔐 Demo login (demo/demo)"
    echo ""
    echo -e "${CYAN}📱 What You Can Do:${NC}"
    echo "  • View and analyze trading signals"
    echo "  • Monitor portfolio performance"
    echo "  • Check risk metrics and alerts"
    echo "  • Test all UI features and components"
    echo "  • Develop and style the frontend"
    echo ""
    echo -e "${YELLOW}⚠️  Limitations:${NC}"
    echo "  • No real trading execution"
    echo "  • No real market data"
    echo "  • No user authentication persistence"
    echo "  • No API rate limits or real latency"
    echo ""
    echo -e "${BLUE}🔐 Demo Login:${NC}"
    echo "  Username: ${GREEN}demo${NC}"
    echo "  Password: ${GREEN}demo${NC}"
    echo ""
}

# Function to start the frontend
start_frontend() {
    cd "$FRONTEND_DIR"

    echo -e "${YELLOW}🚀 Starting frontend development server...${NC}"
    echo ""
    echo -e "${GREEN}✅ Frontend will start on: http://localhost:3000${NC}"
    echo -e "${GREEN}✅ Mock data will automatically load${NC}"
    echo -e "${GREEN}✅ Real-time updates enabled${NC}"
    echo ""
    echo -e "${CYAN}🛠️  Development Commands:${NC}"
    echo "  • npm run type-check    # Check TypeScript"
    echo "  • npm run build         # Build for production"
    echo "  • npm run lint          # Run linting"
    echo ""
    echo -e "${YELLOW}⏹️  Press CTRL+C to stop${NC}"
    echo ""

    # Start the development server
    if command -v npm &> /dev/null; then
        npm run dev
    else
        echo -e "${RED}❌ npm not found. Please install Node.js and npm.${NC}"
        exit 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}📍 Frontend Directory: $FRONTEND_DIR${NC}"

    check_nodejs
    setup_standalone_env
    install_dependencies
    show_standalone_info
    start_frontend
}

# Handle script interruption
trap 'echo -e "\n${YELLOW}👋 Standalone frontend stopped.${NC}"' EXIT

# Run main function
main "$@"