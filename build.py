#!/usr/bin/env python3
"""
Build script to set up uiCA dependencies.

This script:
1. Downloads and converts instruction data from uops.info (if needed)
2. Builds the XED Python extension

Usage:
    uv run python build.py

or:
    python build.py
"""

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


def generate_instruction_data():
    """Download instructions.xml and generate Python data files."""
    instr_data_dir = Path("instrData")

    if instr_data_dir.exists() and list(instr_data_dir.glob("*.py")):
        print("✓ Instruction data already exists in instrData/")
        return

    print("=" * 60)
    print("Downloading instruction data from uops.info...")
    print("=" * 60)

    xml_url = "https://www.uops.info/instructions.xml"
    xml_file = Path("instructions.xml")

    print(f"\nDownloading {xml_url}")
    print("This is ~110MB and may take a minute...")

    try:
        urllib.request.urlretrieve(xml_url, xml_file)
    except Exception as e:
        print(f"\nError downloading instructions.xml: {e}")
        sys.exit(1)

    print(f"\n✓ Downloaded ({xml_file.stat().st_size / 1024 / 1024:.1f} MB)")
    print("\nConverting XML to Python data structures...")

    try:
        subprocess.check_call([sys.executable, "convertXML.py", str(xml_file)])
    except subprocess.CalledProcessError as e:
        print(f"\nError converting XML: {e}")
        sys.exit(1)

    xml_file.unlink()
    print("✓ Instruction data generated in instrData/")


def build_xed():
    """Build the XED Python extension."""
    print("=" * 60)
    print("Building XED Python module...")
    print("=" * 60)

    xed_dir = Path("XED-to-XML").resolve()
    if not xed_dir.exists():
        print("\nError: XED-to-XML directory not found.")
        print("Run: git submodule update --init --recursive")
        sys.exit(1)

    mbuild_dir = Path("mbuild").resolve()
    if not mbuild_dir.exists():
        print("\nError: mbuild directory not found.")
        print("Run: git submodule update --init --recursive")
        sys.exit(1)

    # Build XED with mbuild in PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = str(mbuild_dir)

    print(f"\nBuilding in: {xed_dir}")
    print("This may take 1-2 minutes...\n")

    try:
        subprocess.check_call(
            [sys.executable, "mfile.py", "--opt=2", "--no-encoder", "pymodule"],
            cwd=str(xed_dir),
            env=env
        )
    except subprocess.CalledProcessError as e:
        print(f"\nError: XED build failed with exit code {e.returncode}")
        print("Make sure you have a C compiler installed (gcc/clang)")
        sys.exit(1)

    # Copy to project root
    xed_modules = list(xed_dir.glob("xed*.so")) + list(xed_dir.glob("xed*.pyd"))
    if xed_modules:
        dest = Path(".") / xed_modules[0].name
        shutil.copy2(xed_modules[0], dest)
        print(f"\n✓ XED module built successfully: {dest.name}")
        print(f"  Size: {dest.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("\nError: XED build completed but no module found")
        sys.exit(1)


def main():
    """Run all build steps."""
    generate_instruction_data()
    print()  # Blank line between steps
    build_xed()
    print("\n" + "=" * 60)
    print("✓ Build complete!")
    print("Run: uv run ./uiCA.py --help")
    print("=" * 60)


if __name__ == "__main__":
    main()
