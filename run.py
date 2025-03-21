"""
Run script for the application.
This allows the application to be run with `python run.py`
"""
import os
import subprocess

if __name__ == "__main__":
    # Run gunicorn with our configuration
    subprocess.run([
        "gunicorn",
        "-c", "gunicorn_conf.py",
        "main:app"
    ])