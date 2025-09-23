#!/usr/bin/env python3
"""
Install script for Mario Kart Time Trial Tracker dependencies.

This script helps install the required PIL (Pillow) library for image generation features.
Run this script to install the dependencies needed for lap time image generation.
"""

import subprocess
import sys


def install_pillow():
    """Install Pillow library for image processing"""
    try:
        print("Installing Pillow library for image processing...")

        # Try to install using pip
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "Pillow"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ Successfully installed Pillow!")
            print("\nThe Time Trial Tracker can now generate lap time images.")
            print("When you complete a time trial, it will automatically create")
            print(
                "a composite image showing all lap times overlaid on the final screenshot."
            )
        else:
            print("❌ Failed to install Pillow:")
            print(result.stderr)
            print("\nYou can try installing manually with:")
            print("    pip install Pillow")

    except Exception as e:
        print(f"❌ Error installing Pillow: {e}")
        print("\nYou can try installing manually with:")
        print("    pip install Pillow")


def check_pillow_installation():
    """Check if Pillow is already installed"""
    try:
        import PIL

        print("✅ Pillow is already installed!")
        print(f"   Version: {PIL.__version__}")
        return True
    except ImportError:
        print("⚠️  Pillow is not installed.")
        return False


def main():
    print("Mario Kart Time Trial Tracker - Dependency Installer")
    print("=" * 50)

    if not check_pillow_installation():
        print("\nInstalling required dependencies...")
        install_pillow()
    else:
        print("\nAll dependencies are already installed!")

    print("\n" + "=" * 50)
    print("Installation complete!")
    print("\nTo use the lap time image generation feature:")
    print("1. Complete a time trial run")
    print("2. When the final lap is saved, a new image will be created")
    print("3. The image will show all lap times overlaid on the final screenshot")
    print("4. Look for files named 'LapTimes_[Track]_Run[X]_[timestamp].png'")


if __name__ == "__main__":
    main()
