"""
Project Aurum - Indonesian Quantitative Trading System
Main application entry point

For development:
    uv run python main.py

For production:
    See docs/how-to-guides/deployment/ for deployment guides
"""

import sys
import os
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main application entry point"""
    print("🚀 Project Aurum - Indonesian Quantitative Trading System")
    print("📚 Documentation: docs/README.md")
    print("🔧 Development: docs/how-to-guides/development/")
    print("🚀 Deployment: docs/how-to-guides/deployment/")
    print("")

    # Check if we should start the backend server
    if len(sys.argv) > 1 and sys.argv[1] == '--start':
        start_backend()
    else:
        print("Usage:")
        print("  uv run python main.py --start    # Start the backend API server")
        print("")
        print("To start manually:")
        print("  uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
        print("")
        print("To start the dashboard:")
        print("  cd apps/web_dashboard/frontend && npm run dev")

def start_backend():
    """Start the FastAPI backend server"""
    print("🔥 Starting FastAPI backend server...")

    try:
        # Use uvicorn to start the FastAPI app
        import uvicorn
        from src.api.main import app

        print("✅ Backend starting on http://localhost:8000")
        print("📖 API docs available at http://localhost:8000/docs")
        print("⏹️  Press CTRL+C to stop")

        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the project root and have run: uv sync")
        return 1
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return 1

if __name__ == "__main__":
    main()
