#!/usr/bin/env python3
"""
Celery worker entry point
"""
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import the celery app
from RSA.app.app import celery

if __name__ == '__main__':
    celery.start()