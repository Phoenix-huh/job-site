import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))

# Vercel Serverless: the deployment root contains both frontend/ and backend/
# Try multiple possible locations for the backend directory
_candidates = [
    os.path.join(current_dir, "..", "backend"),
    os.path.join(current_dir, "..", "..", "backend"),
    os.path.join(current_dir, ".."),
]

for candidate in _candidates:
    candidate = os.path.abspath(candidate)
    if os.path.isdir(os.path.join(candidate, "main.py")) if os.path.isdir(candidate) else False:
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
        break
    if os.path.isfile(os.path.join(candidate, "main.py")):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
        break

# Fallback: add all candidates to path so import can find main
for candidate in _candidates:
    p = os.path.abspath(candidate)
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from main import app
except ImportError:
    from backend.main import app
