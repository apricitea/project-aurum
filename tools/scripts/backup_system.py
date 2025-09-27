#!/usr/bin/env python3
"""
Project Aurum - Backup and Recovery System
Comprehensive backup solution for database, logs, and configuration files
"""

import os
import sys
import json
import shutil
import zipfile
import subprocess
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

class BackupSystem:
    """
    Comprehensive backup and recovery system for Project Aurum
    """

    def __init__(self, config_file: Optional[str] = None):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "backups"
        self.config_file = config_file or self.project_root / "backup_config.json"
        self.config = self._load_config()
        self.logger = self._setup_logging()

        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True)

    def _load_config(self) -> Dict:
        """Load backup configuration"""
        default_config = {
            "retention": {
                "daily": 7,    # Keep 7 daily backups
                "weekly": 4,   # Keep 4 weekly backups
                "monthly": 12  # Keep 12 monthly backups
            },
            "compression": True,
            "encryption": False,
            "storage": {
                "local": True,
                "cloud": False,
                "cloud_provider": "aws_s3",
                "cloud_bucket": ""
            },
            "database": {
                "enabled": True,
                "host": "localhost",
                "port": 5432,
                "name": "project_aurum",
                "user": "postgres"
            },
            "files": {
                "include": [
                    "backend/src",
                    "frontend/src",
                    "frontend/public",
                    "scripts",
                    "docker-compose.yml",
                    "*.env.example",
                    "README.md"
                ],
                "exclude": [
                    "node_modules",
                    "*.log",
                    "__pycache__",
                    ".git",
                    "dist",
                    "build",
                    "venv",
                    ".env"
                ]
            },
            "notifications": {
                "email": {
                    "enabled": False,
                    "recipients": [],
                    "smtp_host": "",
                    "smtp_port": 587
                },
                "webhook": {
                    "enabled": False,
                    "url": ""
                }
            }
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    default_config.update(loaded_config)
            except Exception as e:
                logging.warning(f"Could not load config file: {e}. Using defaults.")
        else:
            # Create default config file
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logging.info(f"Created default config file: {self.config_file}")

        return default_config

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for backup system"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        logger = logging.getLogger('backup_system')
        logger.setLevel(logging.INFO)

        # File handler
        file_handler = logging.FileHandler(log_dir / "backup.log")
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def create_backup(self, backup_type: str = "full") -> Tuple[bool, str]:
        """
        Create a backup of the system

        Args:
            backup_type: Type of backup ('full', 'database', 'files')

        Returns:
            Tuple of (success, backup_path)
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"aurum_backup_{backup_type}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)

            self.logger.info(f"Starting {backup_type} backup: {backup_name}")

            # Create backup manifest
            manifest = {
                "backup_type": backup_type,
                "timestamp": timestamp,
                "datetime": datetime.now().isoformat(),
                "version": self._get_app_version(),
                "components": []
            }

            if backup_type in ["full", "database"]:
                if self._backup_database(backup_path):
                    manifest["components"].append("database")
                    self.logger.info("Database backup completed")
                else:
                    self.logger.error("Database backup failed")
                    return False, ""

            if backup_type in ["full", "files"]:
                if self._backup_files(backup_path):
                    manifest["components"].append("files")
                    self.logger.info("Files backup completed")
                else:
                    self.logger.error("Files backup failed")
                    return False, ""

            # Save manifest
            manifest_path = backup_path / "manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)

            # Create checksum
            self._create_checksum(backup_path)

            # Compress if enabled
            if self.config.get("compression", True):
                compressed_path = self._compress_backup(backup_path)
                if compressed_path:
                    shutil.rmtree(backup_path)
                    backup_path = compressed_path

            # Upload to cloud if enabled
            if self.config.get("storage", {}).get("cloud", False):
                self._upload_to_cloud(backup_path)

            # Clean old backups
            self._cleanup_old_backups()

            # Send notifications
            self._send_notification(f"Backup completed successfully: {backup_name}")

            self.logger.info(f"Backup completed successfully: {backup_path}")
            return True, str(backup_path)

        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            self._send_notification(f"Backup failed: {str(e)}", success=False)
            return False, ""

    def _backup_database(self, backup_path: Path) -> bool:
        """Backup database using pg_dump"""
        try:
            db_config = self.config.get("database", {})
            if not db_config.get("enabled", True):
                return True

            db_backup_path = backup_path / "database"
            db_backup_path.mkdir(exist_ok=True)

            # Environment variables for pg_dump
            env = os.environ.copy()
            if "password" in db_config:
                env["PGPASSWORD"] = db_config["password"]

            # Dump database schema and data
            dump_file = db_backup_path / f"{db_config['name']}.sql"
            cmd = [
                "pg_dump",
                "-h", db_config.get("host", "localhost"),
                "-p", str(db_config.get("port", 5432)),
                "-U", db_config.get("user", "postgres"),
                "-d", db_config["name"],
                "-f", str(dump_file),
                "--verbose",
                "--clean",
                "--create"
            ]

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info("Database dump completed successfully")

                # Also create a data-only dump for faster restores
                data_dump_file = db_backup_path / f"{db_config['name']}_data.sql"
                data_cmd = cmd.copy()
                data_cmd[-3] = str(data_dump_file)  # Replace filename
                data_cmd.append("--data-only")

                subprocess.run(data_cmd, env=env, capture_output=True)

                return True
            else:
                self.logger.error(f"Database dump failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Database backup error: {str(e)}")
            return False

    def _backup_files(self, backup_path: Path) -> bool:
        """Backup application files"""
        try:
            files_backup_path = backup_path / "files"
            files_backup_path.mkdir(exist_ok=True)

            include_patterns = self.config.get("files", {}).get("include", [])
            exclude_patterns = self.config.get("files", {}).get("exclude", [])

            # Copy included files and directories
            for pattern in include_patterns:
                self._copy_pattern(pattern, files_backup_path, exclude_patterns)

            return True

        except Exception as e:
            self.logger.error(f"Files backup error: {str(e)}")
            return False

    def _copy_pattern(self, pattern: str, dest: Path, exclude_patterns: List[str]):
        """Copy files matching pattern to destination"""
        source_path = self.project_root / pattern

        if source_path.is_file():
            dest_file = dest / pattern
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_file)
        elif source_path.is_dir():
            for root, dirs, files in os.walk(source_path):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not any(
                    self._matches_pattern(d, excl) for excl in exclude_patterns
                )]

                for file in files:
                    if not any(self._matches_pattern(file, excl) for excl in exclude_patterns):
                        src_file = Path(root) / file
                        rel_path = src_file.relative_to(self.project_root)
                        dest_file = dest / rel_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest_file)

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches exclude pattern"""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)

    def _create_checksum(self, backup_path: Path):
        """Create checksums for backup verification"""
        checksum_file = backup_path / "checksums.txt"
        with open(checksum_file, 'w') as f:
            for file_path in backup_path.rglob('*'):
                if file_path.is_file() and file_path.name != "checksums.txt":
                    checksum = self._calculate_checksum(file_path)
                    rel_path = file_path.relative_to(backup_path)
                    f.write(f"{checksum}  {rel_path}\n")

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _compress_backup(self, backup_path: Path) -> Optional[Path]:
        """Compress backup directory"""
        try:
            zip_path = backup_path.with_suffix('.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in backup_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(backup_path.parent)
                        zipf.write(file_path, arcname)
            return zip_path
        except Exception as e:
            self.logger.error(f"Compression failed: {str(e)}")
            return None

    def _upload_to_cloud(self, backup_path: Path):
        """Upload backup to cloud storage"""
        # Placeholder for cloud upload implementation
        # This would integrate with AWS S3, Google Cloud Storage, etc.
        self.logger.info(f"Cloud upload placeholder for: {backup_path}")

    def _cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        retention = self.config.get("retention", {})

        # Group backups by type and date
        backups = self._get_existing_backups()

        for backup_type, type_backups in backups.items():
            # Sort by date (newest first)
            type_backups.sort(key=lambda x: x['datetime'], reverse=True)

            # Apply retention policy
            to_keep = retention.get("daily", 7)
            to_remove = type_backups[to_keep:]

            for backup in to_remove:
                try:
                    backup_path = Path(backup['path'])
                    if backup_path.exists():
                        if backup_path.is_file():
                            backup_path.unlink()
                        else:
                            shutil.rmtree(backup_path)
                        self.logger.info(f"Removed old backup: {backup_path}")
                except Exception as e:
                    self.logger.error(f"Failed to remove backup {backup['path']}: {e}")

    def _get_existing_backups(self) -> Dict[str, List[Dict]]:
        """Get list of existing backups grouped by type"""
        backups = {}

        for backup_path in self.backup_dir.iterdir():
            if backup_path.name.startswith("aurum_backup_"):
                parts = backup_path.name.split("_")
                if len(parts) >= 4:
                    backup_type = parts[2]
                    timestamp = "_".join(parts[3:]).replace('.zip', '')

                    try:
                        backup_datetime = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")

                        if backup_type not in backups:
                            backups[backup_type] = []

                        backups[backup_type].append({
                            'path': str(backup_path),
                            'type': backup_type,
                            'datetime': backup_datetime,
                            'timestamp': timestamp
                        })
                    except ValueError:
                        continue

        return backups

    def _send_notification(self, message: str, success: bool = True):
        """Send notification about backup status"""
        # Email notification
        email_config = self.config.get("notifications", {}).get("email", {})
        if email_config.get("enabled", False):
            self._send_email_notification(message, success)

        # Webhook notification
        webhook_config = self.config.get("notifications", {}).get("webhook", {})
        if webhook_config.get("enabled", False):
            self._send_webhook_notification(message, success)

    def _send_email_notification(self, message: str, success: bool):
        """Send email notification"""
        # Placeholder for email notification
        self.logger.info(f"Email notification: {message}")

    def _send_webhook_notification(self, message: str, success: bool):
        """Send webhook notification"""
        # Placeholder for webhook notification
        self.logger.info(f"Webhook notification: {message}")

    def _get_app_version(self) -> str:
        """Get application version from package.json or git"""
        try:
            package_json = self.project_root / "frontend" / "package.json"
            if package_json.exists():
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    return data.get("version", "unknown")
        except:
            pass

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        return "unknown"

    def restore_backup(self, backup_path: str, restore_type: str = "full") -> bool:
        """
        Restore from backup

        Args:
            backup_path: Path to backup file or directory
            restore_type: Type of restore ('full', 'database', 'files')
        """
        try:
            backup_path = Path(backup_path)
            self.logger.info(f"Starting restore from: {backup_path}")

            # Extract if it's a zip file
            if backup_path.suffix == '.zip':
                extract_path = backup_path.parent / backup_path.stem
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(extract_path)
                backup_path = extract_path

            # Verify backup integrity
            if not self._verify_backup(backup_path):
                self.logger.error("Backup verification failed")
                return False

            # Load manifest
            manifest_path = backup_path / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                self.logger.info(f"Restoring backup from {manifest['datetime']}")

            # Restore database
            if restore_type in ["full", "database"]:
                db_backup_path = backup_path / "database"
                if db_backup_path.exists():
                    if self._restore_database(db_backup_path):
                        self.logger.info("Database restore completed")
                    else:
                        self.logger.error("Database restore failed")
                        return False

            # Restore files
            if restore_type in ["full", "files"]:
                files_backup_path = backup_path / "files"
                if files_backup_path.exists():
                    if self._restore_files(files_backup_path):
                        self.logger.info("Files restore completed")
                    else:
                        self.logger.error("Files restore failed")
                        return False

            self.logger.info("Restore completed successfully")
            self._send_notification(f"Restore completed successfully from {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"Restore failed: {str(e)}")
            self._send_notification(f"Restore failed: {str(e)}", success=False)
            return False

    def _verify_backup(self, backup_path: Path) -> bool:
        """Verify backup integrity using checksums"""
        checksum_file = backup_path / "checksums.txt"
        if not checksum_file.exists():
            self.logger.warning("No checksum file found, skipping verification")
            return True

        try:
            with open(checksum_file, 'r') as f:
                for line in f:
                    expected_checksum, rel_path = line.strip().split('  ', 1)
                    file_path = backup_path / rel_path

                    if not file_path.exists():
                        self.logger.error(f"Missing file: {rel_path}")
                        return False

                    actual_checksum = self._calculate_checksum(file_path)
                    if actual_checksum != expected_checksum:
                        self.logger.error(f"Checksum mismatch for {rel_path}")
                        return False

            self.logger.info("Backup verification successful")
            return True

        except Exception as e:
            self.logger.error(f"Backup verification failed: {str(e)}")
            return False

    def _restore_database(self, db_backup_path: Path) -> bool:
        """Restore database from backup"""
        try:
            db_config = self.config.get("database", {})
            dump_file = db_backup_path / f"{db_config['name']}.sql"

            if not dump_file.exists():
                self.logger.error("Database dump file not found")
                return False

            # Environment variables for psql
            env = os.environ.copy()
            if "password" in db_config:
                env["PGPASSWORD"] = db_config["password"]

            # Restore database
            cmd = [
                "psql",
                "-h", db_config.get("host", "localhost"),
                "-p", str(db_config.get("port", 5432)),
                "-U", db_config.get("user", "postgres"),
                "-f", str(dump_file)
            ]

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info("Database restore completed successfully")
                return True
            else:
                self.logger.error(f"Database restore failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Database restore error: {str(e)}")
            return False

    def _restore_files(self, files_backup_path: Path) -> bool:
        """Restore files from backup"""
        try:
            # Create backup of current files before restore
            current_backup_path = self.backup_dir / f"pre_restore_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            current_backup_path.mkdir(exist_ok=True)

            # Copy files from backup to project root
            for backup_file in files_backup_path.rglob('*'):
                if backup_file.is_file():
                    rel_path = backup_file.relative_to(files_backup_path)
                    dest_path = self.project_root / rel_path

                    # Backup current file if it exists
                    if dest_path.exists():
                        backup_dest = current_backup_path / rel_path
                        backup_dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(dest_path, backup_dest)

                    # Restore file
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, dest_path)

            return True

        except Exception as e:
            self.logger.error(f"Files restore error: {str(e)}")
            return False

    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []

        for backup_path in self.backup_dir.iterdir():
            if backup_path.name.startswith("aurum_backup_"):
                # Try to load manifest
                manifest = {}
                if backup_path.is_dir():
                    manifest_path = backup_path / "manifest.json"
                    if manifest_path.exists():
                        try:
                            with open(manifest_path, 'r') as f:
                                manifest = json.load(f)
                        except:
                            pass

                # Parse from filename if no manifest
                parts = backup_path.name.split("_")
                if len(parts) >= 4:
                    backup_type = parts[2]
                    timestamp = "_".join(parts[3:]).replace('.zip', '')

                    try:
                        backup_datetime = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")

                        backups.append({
                            'path': str(backup_path),
                            'name': backup_path.name,
                            'type': manifest.get('backup_type', backup_type),
                            'datetime': backup_datetime.isoformat(),
                            'size': self._get_size(backup_path),
                            'components': manifest.get('components', []),
                            'version': manifest.get('version', 'unknown')
                        })
                    except ValueError:
                        continue

        # Sort by datetime (newest first)
        backups.sort(key=lambda x: x['datetime'], reverse=True)
        return backups

    def _get_size(self, path: Path) -> int:
        """Get size of file or directory in bytes"""
        if path.is_file():
            return path.stat().st_size
        else:
            total_size = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size

def main():
    parser = argparse.ArgumentParser(description="Project Aurum Backup System")
    parser.add_argument("command", choices=["backup", "restore", "list", "cleanup"])
    parser.add_argument("--type", choices=["full", "database", "files"], default="full")
    parser.add_argument("--backup-path", help="Path to backup for restore")
    parser.add_argument("--config", help="Path to configuration file")

    args = parser.parse_args()

    backup_system = BackupSystem(args.config)

    if args.command == "backup":
        success, backup_path = backup_system.create_backup(args.type)
        if success:
            print(f"Backup created successfully: {backup_path}")
            sys.exit(0)
        else:
            print("Backup failed")
            sys.exit(1)

    elif args.command == "restore":
        if not args.backup_path:
            print("Error: --backup-path required for restore")
            sys.exit(1)

        success = backup_system.restore_backup(args.backup_path, args.type)
        if success:
            print("Restore completed successfully")
            sys.exit(0)
        else:
            print("Restore failed")
            sys.exit(1)

    elif args.command == "list":
        backups = backup_system.list_backups()
        if backups:
            print(f"{'Name':<40} {'Type':<10} {'Date':<20} {'Size':<10}")
            print("-" * 80)
            for backup in backups:
                size_mb = backup['size'] / (1024 * 1024)
                print(f"{backup['name']:<40} {backup['type']:<10} {backup['datetime'][:19]:<20} {size_mb:.1f}MB")
        else:
            print("No backups found")

    elif args.command == "cleanup":
        backup_system._cleanup_old_backups()
        print("Cleanup completed")

if __name__ == "__main__":
    main()