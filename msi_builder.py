# msi_troubleshooter.py - Diagnose and fix MSI generation issues

import os
import sys
import subprocess
import shutil
from pathlib import Path
import platform

def check_python_version():
    """Check if Python version is compatible"""
    print(f"Python version: {sys.version}")
    if sys.version_info >= (3, 13):
        print("❌ CRITICAL: Python 3.13+ detected!")
        print("   cx_Freeze bdist_msi is NOT supported in Python 3.13")
        print("   Solutions:")
        print("   1. Use Python 3.11 or 3.12")
        print("   2. Use PyInstaller + Inno Setup instead")
        print("   3. Use alternative MSI builders")
        return False
    elif sys.version_info < (3, 7):
        print("❌ Python version too old (need 3.7+)")
        return False
    else:
        print("✓ Python version compatible")
        return True

def check_windows_environment():
    """Check Windows-specific requirements"""
    if platform.system() != "Windows":
        print("❌ MSI generation only works on Windows")
        return False
    
    print("✓ Running on Windows")
    
    # Check for Windows SDK
    sdk_paths = [
        r"C:\Program Files (x86)\Windows Kits\10",
        r"C:\Program Files\Microsoft SDKs\Windows",
        r"C:\Program Files (x86)\Microsoft SDKs\Windows"
    ]
    
    sdk_found = any(os.path.exists(path) for path in sdk_paths)
    if not sdk_found:
        print("⚠ Windows SDK not found - MSI creation might fail")
        print("  Install Windows SDK from Microsoft")
    else:
        print("✓ Windows SDK detected")
    
    return True

def install_fixed_cx_freeze():
    """Install a working version of cx_Freeze"""
    print("Installing compatible cx_Freeze version...")
    try:
        # Uninstall current version
        subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', 'cx_freeze', '-y'])
        
        # Install specific working version
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cx_freeze==6.15.10'])
        print("✓ Installed cx_Freeze 6.15.10 (known working version)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install cx_Freeze: {e}")
        return False

def create_minimal_setup():
    """Create a minimal, working setup.py for MSI generation"""
    
    # Find main script
    main_script = None
    for name in ["app.py", "main.py", "snapsend.py", "SnapSend.py"]:
        if os.path.exists(name):
            main_script = name
            break
    
    if not main_script:
        py_files = [f for f in os.listdir('.') if f.endswith('.py') and not f.startswith('build_') and not f.startswith('setup')]
        if py_files:
            main_script = py_files[0]
    
    if not main_script:
        print("❌ No main Python script found!")
        return False
    
    print(f"✓ Using main script: {main_script}")
    
    setup_content = f'''# Minimal working setup.py for MSI generation
import sys
from cx_Freeze import setup, Executable
import os

# Build options
build_exe_options = {{
    "packages": ["os", "sys"],
    "include_files": [],
    "excludes": ["tkinter", "test", "unittest"],
    "optimize": 2,
    "include_msvcrt": True
}}

# Add files if they exist
if os.path.exists("logo.ico"):
    build_exe_options["include_files"].append("logo.ico")

# MSI options
bdist_msi_options = {{
    "upgrade_code": "{{12345678-1234-1234-1234-123456789012}}",
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\\SnapSend",
}}

# Create executable
executables = [
    Executable(
        script="{main_script}",
        base="Win32GUI" if "{main_script}".endswith(('.pyw', 'app.py')) else None,
        target_name="SnapSend.exe",
        icon="logo.ico" if os.path.exists("logo.ico") else None
    )
]

setup(
    name="SnapSend",
    version="1.0.0",
    description="File Transfer Application",
    author="Your Name",
    options={{
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options
    }},
    executables=executables
)
'''
    
    with open('setup_minimal.py', 'w', encoding='utf-8') as f:
        f.write(setup_content)
    
    print("✓ Created minimal setup_minimal.py")
    return True

def build_msi_step_by_step():
    """Build MSI with detailed logging"""
    print("\n" + "="*50)
    print("BUILDING MSI - STEP BY STEP")
    print("="*50)
    
    # Clean build directories
    print("1. Cleaning build directories...")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"   ✓ Cleaned {dir_name}")
            except Exception as e:
                print(f"   ⚠ Could not clean {dir_name}: {e}")
    
    # Create directories
    os.makedirs('dist', exist_ok=True)
    print("   ✓ Created dist directory")
    
    # Build executable first
    print("2. Building executable...")
    try:
        result = subprocess.run(
            [sys.executable, 'setup_minimal.py', 'build'],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print("   ✓ Executable built successfully")
        else:
            print("   ❌ Executable build failed:")
            print(f"   STDOUT: {result.stdout}")
            print(f"   STDERR: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("   ❌ Build timed out")
        return False
    except Exception as e:
        print(f"   ❌ Build failed: {e}")
        return False
    
    # Build MSI
    print("3. Building MSI...")
    try:
        result = subprocess.run(
            [sys.executable, 'setup_minimal.py', 'bdist_msi'],
            capture_output=True, text=True, timeout=300
        )
        
        print(f"   Return code: {result.returncode}")
        print(f"   STDOUT: {result.stdout}")
        if result.stderr:
            print(f"   STDERR: {result.stderr}")
        
        if result.returncode == 0:
            print("   ✓ MSI command completed")
        else:
            print("   ❌ MSI build failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("   ❌ MSI build timed out")
        return False
    except Exception as e:
        print(f"   ❌ MSI build failed: {e}")
        return False
    
    # Check for MSI files
    print("4. Checking for MSI files...")
    msi_files = []
    
    # Check dist directory
    dist_path = Path('dist')
    if dist_path.exists():
        msi_files.extend(list(dist_path.glob('*.msi')))
    
    # Check build directory
    build_path = Path('build')
    if build_path.exists():
        for subdir in build_path.iterdir():
            if subdir.is_dir():
                msi_files.extend(list(subdir.glob('*.msi')))
    
    if msi_files:
        print("   ✓ MSI files found:")
        for msi_file in msi_files:
            size_mb = msi_file.stat().st_size / (1024*1024)
            print(f"     - {msi_file} ({size_mb:.1f} MB)")
        return True
    else:
        print("   ❌ No MSI files found")
        
        # List all files in build and dist
        print("   Files in build/:")
        if build_path.exists():
            for item in build_path.rglob('*'):
                if item.is_file():
                    print(f"     {item}")
        
        print("   Files in dist/:")
        if dist_path.exists():
            for item in dist_path.rglob('*'):
                if item.is_file():
                    print(f"     {item}")
        
        return False

def try_alternative_msi_methods():
    """Try alternative MSI creation methods"""
    print("\n" + "="*50)
    print("TRYING ALTERNATIVE METHODS")
    print("="*50)
    
    # Method 1: Different cx_Freeze command
    print("Method 1: Using different cx_Freeze syntax...")
    try:
        result = subprocess.run(
            [sys.executable, '-c', 
             "from cx_Freeze import setup, Executable; "
             "setup(name='SnapSend', executables=[Executable('app.py' if __import__('os').path.exists('app.py') else [f for f in __import__('os').listdir('.') if f.endswith('.py')][0])], "
             "options={'bdist_msi': {'upgrade_code': '{12345678-1234-1234-1234-123456789012}'}})"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("   ✓ Alternative method 1 worked")
            return True
    except Exception as e:
        print(f"   ❌ Method 1 failed: {e}")
    
    # Method 2: Manual MSI with msilib (if available)
    print("Method 2: Trying manual MSI creation...")
    try:
        import msilib
        print("   ✓ msilib available - this could work")
        # This would require a full MSI creation script
        print("   ⚠ Manual MSI creation requires more complex implementation")
    except ImportError:
        print("   ❌ msilib not available")
    
    return False

def create_pyinstaller_alternative():
    """Create PyInstaller + Inno Setup alternative"""
    print("\n" + "="*50)
    print("CREATING PYINSTALLER ALTERNATIVE")
    print("="*50)
    
    # Install PyInstaller
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        print("✓ PyInstaller installed")
    except:
        print("❌ Failed to install PyInstaller")
        return False
    
    # Find main script
    main_script = None
    for name in ["app.py", "main.py", "snapsend.py", "SnapSend.py"]:
        if os.path.exists(name):
            main_script = name
            break
    
    if not main_script:
        print("❌ No main script found")
        return False
    
    # Create PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', 'SnapSend',
        main_script
    ]
    
    if os.path.exists('logo.ico'):
        cmd.extend(['--icon', 'logo.ico'])
    
    try:
        subprocess.check_call(cmd)
        print("✓ PyInstaller EXE created")
        
        # Create simple Inno Setup script
        inno_script = '''[Setup]
AppId={{12345678-1234-1234-1234-123456789012}}
AppName=SnapSend
AppVersion=1.0.0
DefaultDirName={autopf}\\SnapSend
DefaultGroupName=SnapSend
OutputDir=dist
OutputBaseFilename=SnapSend-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\\SnapSend.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\\SnapSend"; Filename: "{app}\\SnapSend.exe"
Name: "{autodesktop}\\SnapSend"; Filename: "{app}\\SnapSend.exe"

[Run]
Filename: "{app}\\SnapSend.exe"; Description: "Launch SnapSend"; Flags: nowait postinstall skipifsilent
'''
        
        with open('SnapSend.iss', 'w') as f:
            f.write(inno_script)
        
        print("✓ Created SnapSend.iss for Inno Setup")
        print("📋 Next steps:")
        print("   1. Download Inno Setup: https://jrsoftware.org/isdl.php")
        print("   2. Install Inno Setup")
        print("   3. Open SnapSend.iss in Inno Setup")
        print("   4. Click Build > Compile to create installer")
        
        return True
        
    except Exception as e:
        print(f"❌ PyInstaller failed: {e}")
        return False

def main():
    """Main troubleshooting function"""
    print("MSI GENERATION TROUBLESHOOTER")
    print("="*50)
    
    # Check basic requirements
    if not check_python_version():
        print("\n🔧 RECOMMENDED FIXES:")
        print("1. Install Python 3.11 or 3.12")
        print("2. Use PyInstaller + Inno Setup instead")
        
        if input("\nTry PyInstaller alternative? (y/n): ").lower() == 'y':
            create_pyinstaller_alternative()
        return
    
    if not check_windows_environment():
        return
    
    # Install proper cx_Freeze version
    if not install_fixed_cx_freeze():
        return
    
    # Create minimal setup
    if not create_minimal_setup():
        return
    
    # Try to build MSI
    if build_msi_step_by_step():
        print("\n🎉 SUCCESS! MSI generated successfully!")
        return
    
    # Try alternatives
    print("\n🔧 Trying alternative methods...")
    if try_alternative_msi_methods():
        print("\n🎉 SUCCESS! Alternative method worked!")
        return
    
    # Final fallback
    print("\n🔄 Falling back to PyInstaller + Inno Setup...")
    if create_pyinstaller_alternative():
        print("\n✅ PyInstaller alternative created!")
    else:
        print("\n❌ All methods failed!")
        print("\n🆘 MANUAL SOLUTIONS:")
        print("1. Try on a different Windows machine")
        print("2. Use Python 3.11 instead of current version")
        print("3. Install Visual Studio Build Tools")
        print("4. Use NSIS instead of MSI")
        print("5. Create a simple ZIP distribution")

if __name__ == "__main__":
    main()