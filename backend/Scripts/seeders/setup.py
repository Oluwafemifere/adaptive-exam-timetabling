#!/usr/bin/env python3

# backend/scripts/seeders/setup.py

"""
Setup script for the seeders package.
Creates necessary directories and validates the environment.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def create_directory_structure() -> List[str]:
    """Create necessary directories for seeding operations."""
    created_dirs = []

    paths = {
        "data": BACKEND_DIR / "data",
        "logs": BACKEND_DIR / "logs",
        "data/csv": BACKEND_DIR / "data" / "csv",
        "data/exports": BACKEND_DIR / "data" / "exports",
        "logs/seeders": BACKEND_DIR / "logs" / "seeders",
    }

    for name, path in paths.items():
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(path))
            print(f"✓ Created directory: {path}")
        else:
            print(f"• Directory exists: {path}")

    return created_dirs


def create_env_template() -> bool:
    """Create a .env template file if it doesn't exist."""
    env_path = BACKEND_DIR / ".env"
    env_template_path = BACKEND_DIR / ".env.seeders.template"

    template_content = """# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/exam_system

# Admin User Configuration
ADMIN_EMAIL=admin@baze.edu.ng
ADMIN_PASSWORD=admin123
ADMIN_FIRST_NAME=System
ADMIN_LAST_NAME=Administrator

# Seeder Scale Limits (Development Mode)
SEED_FACULTIES=4
SEED_DEPARTMENTS=15
SEED_PROGRAMMES=25
SEED_BUILDINGS=6
SEED_ROOMS=50
SEED_COURSES=100
SEED_STUDENTS=500
SEED_EXAMS=100

# Seeder Configuration
SEED_BATCH_SIZE=500
SEED_PROGRESS_INTERVAL=1000
SEED_DEBUG=false

# For Production, use larger scale limits:
# SEED_FACULTIES=12
# SEED_DEPARTMENTS=60
# SEED_PROGRAMMES=150
# SEED_BUILDINGS=20
# SEED_ROOMS=500
# SEED_COURSES=2000
# SEED_STUDENTS=15000
# SEED_EXAMS=2000
"""

    if not env_template_path.exists():
        with open(env_template_path, "w") as f:
            f.write(template_content)
        print(f"✓ Created .env template: {env_template_path}")

        if not env_path.exists():
            print(
                f"📋 Copy {env_template_path} to {env_path} and configure your settings"
            )
            return False
        return True
    else:
        print(f"• Template exists: {env_template_path}")
        return True


def validate_dependencies() -> Dict[str, bool]:
    """Validate that required dependencies are installed."""
    dependencies = {
        "faker": False,
        "python-dotenv": False,
        "sqlalchemy": False,
        "asyncpg": False,
        "alembic": False,
    }

    for dep in dependencies:
        try:
            __import__(dep.replace("-", "_"))
            dependencies[dep] = True
            print(f"✓ {dep} is installed")
        except ImportError:
            print(f"❌ {dep} is NOT installed")

    return dependencies


def check_alembic_setup() -> bool:
    """Check if Alembic is properly set up."""
    alembic_dir = BACKEND_DIR / "alembic"
    alembic_ini = BACKEND_DIR / "alembic.ini"

    if alembic_dir.exists() and alembic_ini.exists():
        print("✓ Alembic is set up")

        # Check for migrations
        versions_dir = alembic_dir / "versions"
        if versions_dir.exists():
            migrations = list(versions_dir.glob("*.py"))
            if migrations:
                print(f"✓ Found {len(migrations)} migration(s)")
                return True
            else:
                print(
                    "⚠️ No migrations found - run 'alembic upgrade head' after creating initial migration"
                )
        else:
            print("❌ Alembic versions directory not found")
    else:
        print("❌ Alembic is not set up - run 'alembic init alembic' first")
        return False

    return True


def print_usage_guide():
    """Print a usage guide for the seeders."""
    guide = """
🌱 SEEDERS USAGE GUIDE

1. Basic Development Setup:
   python scripts/seeders/run_seeders.py --mode fake --drop-existing

2. Production Data Setup:
   python scripts/seeders/run_seeders.py --mode structured

3. CSV Import:
   python scripts/seeders/run_seeders.py --mode csv --csv-file data.csv --entity-type students

4. Environment Configuration:
   - Copy .env.seeders.template to .env
   - Adjust SEED_* variables for your needs
   - Set DATABASE_URL for your database

5. File Structure:
   backend/
   ├── scripts/seeders/     # Seeder scripts
   ├── data/csv/           # CSV import files
   ├── logs/seeders/       # Seeding logs
   └── .env               # Environment configuration

6. Scale Modes:
   - Development: Small datasets for fast seeding
   - Production: Realistic datasets for production use
   - Custom: Use environment variables to override defaults

For detailed help: python scripts/seeders/run_seeders.py --mode help
"""
    print(guide)


def main():
    """Main setup function."""
    print("🔧 Setting up seeders environment...\n")

    # Create directories
    print("📁 Creating directory structure:")
    created_dirs = create_directory_structure()
    print()

    # Create env template
    print("⚙️ Setting up environment configuration:")
    env_created = create_env_template()
    print()

    # Validate dependencies
    print("📦 Checking dependencies:")
    dependencies = validate_dependencies()
    print()

    # Check Alembic
    print("🗃️ Checking Alembic setup:")
    alembic_ok = check_alembic_setup()
    print()

    # Summary
    print("📋 SETUP SUMMARY:")
    print(f"• Directories created: {len(created_dirs)}")
    print(f"• Environment template: {'✓' if env_created else '❌'}")
    print(f"• Dependencies: {sum(dependencies.values())}/{len(dependencies)} installed")
    print(f"• Alembic: {'✓' if alembic_ok else '❌'}")

    # Check for issues
    missing_deps = [k for k, v in dependencies.items() if not v]
    issues = []

    if missing_deps:
        issues.append(
            f"Install missing dependencies: pip install {' '.join(missing_deps)}"
        )

    if not env_created:
        issues.append("Create .env file from template and configure settings")

    if not alembic_ok:
        issues.append(
            "Set up Alembic migrations: alembic init alembic && alembic upgrade head"
        )

    if issues:
        print("\n⚠️ ISSUES TO RESOLVE:")
        for issue in issues:
            print(f"• {issue}")
    else:
        print("\n🎉 Setup complete! Ready to use seeders.")

    print_usage_guide()


if __name__ == "__main__":
    main()
