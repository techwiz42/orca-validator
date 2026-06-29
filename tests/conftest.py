import os
import sys

# Make the repo root importable (backend.*, machines.*) without an editable install.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
