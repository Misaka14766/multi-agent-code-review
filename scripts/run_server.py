#!/usr/bin/env python3
"""Launch the FastAPI review server.

Usage:
  python scripts/run_server.py
  python scripts/run_server.py --port 8080 --reload
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Code Review API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    import uvicorn

    print(f"Starting Multi-Agent Code Review API on http://{args.host}:{args.port}")
    print(f"Swagger UI: http://localhost:{args.port}/docs")
    print(f"Dashboard:  http://localhost:{args.port}/")
    print()

    uvicorn.run(
        "src.api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
