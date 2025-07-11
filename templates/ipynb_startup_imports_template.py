"""Template for the Automatic Imports on Kernel Restart"""

# This runs on every time the .ipynb kernel (re)start

# general packages and modules
import numpy as np
import pandas as pd 
import json
import os 
import sys

# Build an absolute path from this notebook's parent directory
module_path = os.path.abspath(os.path.join('..'))

# Add `module_path` to sys.path if not already present
if module_path not in sys.path:
    sys.path.append(module_path)

# Any project-specific modules
import new_factsheet as nf
import graphql_leanix_utils as gqlix

print("ipynb_startup_imports.py imports loaded successfully!")