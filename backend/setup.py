#!/usr/bin/env python3
"""
Setup script for the Loan Management System backend.
This script helps initialize the development environment.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        return None

def main():
    """Main setup function."""
    print("🚀 Setting up Loan Management System Backend")
    print("=" * 50)

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)

    print(f"✅ Python version: {sys.version}")

    # Check if virtual environment exists
    venv_path = Path("myenv")
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        run_command("python -m venv myenv")
    else:
        print("✅ Virtual environment already exists")

    # Activate virtual environment and install dependencies
    print("📦 Installing dependencies...")

    # Install production dependencies
    if Path("requirements.txt").exists():
        print("Installing production dependencies...")
        run_command("myenv/bin/pip install -r requirements.txt")
    else:
        print("⚠️  requirements.txt not found")

    # Install development dependencies
    if Path("requirements-dev.txt").exists():
        print("Installing development dependencies...")
        run_command("myenv/bin/pip install -r requirements-dev.txt")
    else:
        print("⚠️  requirements-dev.txt not found")

    # Create .env file if it doesn't exist
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        print("📋 Creating .env file from template...")
        shutil.copy(env_example, env_file)
        print("✅ .env file created. Please edit it with your configuration.")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("⚠️  .env.example not found. Please create .env manually.")

    # Run database migrations
    print("🗄️  Setting up database...")
    result = run_command("myenv/bin/alembic upgrade head")
    if result and result.returncode == 0:
        print("✅ Database migrations completed")
    else:
        print("⚠️  Database migration failed. You may need to run it manually.")

    # Create default admin user
    print("👤 Creating default admin user...")
    result = run_command("myenv/bin/python -c \"from app.utils.init_db import create_default_admin; create_default_admin()\"")
    if result and result.returncode == 0:
        print("✅ Default admin user created")
    else:
        print("⚠️  Failed to create default admin user")

    print("\n🎉 Setup completed!")
    print("\nTo start the development server:")
    print("1. Activate virtual environment: source myenv/bin/activate")
    print("2. Run: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    print("\nAPI Documentation will be available at:")
    print("- http://localhost:8000/api/docs (Swagger UI)")
    print("- http://localhost:8000/api/redoc (ReDoc)")
    print("\nDefault admin credentials:")
    print("- Username: admin")
    print("- Password: admin123")

if __name__ == "__main__":
    main()
