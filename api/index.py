import os
import sys

# Ensure root folder is in python path for serverless imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
