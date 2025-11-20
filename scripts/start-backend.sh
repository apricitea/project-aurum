#!/bin/bash

# Backend startup script for Project Aurum
# This script starts the FastAPI backend server with automatic port detection

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

# Source port utility
source "$SCRIPT_DIR/port-utility.sh"

echo -e "${BLUE}🚀 Starting Project Aurum Backend${NC}"
echo "================================"

# Check if we're in the project root
if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    echo -e "${RED}❌ Error: pyproject.toml not found. Make sure you're in the project root.${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ Error: uv is not installed. Install it from https://github.com/astral-sh/uv${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Project root: $(pwd)${NC}"

# Check if dependencies are installed
if [[ ! -d ".venv" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Installing dependencies...${NC}"
    uv sync
else
    echo -e "${GREEN}✓ Virtual environment found${NC}"
fi

echo ""

# Find available port for backend
DEFAULT_BACKEND_PORT=8000
BACKEND_PORT=$(find_available_port $DEFAULT_BACKEND_PORT)

if [[ -z "$BACKEND_PORT" ]]; then
    echo -e "${RED}❌ Failed to find available port for backend${NC}"
    exit 1
fi

# Update API_PORT in environment if different from default
if [[ "$BACKEND_PORT" != "$DEFAULT_BACKEND_PORT" ]]; then
    update_port_in_config ".env" "API_PORT" "$BACKEND_PORT" "Backend"
    update_port_in_config ".env" "API_HOST" "0.0.0.0" "Backend"
fi

echo ""
echo -e "${BLUE}🔥 Starting FastAPI backend server...${NC}"

# Start the backend with dynamic port
echo -e "${GREEN}✅ Backend starting on http://localhost:$BACKEND_PORT${NC}"
echo -e "${GREEN}📖 API docs will be available at http://localhost:$BACKEND_PORT/docs${NC}"
echo -e "${GREEN}⏹️  Press CTRL+C to stop${NC}"
echo ""

# Start the backend with custom port
API_PORT="$BACKEND_PORT" uv run python main.py --start