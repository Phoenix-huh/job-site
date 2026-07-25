import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
backend_dir = os.path.join(root_dir, "backend")

for path in [root_dir, backend_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from main import app
except Exception as first_error:
    try:
        from app import app
    except Exception as second_error:
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/api/{full_path:path}")
        def startup_error_handler(full_path: str):
            return {
                "error": "Serverless function failed to import backend app.",
                "primary_exception": str(first_error),
                "fallback_exception": str(second_error),
                "sys_path": sys.path,
            }
