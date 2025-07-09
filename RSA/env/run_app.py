#!/usr/bin/env python3
"""
Flask app runner
"""
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the Flask app
from RSA.app.app import app

if __name__ == '__main__':
    app.run(debug=True, port=5000)