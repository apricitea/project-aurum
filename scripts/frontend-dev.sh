#!/bin/bash

# Frontend Development Script
# This script ensures commands are run from the correct directory
# Supports automatic port detection

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/apps/web_dashboard/frontend"

# Source port utility
source "$SCRIPT_DIR/port-utility.sh"

echo -e "${BLUE}🚀 Project Aurum Frontend Development Script${NC}"
echo "========================================="

# Function to check if we're in the right directory
check_directory() {
    local current_dir=$(pwd)
    if [[ "$current_dir" != "$FRONTEND_DIR" ]]; then
        echo -e "${YELLOW}⚠️  WARNING: Not in frontend directory${NC}"
        echo -e "Current: ${RED}$current_dir${NC}"
        echo -e "Expected: ${GREEN}$FRONTEND_DIR${NC}"
        echo ""
        read -p "Do you want to switch to the frontend directory? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$FRONTEND_DIR"
            echo -e "${GREEN}✓ Switched to frontend directory${NC}"
            echo -e "Now in: $(pwd)${NC}"
        else
            echo -e "${RED}❌ Cannot continue. Please run from frontend directory.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Already in correct directory: $(pwd)${NC}"
    fi
}

# Function to check if Node.js is installed
check_nodejs() {
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js is not installed${NC}"
        echo "Please install Node.js 18+ from https://nodejs.org/"
        exit 1
    fi

    local node_version=$(node --version | cut -d'v' -f2)
    echo -e "${GREEN}✓ Node.js version: $node_version${NC}"
}

# Function to check if dependencies are installed
check_dependencies() {
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}⚠️  Dependencies not found. Installing...${NC}"
        npm install
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    else
        echo -e "${GREEN}✓ Dependencies already installed${NC}"
    fi
}

# Function to check if backend is running
check_backend() {
    if curl -s http://localhost:8000/health &> /dev/null; then
        echo -e "${GREEN}✓ Backend is running on http://localhost:8000${NC}"
    else
        echo -e "${YELLOW}⚠️  Backend may not be running on http://localhost:8000${NC}"
        echo "Make sure to start the backend before running the frontend:"
        echo "  cd $PROJECT_ROOT"
        echo "  source .venv/bin/activate"
        echo "  python main.py"
        echo ""
    fi
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  dev       Start development server"
    echo "  build     Build for production"
    echo "  preview   Preview production build"
    echo "  check     Run type checking and linting"
    echo "  install   Install dependencies"
    echo "  clean     Clean node_modules and dist"
    echo "  help      Show this help message"
    echo ""
    echo "If no command is provided, defaults to 'dev'"
}

# Main script execution
main() {
    local command=${1:-dev}

    case "$command" in
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
        "install")
            echo -e "${BLUE}📦 Installing dependencies...${NC}"
            check_directory
            check_nodejs
            npm install
            echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
            exit 0
            ;;
        "clean")
            echo -e "${BLUE}🧹 Cleaning up...${NC}"
            check_directory
            rm -rf node_modules dist package-lock.json
            echo -e "${GREEN}✓ Cleaned node_modules and dist${NC}"
            exit 0
            ;;
        "check")
            echo -e "${BLUE}🔍 Running code quality checks...${NC}"
            check_directory
            echo "Running type check..."
            npm run type-check
            echo "Running linter..."
            npm run lint
            echo -e "${GREEN}✓ All checks passed${NC}"
            exit 0
            ;;
    esac

    # For other commands, perform setup checks
    check_directory
    check_nodejs
    check_dependencies
    check_backend

    echo ""
    echo -e "${BLUE}🎯 Running: npm run $command${NC}"
    echo "========================================="

    case "$command" in
        "dev")
            echo -e "${GREEN}🌟 Starting development server...${NC}"

            # Find available port for frontend
            DEFAULT_FRONTEND_PORT=3000
            FRONTEND_PORT=$(find_available_port $DEFAULT_FRONTEND_PORT)

            if [[ -z "$FRONTEND_PORT" ]]; then
                echo -e "${RED}❌ Failed to find available port for frontend${NC}"
                exit 1
            fi

            echo -e "${GREEN}✅ Frontend will be available at: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"

            # Try to detect backend port
            BACKEND_PORT=8000
            if is_port_available "$BACKEND_PORT"; then
                echo -e "${YELLOW}⚠️  Backend API not detected on default port 8000${NC}"
                echo -e "${YELLOW}💡 Frontend will run in standalone mode${NC}"

                # Configure standalone mode
                echo -e "${BLUE}📝 Configuring standalone mode...${NC}"
                cp .env.standalone .env 2>/dev/null || echo "Standalone env already exists"
                echo -e "${GREEN}✅ Standalone mode configured${NC}"
            else
                echo -e "${GREEN}✅ Backend API detected at: ${BLUE}http://localhost:$BACKEND_PORT${NC}"
            fi

            echo ""
            echo "Press Ctrl+C to stop the server"
            echo ""

            # Start frontend with custom port
            if [[ "$FRONTEND_PORT" != "$DEFAULT_FRONTEND_PORT" ]]; then
                PORT="$FRONTEND_PORT" npm run dev
            else
                npm run dev
            fi
            ;;
        "build")
            echo -e "${GREEN}🏗️  Building for production...${NC}"
            npm run build
            echo -e "${GREEN}✓ Build completed successfully${NC}"
            echo -e "Output in: ${BLUE}dist/${NC}"
            ;;
        "preview")
            echo -e "${GREEN}👀 Starting preview server...${NC}"
            echo -e "Preview will be available at: ${BLUE}http://localhost:4173${NC}"
            npm run preview
            ;;
        *)
            echo -e "${RED}❌ Unknown command: $command${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"