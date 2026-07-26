import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))

_candidates = [
    os.path.abspath(os.path.join(current_dir, "..", "..", "backend")),
    os.path.abspath(os.path.join(current_dir, "..", "backend")),
    os.path.abspath(current_dir),
    os.path.abspath(os.path.join(current_dir, "..")),
]

for p in _candidates:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from main import app
except ImportError:
    from backend.main import app
