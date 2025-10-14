#!/bin/bash
###############################################################################
# Local Development Setup Script
# Sets up SQLite database and initializes with sample data
###############################################################################

set -e  # Exit on error

echo "🚀 Project Aurum - Local Development Setup"
echo "=========================================="
echo ""

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Create data directory if it doesn't exist
echo "📁 Creating data directory..."
mkdir -p data

# Check if database already exists
if [ -f "data/trading_system.db" ]; then
    echo "⚠️  Database already exists at data/trading_system.db"
    read -p "Do you want to recreate it? This will delete all existing data. (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing database..."
        rm -f data/trading_system.db
    else
        echo "✅ Keeping existing database"
        echo ""
        echo "🎉 Setup complete! You can now start the server:"
        echo "   cd src && uv run uvicorn api.main_local:app --reload --host 0.0.0.0 --port 8000"
        exit 0
    fi
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if command -v uv &> /dev/null; then
    echo "Using uv..."
    uv sync
elif command -v pip &> /dev/null; then
    echo "Using pip..."
    pip install -r requirements.txt
else
    echo "❌ Error: Neither uv nor pip found. Please install Python package manager."
    exit 1
fi

# Initialize database with sample data
echo ""
echo "🗄️  Initializing SQLite database with sample data..."
python scripts/init_database.py

echo ""
echo "✨ ================================="
echo "✅ Local development setup complete!"
echo "=================================== ✨"
echo ""
echo "📝 Demo Credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "🚀 Next steps:"
echo "   1. Start the backend server:"
echo "      cd src && uv run uvicorn api.main_local:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "   2. Start the frontend (in a new terminal):"
echo "      cd apps/web_dashboard/frontend && npm run dev"
echo ""
echo "   3. Open your browser:"
echo "      http://localhost:3000"
echo ""
echo "📍 Database location: data/trading_system.db"
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""
