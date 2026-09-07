"""
Streamlit Cloud Default Entry Point for Adhi's AI Gym Coach.
"""

import sys
import os
from pathlib import Path

# Add 'Main App' to sys.path
_ROOT_DIR = Path(__file__).resolve().parent
_MAIN_APP_DIR = _ROOT_DIR / "Main App"

if str(_MAIN_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_MAIN_APP_DIR))

# Set working directory to Main App
os.chdir(str(_MAIN_APP_DIR))

from main import main

if __name__ == "__main__":
    main()
