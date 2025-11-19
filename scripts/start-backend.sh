#!/bin/bash

# Backend startup script for Project Aurum
# This script starts the FastAPI backend server

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
echo -e "${BLUE}🔥 Starting FastAPI backend server...${NC}"
echo -e "${GREEN}✅ Backend will start on http://localhost:8000${NC}"
echo -e "${GREEN}📖 API docs will be available at http://localhost:8000/docs${NC}"
echo -e "${YELLOW}⏹️  Press CTRL+C to stop${NC}"
echo ""

# Start the backend
uv run python main.py --start