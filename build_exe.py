"""
Build script to package Amazon ASIN Finder into a single standalone executable.
Bundles PySide6, Playwright driver, and Chromium binaries.
"""

import os
import sys
import subprocess
from pathlib import Path

def build():
    project_root = Path(__file__).resolve().parent
    playwright_dir = Path.home() / "AppData" / "Local" / "ms-playwright"

    if not playwright_dir.exists():
        print("ERROR: Playwright browsers directory not found.")
        print("Please run: playwright install chromium")
        sys.exit(1)

    # Terminate any running Amazon_ASIN_Finder.exe instances to unlock dist file
    print("Ensuring no running instances of Amazon_ASIN_Finder.exe...")
    subprocess.run(["taskkill", "/f", "/im", "Amazon_ASIN_Finder.exe"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    print(f"Project root: {project_root}")
    print(f"Playwright browsers directory: {playwright_dir}")

    # Build add-data list specifically for chromium folders to save space
    add_data_args = []
    for item in playwright_dir.iterdir():
        if "chromium" in item.name.lower() or "winldd" in item.name.lower():
            add_data_args.extend(["--add-data", f"{item};ms-playwright/{item.name}"])

    # Build PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name=Amazon_ASIN_Finder",
        *add_data_args,
        str(project_root / "main.py"),
    ]

    print("\nRunning PyInstaller...")
    print(" ".join(cmd))
    
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("SUCCESS! Executable built successfully.")
        print(f"Location: {project_root / 'dist' / 'Amazon_ASIN_Finder.exe'}")
        print("=" * 60)
    else:
        print("\nBUILD FAILED with exit code:", result.returncode)

if __name__ == "__main__":
    build()
