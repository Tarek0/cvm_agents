#!/usr/bin/env python
"""
Launch script for the CVM System Streamlit UI.

This script starts the Streamlit server with the appropriate options.
"""
import os
import subprocess
import sys
from pathlib import Path

def main():
    """Launch the Streamlit UI for CVM System."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    
    # Path to the Streamlit app
    app_path = script_dir / "app.py"
    
    # Ensure we're in the project root directory
    project_root = script_dir.parent.parent
    
    # Check if the app file exists
    if not app_path.exists():
        print(f"Error: Could not find app.py at {app_path}")
        sys.exit(1)
    
    # Construct the streamlit run command
    cmd = [
        "streamlit", "run", str(app_path),
        "--server.port", "8501",
        "--server.address", "localhost",
        "--browser.serverAddress", "localhost",
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false"
    ]
    
    print(f"Starting CVM System UI...")
    print(f"URL: http://localhost:8501")
    print(f"Press Ctrl+C to stop the server")
    
    # Start the Streamlit server
    try:
        subprocess.run(cmd, cwd=project_root)
    except KeyboardInterrupt:
        print("\nShutting down CVM System UI...")
    except Exception as e:
        print(f"Error starting Streamlit server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 