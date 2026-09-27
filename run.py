"""
run.py -- Start the Classroom Attendance System

Usage (from AttendanceProject/ root):
    python run.py
"""

import os
import sys
import socket

# Ensure we are always running from project root
# so relative paths (CleanDataset/, models/) resolve correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

# Now import from backend (no package prefix needed)
import database as db
from recognize import load_known_faces
from app import app


def find_available_port(preferred_port=5000):
    """Finds an open port starting from preferred_port."""
    for port in [preferred_port, 5001, 5002, 8000, 8080]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred_port


if __name__ == "__main__":
    print("\n========================================")
    print("  ClassTrack - Classroom Attendance System")
    print("========================================")
    print("[startup] Working directory : " + os.getcwd())

    print("[startup] Initialising MySQL database...")
    try:
        db.init_db()
        print("[startup] Database ready.")
    except Exception as e:
        print("[startup] Database error: " + str(e))
        print("[startup]   Make sure MySQL is running and credentials are correct.")
        sys.exit(1)

    print("[startup] Pre-loading face recognition models...")
    try:
        known = load_known_faces()
        print("[startup] Loaded " + str(len(known)) + " student(s) into face database.")
    except Exception as e:
        print("[startup] Model loading error: " + str(e))
        sys.exit(1)

    port = find_available_port(5000)
    print(f"[startup] Server --> http://localhost:{port}")
    if port != 5000:
        print(f"[startup] (Note: Port 5000 was occupied by another app, switched to port {port})")
    print("========================================\n")

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
