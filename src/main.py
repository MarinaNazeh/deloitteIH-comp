"""
Fresh Flow Insights - Entry point.
Run after building cache:  python -m src.main
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main():
    from src.api.routes import create_app
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    print(f"API at http://127.0.0.1:{port} (uses cache/ if present)")
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "true").lower() == "true")


if __name__ == "__main__":
    main()
