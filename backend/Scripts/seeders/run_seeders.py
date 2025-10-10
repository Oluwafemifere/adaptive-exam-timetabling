#!/usr/bin/env python3

# backend/Scripts/seeders/run_seeders.py

"""
Unified seeder runner script for the Baze University Adaptive Exam Timetabling System.
This script provides a convenient interface to run both fake data seeding and structured data seeding.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from backend.Scripts.seeders.fake_seed import ComprehensiveFakeSeeder
from backend.Scripts.seeders.seed_data import EnhancedDatabaseSeeder


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class UnifiedSeederRunner:
    """
    Unified interface for running different types of database seeding operations.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url
        self.fake_seeder = ComprehensiveFakeSeeder(database_url)
        self.data_seeder = EnhancedDatabaseSeeder(database_url)

    async def run_fake_seeding(
        self, drop_existing: bool = False, magnitude: int = 3
    ) -> None:
        """Run fake data seeding for development and testing"""
        logger.info(
            f"🎭 Starting fake data seeding with magnitude level {magnitude}..."
        )
        # Set the magnitude level before running
        self.fake_seeder._set_magnitude_level(magnitude)
        await self.fake_seeder.run(drop_existing=drop_existing)
        logger.info("✅ Fake data seeding completed!")

    async def run_structured_seeding(
        self, drop_existing: bool = False, sample_data: bool = True
    ) -> None:
        """Run structured data seeding for production"""
        logger.info("🏗️ Starting structured data seeding...")
        await self.data_seeder.seed_all(
            drop_existing=drop_existing, sample_data=sample_data
        )
        logger.info("✅ Structured data seeding completed!")

    async def import_csv_data(self, file_path: str, entity_type: str) -> bool:
        """Import data from CSV file"""
        logger.info(f"📄 Importing {entity_type} from {file_path}...")
        result = await self.data_seeder.import_csv_data(file_path, entity_type)

        if result["success"]:
            logger.info(
                f"✅ Successfully imported {result.get('count', 0)} {entity_type} records"
            )
            return True
        else:
            logger.error(f"❌ Import failed: {result.get('error', 'Unknown error')}")
            if result.get("errors"):
                for error in result["errors"]:
                    logger.error(f"  - {error}")
            return False

    async def run_full_setup(
        self,
        use_fake_data: bool = False,
        drop_existing: bool = False,
        magnitude: int = 3,
    ) -> None:
        """
        Run a complete database setup with either structured or fake data
        """
        logger.info("🚀 Starting full database setup...")

        if use_fake_data:
            logger.info(
                f"Using fake data for development environment (magnitude: {magnitude})"
            )
            await self.run_fake_seeding(
                drop_existing=drop_existing, magnitude=magnitude
            )
        else:
            logger.info("Using structured data for production environment")
            await self.run_structured_seeding(
                drop_existing=drop_existing, sample_data=True
            )

        logger.info("🎉 Full database setup completed!")


def print_usage_examples():
    """Print usage examples for the seeder runner"""
    examples = """
Usage Examples:

1. Development setup with fake data (basic level):
   python scripts/seeders/run_seeders.py --mode fake --drop-existing --magnitude 1

2. Development setup with fake data (medium level - default):
   python scripts/seeders/run_seeders.py --mode fake --drop-existing --magnitude 3

3. Large-scale testing with fake data:
   python scripts/seeders/run_seeders.py --mode fake --drop-existing --magnitude 5

4. Production setup with structured data:
   python scripts/seeders/run_seeders.py --mode structured

5. Import CSV data:
   python scripts/seeders/run_seeders.py --mode csv --csv-file data.csv --entity-type students

6. Full setup with fake data (custom magnitude):
   python scripts/seeders/run_seeders.py --mode full --use-fake-data --drop-existing --magnitude 4

Magnitude Levels:
  1 = Basic (100 students)     - Fastest seeding, minimal data
  2 = Small (500 students)     - Quick testing
  3 = Medium (2000 students)   - Balanced development (DEFAULT)
  4 = Large (5000 students)    - Realistic testing
  5 = Enterprise (10000 students) - Production-like scale

Environment Variables:
- DATABASE_URL: Database connection string
- SEED_* variables: Scale limits for fake data generation (overrides magnitude)

Examples:
   export SEED_STUDENTS=1000
   export SEED_COURSES=500
   python scripts/seeders/run_seeders.py --mode fake --magnitude 2
"""
    print(examples)


async def main():
    """Main entry point with comprehensive argument parsing"""
    parser = argparse.ArgumentParser(
        description="Unified database seeder for Baze University Exam Timetabling System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["fake", "structured", "csv", "full", "help"],
        required=True,
        help="Seeding mode to run",
    )

    parser.add_argument("--database-url", help="Database URL override")

    parser.add_argument(
        "--drop-existing", action="store_true", help="Drop existing data before seeding"
    )
    parser.add_argument(
        "--use-fake-data",
        action="store_true",
        help="Use fake data instead of structured data (for full mode)",
    )
    parser.add_argument(
        "--no-sample-data",
        action="store_true",
        help="Skip sample data seeding (for structured mode)",
    )
    parser.add_argument(
        "--csv-file", help="CSV file path for import (required for csv mode)"
    )
    parser.add_argument(
        "--entity-type",
        choices=[
            "faculties",
            "departments",
            "students",
            "courses",
            "academic_sessions",
        ],
        help="Entity type for CSV import (required for csv mode)",
    )
    parser.add_argument(
        "--magnitude",
        type=int,
        choices=[0, 1, 2, 3, 4, 5],
        default=3,
        help="Set problem size magnitude level (1=Basic/100 students, 2=Small/500, 3=Medium/2000, 4=Large/5000, 5=Enterprise/10000)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle help mode early
    if args.mode == "help":
        print_usage_examples()
        return

    # Validate CSV mode arguments
    if args.mode == "csv":
        if not args.csv_file or not args.entity_type:
            parser.error("CSV mode requires --csv-file and --entity-type arguments")
        if not Path(args.csv_file).exists():
            parser.error(f"CSV file does not exist: {args.csv_file}")

    try:
        runner = UnifiedSeederRunner(args.database_url)

        if args.mode == "fake":
            await runner.run_fake_seeding(
                drop_existing=args.drop_existing, magnitude=args.magnitude
            )

        elif args.mode == "structured":
            await runner.run_structured_seeding(
                drop_existing=args.drop_existing,
                sample_data=not args.no_sample_data,
            )

        elif args.mode == "csv":
            success = await runner.import_csv_data(args.csv_file, args.entity_type)
            if not success:
                sys.exit(1)

        elif args.mode == "full":
            await runner.run_full_setup(
                use_fake_data=args.use_fake_data,
                drop_existing=args.drop_existing,
                magnitude=args.magnitude,
            )

        logger.info("🎯 All seeding operations completed successfully!")

    except KeyboardInterrupt:
        logger.info("⏹️ Seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Seeding failed with error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
