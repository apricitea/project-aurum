#!/usr/bin/env python3
"""
Automated dependency checker and fixer for Project Aurum
Checks for version conflicts and automatically resolves them
"""

import subprocess
import sys
import re
import json
from pathlib import Path

# Known compatible version sets
COMPATIBLE_VERSIONS = {
    # Machine Learning Stack
    "numpy": "1.26.4",
    "pandas": "2.2.0",
    "scikit-learn": "1.4.0",
    "scipy": "1.12.0",
    "statsmodels": "0.14.1",
    "xgboost": "2.0.3",

    # Redis/Celery Stack
    "redis": "5.0.1",
    "celery": "5.4.0",
    "aioredis": "2.0.1",
    "flower": "2.0.1",

    # FastAPI Stack
    "fastapi": "0.104.1",
    "pydantic": "2.5.3",
    "uvicorn": "0.24.0",

    # Database (Python 3.13 compatible)
    "asyncpg": "0.30.0",
    "sqlalchemy": "2.0.23",
    "alembic": "1.12.1",

    # XML Processing (Python 3.13 compatible)
    "lxml": "5.1.0",
    "beautifulsoup4": "4.12.2",
}

def run_command(cmd, capture_output=True):
    """Run a shell command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=30
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {cmd}")
        return None

def check_package_exists(package, version):
    """Check if a specific package version exists on PyPI"""
    cmd = f"pip index versions {package}"
    result = run_command(cmd)

    if result and result.returncode == 0:
        # Simple check - if version appears in output, it likely exists
        return version in result.stdout

    # Fallback: try to get package info
    cmd = f"pip show {package}=={version} --dry-run"
    result = run_command(cmd)
    return result and result.returncode == 0

def parse_requirements_file(file_path):
    """Parse requirements.txt and return package dictionary"""
    packages = {}

    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#') and '==' in line:
                try:
                    # Handle packages with extras like redis[hiredis]==5.0.1
                    if '[' in line:
                        package_part, version = line.split('==')
                        package = package_part.split('[')[0]
                        extras = package_part.split('[')[1].split(']')[0]
                        packages[package] = {
                            'version': version,
                            'extras': extras,
                            'line_num': line_num,
                            'original_line': line
                        }
                    else:
                        package, version = line.split('==')
                        packages[package] = {
                            'version': version,
                            'extras': None,
                            'line_num': line_num,
                            'original_line': line
                        }
                except ValueError:
                    print(f"Warning: Could not parse line {line_num}: {line}")

    return packages

def fix_requirements_file(file_path):
    """Fix requirements.txt with known compatible versions"""
    print("🔧 Fixing requirements.txt...")

    # Read current file
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Parse packages
    packages = parse_requirements_file(file_path)

    # Track changes
    changes_made = []

    # Fix known problematic packages
    for package, info in packages.items():
        current_version = info['version']

        if package in COMPATIBLE_VERSIONS:
            recommended_version = COMPATIBLE_VERSIONS[package]

            if current_version != recommended_version:
                print(f"  📦 {package}: {current_version} → {recommended_version}")

                # Update the line
                old_line = info['original_line']
                if info['extras']:
                    new_line = f"{package}[{info['extras']}]=={recommended_version}"
                else:
                    new_line = f"{package}=={recommended_version}"

                # Replace in lines
                for i, line in enumerate(lines):
                    if line.strip() == old_line:
                        lines[i] = new_line + '\n'
                        changes_made.append(f"{package}: {current_version} → {recommended_version}")
                        break

    # Write updated file
    if changes_made:
        with open(file_path, 'w') as f:
            f.writelines(lines)

        print(f"✅ Updated {len(changes_made)} packages in requirements.txt")
        for change in changes_made:
            print(f"  - {change}")
    else:
        print("✅ No changes needed in requirements.txt")

    return len(changes_made) > 0

def test_dependency_resolution():
    """Test if dependencies can be resolved"""
    print("\n🧪 Testing dependency resolution...")

    # Try uv resolution (uv doesn't have --dry-run, so we'll use a different approach)
    result = run_command("uv tree --quiet")

    if result and result.returncode == 0:
        print("✅ Dependencies resolve successfully!")
        return True
    else:
        # Try actual uv add to see the real error
        print("Testing with actual uv add...")
        result = run_command("uv add -r requirements.txt")
        if result and result.returncode == 0:
            print("✅ Dependencies resolve successfully!")
            return True
        else:
            print("❌ Dependencies still have conflicts:")
            if result:
                print(result.stderr)
            return False

def main():
    """Main dependency fixer"""
    print("🚀 Project Aurum Dependency Fixer")
    print("=" * 50)

    requirements_file = Path("requirements.txt")

    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        sys.exit(1)

    # Step 1: Parse current requirements
    print("📋 Analyzing current requirements...")
    packages = parse_requirements_file(requirements_file)
    print(f"Found {len(packages)} packages")

    # Step 2: Fix known issues
    changes_made = fix_requirements_file(requirements_file)

    # Step 3: Test resolution
    if test_dependency_resolution():
        print("\n🎉 All dependencies resolved successfully!")
        if changes_made:
            print("\n📝 Summary of changes:")
            print("The following packages were updated to compatible versions:")
            for package in COMPATIBLE_VERSIONS:
                if package in packages:
                    old_version = packages[package]['version']
                    new_version = COMPATIBLE_VERSIONS[package]
                    if old_version != new_version:
                        print(f"  • {package}: {old_version} → {new_version}")
    else:
        print("\n🔄 Dependencies still have conflicts. Manual intervention needed.")
        print("\nTo force installation with current versions:")
        print("  uv add -r requirements.txt --frozen")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()