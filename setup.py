#!/usr/bin/env python3
"""Setup script for uiCA that builds XED Python extension."""

import os
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext


class XEDBuildExt(build_ext):
    """Custom build extension that compiles XED using its mfile.py build system."""

    def run(self):
        # Ensure submodules are initialized
        self._ensure_submodules()

        # Build XED using its build system
        self._build_xed()

        # Run the standard build_ext
        super().run()

    def _ensure_submodules(self):
        """Initialize git submodules if they don't exist."""
        xed_path = Path("XED-to-XML")
        mbuild_path = Path("mbuild")

        if not xed_path.exists() or not list(xed_path.iterdir()):
            print("Initializing XED-to-XML submodule...")
            subprocess.check_call(["git", "submodule", "update", "--init", "--recursive"])

        if not mbuild_path.exists() or not list(mbuild_path.iterdir()):
            print("Initializing mbuild submodule...")
            subprocess.check_call(["git", "submodule", "update", "--init", "--recursive"])

    def _build_xed(self):
        """Build XED library and Python module."""
        xed_dir = Path("XED-to-XML").resolve()

        if not xed_dir.exists():
            raise RuntimeError("XED-to-XML directory not found. Run 'git submodule update --init'")

        print("Building XED library and Python module...")

        # Run XED's build system
        env = os.environ.copy()
        env["PYTHONPATH"] = str(xed_dir.parent / "mbuild")

        subprocess.check_call(
            [sys.executable, "mfile.py", "--opt=2", "--no-encoder", "pymodule"],
            cwd=str(xed_dir),
            env=env
        )

        # Copy built xed module to package directory
        xed_module = None
        for pattern in ["xed*.so", "xed*.pyd", "xed*.dylib"]:
            matches = list(xed_dir.glob(pattern))
            if matches:
                xed_module = matches[0]
                break

        if not xed_module:
            raise RuntimeError("XED module build failed - no xed.so/pyd found")

        # Copy XED module to multiple locations for different install scenarios
        import shutil
        import sysconfig

        # 1. Copy to project root (for editable installs and source builds)
        dest_root = Path(".") / xed_module.name
        print(f"Copying {xed_module} -> {dest_root}")
        shutil.copy2(xed_module, dest_root)

        # 2. Copy to build lib directory (for wheel builds)
        if self.build_lib:
            dest_build = Path(self.build_lib) / xed_module.name
            print(f"Copying {xed_module} -> {dest_build}")
            shutil.copy2(xed_module, dest_build)

        # 3. For editable installs, also copy to site-packages
        site_packages = sysconfig.get_path("purelib")
        if site_packages:
            dest_site = Path(site_packages) / xed_module.name
            print(f"Copying {xed_module} -> {dest_site}")
            shutil.copy2(xed_module, dest_site)


setup(
    name="uica",
    version="1.0.0",
    author="Andreas Abel",
    author_email="",
    description="uiCA: uops.info Code Analyzer - Throughput prediction for Intel CPUs",
    long_description=Path("README.md").read_text() if Path("README.md").exists() else "",
    long_description_content_type="text/markdown",
    url="https://github.com/compiler-explorer/uiCA",
    packages=find_packages(),
    package_data={
        "": ["*.html", "xed*.so", "xed*.pyd", "xed*.dylib"],
    },
    include_package_data=True,
    install_requires=[
        "plotly",
    ],
    extras_require={
        "windows": ["pydot"],
    },
    entry_points={
        "console_scripts": [
            "uica=uiCA:main",
            "uica-facile=facile:main",
        ],
    },
    # Dummy extension to trigger build_ext
    ext_modules=[Extension("_xed_build_trigger", sources=["_xed_build_trigger.c"])],
    cmdclass={
        "build_ext": XEDBuildExt,
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Disassemblers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
