"""
Unified Path Configuration for IoT Device Monitor

This module provides consistent path configuration for all components.
Ensures that the project can be run from the root directory with proper Python path setup.

Usage:
    from backend.api.common.path_config import setup_project_paths
    setup_project_paths()
    # Now all imports will work correctly
"""

import sys
import os
from pathlib import Path

def get_project_root():
    """
    Get the project root directory by looking for characteristic files.
    This is more reliable than relative path calculations.
    """
    current_path = Path(__file__).resolve()
    
    # Look for project root indicators
    for parent in current_path.parents:
        if (parent / "requirements.txt").exists() and (parent / "backend").exists() and (parent / "database").exists():
            return parent
    
    # Fallback: use relative path calculation
    return Path(__file__).parent.parent.parent.parent

def setup_project_paths():
    """
    Setup sys.path for consistent imports across all components.
    This should be called at the beginning of standalone scripts.
    
    Designed to work from:
    - Project root: python -m backend.api.app
    - Backend API directory: cd backend/api && python app.py
    """
    project_root = get_project_root()
    
    # Paths needed for all imports to work correctly
    paths_to_add = [
        str(project_root),                    # For: import backend.*, import database.*
        str(project_root / "backend"),        # For: import api.*, import pcap_process.*
        str(project_root / "backend" / "api") # For: import endpoints.*, import services.*
    ]
    
    # Add paths to sys.path if not already present
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    return {
        'project_root': project_root,
        'backend_dir': project_root / "backend",
        'api_dir': project_root / "backend" / "api",
        'database_dir': project_root / "database"
    }

def ensure_project_imports():
    """
    Ensure that project imports work by setting up paths.
    This is a no-op if paths are already correctly configured.
    """
    project_root = get_project_root()
    
    # Check if we can import core modules
    try:
        import database
        import backend
        return True
    except ImportError:
        # Setup paths and try again
        setup_project_paths()
        try:
            import database
            import backend
            return True
        except ImportError:
            return False

if __name__ != "__main__":
    setup_project_paths() 