"""
Fresh Flow Insights - Entry point.
Run after building cache:  python -m src.main
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass  # python-dotenv not installed, use system env vars


def main():
    from src.api.routes import create_app
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    
    # Check if chat API is configured
    chat_api_key = os.environ.get("CHAT_API_KEY", "")
    chat_status = "[OK] configured" if chat_api_key else "[!] not configured (set CHAT_API_KEY)"
    
    print(f"API at http://127.0.0.1:{port} (uses cache/ if present)")
    print(f"Chat API: {chat_status}")
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "true").lower() == "true")


if __name__ == "__main__":
    main()
