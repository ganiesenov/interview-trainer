import sys
from pathlib import Path

# Make `core` importable when pytest is invoked as a bare `pytest`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
