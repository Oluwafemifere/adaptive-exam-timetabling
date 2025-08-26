# scripts/backup_manager.py
"""
Database Backup Manager for the Adaptive Exam Timetabling System.
Handles database backups, restoration, and data archiving.
"""
import os
import sys
import logging
import argparse
import subprocess
import gzip
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2 import sql
import boto3
from botocore.exceptions import ClientError

# Add the backend app to Python path
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from app.database import db_manager, init_db
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database backups and restoration operations."""

    def __init__(self, database_url: Optional[str] = None, backup_dir: Optional[str] = None):
        self.settings = get_settings()
        self.database_url = database_url or self.settings.DATABASE_URL
        self.backup_dir = Path(backup_dir or self.settings.BACKUP_DIR or './backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # AWS S3 configuration for remote backups
        self.s3_client = None
        self.s3_bucket = self.settings.BACKUP_S3_BUCKET

        if self.settings.AWS_ACCESS_KEY_ID and self.settings.AWS_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.settings.AWS_REGION or 'us-east-1'
            )

        logger.info(f"Backup manager initialized with backup directory: {self.backup_dir}")

    def create_backup(
        self,
        backup_name: Optional[str] = None,
        compress: bool = True,
        upload_to_s3: bool = False,
        schema_only: bool = False,
        exclude_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a database backup.

        Args:
            backup_name: Name for the backup file (auto-generated if None)
            compress: Whether to compress the backup file
            upload_to_s3: Whether to upload backup to S3
            schema_only: Whether to backup schema only (no data)
            exclude_tables: List of tables to exclude from backup

        Returns:
            dict: Backup operation result
        """
        logger.info("Starting database backup")

        try:
            # Generate backup filename
            if not backup_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"exam_system_backup_{timestamp}"

            backup_file = self.backup_dir / f"{backup_name}.sql"

            # Parse database URL
            db_params = self._parse_database_url(self.database_url)

            # Build pg_dump command
            cmd = [
                'pg_dump',
                '--host', db_params['host'],
                '--port', str(db_params['port']),
                '--username', db_params['username'],
                '--dbname', db_params['database'],
                '--verbose',
                '--clean',
                '--if-exists',
                '--create'
            ]

            if schema_only:
                cmd.append('--schema-only')
            else:
                cmd.append('--data-only')

            # Exclude tables if specified
            if exclude_tables:
                for table in exclude_tables:
                    cmd.extend(['--exclude-table', table])

            # Set password environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_params['password']

            # Execute backup
            logger.info(f"Creating backup: {backup_file}")
            with open(backup_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )

            if result.returncode != 0:
                error_msg = result.stderr
                logger.error(f"Backup failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'backup_file': None
                }

            # Get file size
            file_size = backup_file.stat().st_size

            # Compress if requested
            compressed_file: Optional[Path] = None
            if compress:
                compressed_file = self._compress_backup(backup_file)
                if compressed_file:
                    backup_file.unlink()
                    backup_file = compressed_file
                    file_size = backup_file.stat().st_size

            # Upload to S3 if requested
            s3_key: Optional[str] = None
            if upload_to_s3 and self.s3_client and self.s3_bucket:
                s3_key = self._upload_to_s3(backup_file)

            # Create backup metadata
            metadata = {
                'backup_name': backup_name,
                'created_at': datetime.now().isoformat(),
                'database': db_params['database'],
                'file_path': str(backup_file),
                'file_size': file_size,
                'compressed': compress,
                'schema_only': schema_only,
                'excluded_tables': exclude_tables or [],
                's3_key': s3_key
            }

            # Save metadata
            metadata_file = backup_file.with_suffix('.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Backup completed successfully: {backup_file} ({file_size:,} bytes)")

            return {
                'success': True,
                'backup_file': str(backup_file),
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'backup_file': None
            }

    def restore_backup(
        self,
        backup_file: str,
        target_database: Optional[str] = None,
        clean_first: bool = True
    ) -> Dict[str, Any]:
        """
        Restore a database backup.

        Args:
            backup_file: Path to backup file
            target_database: Target database name (uses current if None)
            clean_first: Whether to clean target database first

        Returns:
            dict: Restore operation result
        """
        logger.info(f"Starting database restore from: {backup_file}")

        try:
            backup_path = Path(backup_file)

            if not backup_path.exists():
                return {
                    'success': False,
                    'error': f'Backup file not found: {backup_file}'
                }

            # Decompress if needed
            if backup_path.suffix == '.gz':
                decompressed_file = self._decompress_backup(backup_path)
                if not decompressed_file:
                    return {
                        'success': False,
                        'error': 'Failed to decompress backup file'
                    }
                backup_path = decompressed_file

            # Parse database URL
            db_params = self._parse_database_url(self.database_url)
            if target_database:
                db_params['database'] = target_database

            # Build psql command
            cmd = [
                'psql',
                '--host', db_params['host'],
                '--port', str(db_params['port']),
                '--username', db_params['username'],
                '--dbname', db_params['database'],
                '--file', str(backup_path),
                '--verbose'
            ]
            if clean_first:
                cmd.append('--single-transaction')

            # Set password environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_params['password']

            # Execute restore
            logger.info(f"Restoring to database: {db_params['database']}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                env=env,
                text=True
            )

            if result.returncode != 0:
                error_msg = result.stderr
                logger.error(f"Restore failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

            logger.info("Database restore completed successfully")
            return {
                'success': True,
                'target_database': db_params['database'],
                'restored_from': str(backup_path)
            }

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def list_backups(self, include_s3: bool = False) -> List[Dict[str, Any]]:
        """
        List available backups.

        Args:
            include_s3: Whether to include S3 backups

        Returns:
            list: List of backup information
        """
        backups: List[Dict[str, Any]] = []

        # Local backups
        for backup_file in self.backup_dir.glob('*.sql*'):
            metadata_file = backup_file.with_suffix('.json')
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    backups.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to read metadata for {backup_file}: {e}")
            else:
                stat = backup_file.stat()
                backups.append({
                    'backup_name': backup_file.stem,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'file_path': str(backup_file),
                    'file_size': stat.st_size,
                    'compressed': backup_file.suffix == '.gz'
                })

        # S3 backups
        if include_s3 and self.s3_client and self.s3_bucket:
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix='exam_system_backup_'
                )
                for obj in response.get('Contents', []):
                    backups.append({
                        'backup_name': obj['Key'],
                        'created_at': obj['LastModified'].isoformat(),
                        'file_size': obj['Size'],
                        's3_key': obj['Key'],
                        'location': 's3'
                    })
            except ClientError as e:
                logger.warning(f"Failed to list S3 backups: {e}")

        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups

    def cleanup_old_backups(
        self,
        keep_days: int = 30,
        keep_count: int = 10,
        cleanup_s3: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up old backup files.

        Args:
            keep_days: Number of days to keep backups
            keep_count: Minimum number of backups to keep
            cleanup_s3: Whether to cleanup S3 backups too

        Returns:
            dict: Cleanup operation result
        """
        logger.info(f"Cleaning up backups older than {keep_days} days")

        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            cleaned_files: List[str] = []

            backups = self.list_backups(include_s3=cleanup_s3)
            local_backups = [b for b in backups if b.get('location') != 's3']
            local_backups.sort(key=lambda x: x['created_at'], reverse=True)

            files_to_keep = set()
            for i, backup in enumerate(local_backups):
                if i < keep_count:
                    files_to_keep.add(backup['file_path'])

            for backup_file in self.backup_dir.glob('*.sql*'):
                if str(backup_file) in files_to_keep:
                    continue
                stat = backup_file.stat()
                file_date = datetime.fromtimestamp(stat.st_mtime)
                if file_date < cutoff_date:
                    backup_file.unlink()
                    cleaned_files.append(str(backup_file))
                    metadata_file = backup_file.with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()
                        cleaned_files.append(str(metadata_file))

            s3_cleaned: List[str] = []
            if cleanup_s3 and self.s3_client and self.s3_bucket:
                s3_backups = [b for b in backups if b.get('location') == 's3']
                s3_backups.sort(key=lambda x: x['created_at'], reverse=True)
                for i, backup in enumerate(s3_backups):
                    if i < keep_count:
                        continue
                    backup_date = datetime.fromisoformat(backup['created_at'].replace('Z', '+00:00'))
                    if backup_date.replace(tzinfo=None) < cutoff_date:
                        try:
                            self.s3_client.delete_object(
                                Bucket=self.s3_bucket,
                                Key=backup['s3_key']
                            )
                            s3_cleaned.append(backup['s3_key'])
                        except ClientError as e:
                            logger.warning(f"Failed to delete S3 backup {backup['s3_key']}: {e}")

            logger.info(f"Cleanup completed: {len(cleaned_files)} local files, {len(s3_cleaned)} S3 files removed")
            return {
                'success': True,
                'local_files_cleaned': cleaned_files,
                's3_files_cleaned': s3_cleaned,
                'total_cleaned': len(cleaned_files) + len(s3_cleaned)
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def verify_backup(self, backup_file: str) -> Dict[str, Any]:
        """Verify backup file integrity."""
        logger.info(f"Verifying backup: {backup_file}")

        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                return {
                    'success': False,
                    'error': f'Backup file not found: {backup_file}'
                }

            if backup_path.suffix == '.gz':
                try:
                    with gzip.open(backup_path, 'rt') as f:
                        for i, _ in enumerate(f):
                            if i > 10:
                                break
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Compressed file is corrupted: {e}'
                    }
            else:
                try:
                    with open(backup_path, 'r') as f:
                        content = f.read(1000)
                        if not content.strip():
                            return {
                                'success': False,
                                'error': 'Backup file is empty'
                            }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Cannot read backup file: {e}'
                    }

            metadata_file = backup_path.with_suffix('.json')
            metadata = None
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.warning(f"Cannot read metadata: {e}")

            file_size = backup_path.stat().st_size
            return {
                'success': True,
                'file_size': file_size,
                'metadata': metadata,
                'compressed': backup_path.suffix == '.gz'
            }

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _parse_database_url(self, url: str) -> Dict[str, Any]:
        """Parse database URL into components."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'username': parsed.username or '',
            'password': parsed.password or ''
        }

    def _compress_backup(self, backup_file: Path) -> Optional[Path]:
        """Compress backup file using gzip."""
        try:
            compressed_file = backup_file.with_suffix(backup_file.suffix + '.gz')
            with open(backup_file, 'rb') as f_in, gzip.open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            logger.info(f"Backup compressed: {compressed_file}")
            return compressed_file
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return None

    def _decompress_backup(self, compressed_file: Path) -> Optional[Path]:
        """Decompress backup file."""
        try:
            if compressed_file.suffix != '.gz':
                return compressed_file
            decompressed_file = compressed_file.with_suffix('')
            with gzip.open(compressed_file, 'rb') as f_in, open(decompressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            logger.info(f"Backup decompressed: {decompressed_file}")
            return decompressed_file
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return None

    def _upload_to_s3(self, backup_file: Path) -> Optional[str]:
        """Upload backup file to S3."""
        try:
            if not self.s3_client or not self.s3_bucket:
                return None
            s3_key = f"backups/{backup_file.name}"
            self.s3_client.upload_file(
                str(backup_file),
                self.s3_bucket,
                s3_key
            )
            logger.info(f"Backup uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return None

    def schedule_automatic_backups(self) -> None:
        """Setup automatic backup scheduling."""
        logger.info("To schedule automatic backups, add the following cron job:")
        logger.info("0 2 * * * /path/to/python /path/to/backup_manager.py --create --compress --upload-s3")
        logger.info("0 3 * * 0 /path/to/python /path/to/backup_manager.py --cleanup --keep-days 30")


def main() -> None:
    """Main backup manager function."""
    parser = argparse.ArgumentParser(description='Database Backup Manager')
    parser.add_argument('--database-url', help='Database connection URL')
    parser.add_argument('--backup-dir', help='Backup directory path')

    # Backup operations
    parser.add_argument('--create', action='store_true', help='Create a new backup')
    parser.add_argument('--restore', help='Restore from backup file')
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--verify', help='Verify backup file')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old backups')

    # Backup options
    parser.add_argument('--backup-name', help='Name for the backup')
    parser.add_argument('--compress', action='store_true', help='Compress backup file')
    parser.add_argument('--upload-s3', action='store_true', help='Upload to S3')
    parser.add_argument('--schema-only', action='store_true', help='Backup schema only')
    parser.add_argument('--exclude-table', action='append', help='Exclude table from backup')

    # Cleanup options
    parser.add_argument('--keep-days', type=int, default=30, help='Days to keep backups')
    parser.add_argument('--keep-count', type=int, default=10, help='Minimum backups to keep')

    # Restore options
    parser.add_argument('--target-database', help='Target database for restore')
    parser.add_argument('--no-clean', action='store_true', help="Don't clean database before restore")

    args = parser.parse_args()
    backup_manager = BackupManager(args.database_url, args.backup_dir)

    if args.create:
        result = backup_manager.create_backup(
            backup_name=args.backup_name,
            compress=args.compress,
            upload_to_s3=args.upload_s3,
            schema_only=args.schema_only,
            exclude_tables=args.exclude_table
        )
        if result['success']:
            print(f"Backup created successfully: {result['backup_file']}")
        else:
            print(f"Backup failed: {result['error']}")
            sys.exit(1)

    elif args.restore:
        result = backup_manager.restore_backup(
            backup_file=args.restore,
            target_database=args.target_database,
            clean_first=not args.no_clean
        )
        if result['success']:
            print(f"Restore completed successfully to: {result['target_database']}")
        else:
            print(f"Restore failed: {result['error']}")
            sys.exit(1)

    elif args.list:
        backups = backup_manager.list_backups(include_s3=True)
        if backups:
            print(f"Found {len(backups)} backups:")
            print(f"{'Name':<30} {'Date':<20} {'Size':<10} {'Location':<10}")
            print("-" * 70)
            for backup in backups:
                name = backup.get('backup_name', 'Unknown')
                date = backup.get('created_at', 'Unknown')[:19]
                size = f"{backup.get('file_size', 0):,}"
                location = backup.get('location', 'local')
                print(f"{name:<30} {date:<20} {size:<10} {location:<10}")
        else:
            print("No backups found")

    elif args.verify:
        result = backup_manager.verify_backup(args.verify)
        if result['success']:
            print("Backup verification successful")
            print(f"File size: {result['file_size']:,} bytes")
            print(f"Compressed: {result['compressed']}")
            if result['metadata']:
                print(f"Created: {result['metadata']['created_at']}")
        else:
            print(f"Backup verification failed: {result['error']}")
            sys.exit(1)

    elif args.cleanup:
        result = backup_manager.cleanup_old_backups(
            keep_days=args.keep_days,
            keep_count=args.keep_count,
            cleanup_s3=True
        )
        if result['success']:
            print(f"Cleanup completed: {result['total_cleaned']} files removed")
        else:
            print(f"Cleanup failed: {result['error']}")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
