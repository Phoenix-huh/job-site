import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))

backend_dir = os.path.abspath(os.path.join(current_dir, "..", "backend"))
if os.path.isdir(backend_dir):
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

from main import app
