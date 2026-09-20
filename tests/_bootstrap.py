"""Shared test setup.

Every test imports this first: it puts the project root on sys.path, makes it
the working directory and forces pygame into headless mode. That way the
suites run from anywhere - the tests folder, the project root or an IDE.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.chdir(PROJECT_ROOT)

# Headless: no window, no sound card needed
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

