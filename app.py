"""
Streamlit Cloud Entry Point for Adhi's AI Gym Coach.
Delegates cleanly to Main App/main.py while ensuring sys.path and directory resolution.
"""

import sys
import os
from pathlib import Path

# Add 'Main App' directory to sys.path
_ROOT_DIR = Path(__file__).resolve().parent
_MAIN_APP_DIR = _ROOT_DIR / "Main App"

if str(_MAIN_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_MAIN_APP_DIR))

# Change current working directory to Main App so relative asset lookups succeed
os.chdir(str(_MAIN_APP_DIR))

# Import and launch main application
from main import main

if __name__ == "__main__":
    main()
