import sys
import os

# Calculate absolute paths for Vercel runtime
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
backend_dir = os.path.join(root_dir, "backend")

# Ensure root and backend directories are in Python path
for path in [backend_dir, root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import app from backend/main.py cleanly
try:
    from main import app
except ImportError:
    from backend.main import app
