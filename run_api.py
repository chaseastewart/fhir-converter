"""Start the FHIR Converter FastAPI server.

Usage:
    python run_api.py [--host 127.0.0.1] [--port 8000] [--reload]

Interactive docs are served at http://<host>:<port>/docs
"""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FHIR Converter API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes")
    args = parser.parse_args()

    uvicorn.run("api.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
