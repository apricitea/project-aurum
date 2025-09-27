"""
Project Aurum - Indonesian Quantitative Trading System
Main application entry point

For development:
    python main.py

For production:
    See docs/how-to-guides/deployment/ for deployment guides
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main application entry point"""
    print("🚀 Project Aurum - Indonesian Quantitative Trading System")
    print("📚 Documentation: docs/README.md")
    print("🔧 Development: docs/how-to-guides/development/")
    print("🚀 Deployment: docs/how-to-guides/deployment/")
    print("")
    print("To start the API server:")
    print("  cd src && uvicorn api.main:app --reload")
    print("")
    print("To start the dashboard:")
    print("  cd apps/web_dashboard && npm run dev")

if __name__ == "__main__":
    main()
