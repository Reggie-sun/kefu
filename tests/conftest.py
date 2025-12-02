"""
Test bootstrap to ensure local packages are importable before any global site packages.
This guards against name collisions with similarly named libs in the environment.
"""
import os
import sys


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
