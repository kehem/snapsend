
import sys
from cx_Freeze import setup, Executable
import os

# Include files - adjust paths according to your project structure
include_files = []

# Add font files if they exist
if os.path.exists("fonts"):
    include_files.append(("fonts/", "fonts/"))

# Add image files
image_files = ["logo.svg", "back.png", "settings_icon.png"]
for img in image_files:
    if os.path.exists(img):
        include_files.append((img, img))

# Convert logo.svg to logo.ico if needed
if os.path.exists("logo.ico"):
    include_files.append(("logo.ico", "logo.ico"))

# Packages to include
packages = [
    "kivy", "kivy.app", "kivy.uix", "kivy.clock", "kivy.properties",
    "kivy.core.window", "kivy.graphics", "socket", "threading", 
    "tkinter", "zipfile", "tempfile", "collections", "time", "os", "sys"
]

# Build options
build_options = {
    "packages": packages,
    "include_files": include_files,
    "excludes": ["test", "unittest", "email", "http", "urllib", "xml"],
    "include_msvcrt": True,
    "optimize": 2,
}

# MSI options
bdist_msi_options = {
    "upgrade_code": "{ac97e9bf-ae0b-4d65-ac7c-0a5ef5597713}",
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\SnapSend",
    "install_icon": "logo.ico" if os.path.exists("logo.ico") else None,
    "summary_data": {
        "author": "Anirban Singha",
        "comments": "Fast File Transfer Application",
        "keywords": "File Transfer, Network, Sharing"
    },
    "all_users": True,
}

# Executable configuration
exe = Executable(
    script="app.py",  # Your main script - adjust filename
    base="Win32GUI",
    icon="logo.ico" if os.path.exists("logo.ico") else None,
    target_name="SnapSend.exe",
    copyright="Copyright (c) 2024 Anirban Singha",  # Fixed: removed © symbol
    trademarks="SnapSend Trademark"  # Fixed: removed ™ symbol
)

setup(
    name="SnapSend",
    version="1.0.0",
    description="Fast File Transfer Application",
    author="Anirban Singha",
    options={
        "build_exe": build_options,
        "bdist_msi": bdist_msi_options
    },
    executables=[exe]
)
