"""
Backup and Restore Module
Handles database backup, restore, and data export/import.
"""
from __future__ import annotations

import sqlite3
import shutil
import json
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

from . import db

logger = logging.getLogger(__name__)

BACKUP_DIR = db.DB_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def create_backup(description: Optional[str] = None) -> Optional[Path]:
    """Create a backup of the database."""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"techfix_backup_{timestamp}"
        if description:
            safe_desc = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in description[:50])
            backup_name = f"{backup_name}_{safe_desc}"
        
        backup_path = BACKUP_DIR / f"{backup_name}.db"
        
        # Copy database file
        if db.DB_PATH.exists():
            shutil.copy2(db.DB_PATH, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return backup_path
        else:
            logger.error("Database file not found")
            return None
    except Exception as e:
        logger.error(f"Backup creation failed: {e}", exc_info=True)
        return None


def create_full_backup(description: Optional[str] = None) -> Optional[Path]:
    """Create a full backup including database and settings."""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"techfix_full_backup_{timestamp}"
        if description:
            safe_desc = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in description[:50])
            backup_name = f"{backup_name}_{safe_desc}"
        
        backup_zip = BACKUP_DIR / f"{backup_name}.zip"
        
        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database
            if db.DB_PATH.exists():
                zipf.write(db.DB_PATH, db.DB_PATH.name)
            
            # Add settings
            settings_path = db.DB_DIR / "settings.json"
            if settings_path.exists():
                zipf.write(settings_path, "settings.json")
            
            # Add metadata
            metadata = {
                'timestamp': timestamp,
                'description': description,
                'version': db.SCHEMA_VERSION,
            }
            zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
        
        logger.info(f"Full backup created: {backup_zip}")
        return backup_zip
    except Exception as e:
        logger.error(f"Full backup creation failed: {e}", exc_info=True)
        return None


def restore_backup(backup_path: Path, verify: bool = True) -> bool:
    """Restore database from backup."""
    try:
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        # Verify backup
        if verify:
            try:
                test_conn = sqlite3.connect(str(backup_path))
                test_conn.execute("SELECT 1")
                test_conn.close()
            except Exception as e:
                logger.error(f"Backup verification failed: {e}")
                return False
        
        # Create backup of current database before restore
        current_backup = create_backup("pre_restore")
        if not current_backup:
            logger.warning("Could not create pre-restore backup")
        
        # Close any open connections
        # Note: In production, you'd want to ensure all connections are closed
        
        # Restore database
        shutil.copy2(backup_path, db.DB_PATH)
        
        logger.info(f"Database restored from: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Restore failed: {e}", exc_info=True)
        return False


def restore_full_backup(backup_zip: Path) -> bool:
    """Restore from full backup zip file."""
    try:
        if not backup_zip.exists():
            logger.error(f"Backup zip not found: {backup_zip}")
            return False
        
        # Create pre-restore backup
        current_backup = create_backup("pre_restore")
        if not current_backup:
            logger.warning("Could not create pre-restore backup")
        
        # Extract backup
        extract_dir = BACKUP_DIR / "restore_temp"
        extract_dir.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(backup_zip, 'r') as zipf:
                zipf.extractall(extract_dir)
            
            # Restore database
            db_file = extract_dir / db.DB_PATH.name
            if db_file.exists():
                shutil.copy2(db_file, db.DB_PATH)
            
            # Restore settings
            settings_file = extract_dir / "settings.json"
            if settings_file.exists():
                shutil.copy2(settings_file, db.DB_DIR / "settings.json")
            
            logger.info(f"Full backup restored from: {backup_zip}")
            return True
        finally:
            # Cleanup
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
    except Exception as e:
        logger.error(f"Full restore failed: {e}", exc_info=True)
        return False


def list_backups() -> List[Dict[str, Any]]:
    """List all available backups."""
    backups = []
    
    try:
        # List database backups
        for backup_file in BACKUP_DIR.glob("techfix_backup_*.db"):
            try:
                stat = backup_file.stat()
                backups.append({
                    'path': backup_file,
                    'name': backup_file.name,
                    'type': 'database',
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                })
            except Exception:
                pass
        
        # List full backups
        for backup_file in BACKUP_DIR.glob("techfix_full_backup_*.zip"):
            try:
                stat = backup_file.stat()
                backups.append({
                    'path': backup_file,
                    'name': backup_file.name,
                    'type': 'full',
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                })
            except Exception:
                pass
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
    except Exception as e:
        logger.error(f"Error listing backups: {e}", exc_info=True)
    
    return backups


def delete_backup(backup_path: Path) -> bool:
    """Delete a backup file."""
    try:
        if backup_path.exists() and backup_path.parent == BACKUP_DIR:
            backup_path.unlink()
            logger.info(f"Backup deleted: {backup_path}")
            return True
        else:
            logger.error(f"Invalid backup path: {backup_path}")
            return False
    except Exception as e:
        logger.error(f"Error deleting backup: {e}", exc_info=True)
        return False


def export_data_to_json(output_path: Path, tables: Optional[List[str]] = None) -> bool:
    """Export database data to JSON file."""
    try:
        conn = db.get_connection()
        data = {}
        
        try:
            if tables is None:
                # Export all tables
                cur = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                tables = [row[0] for row in cur.fetchall()]
            
            for table in tables:
                cur = conn.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                data[table] = [dict(row) for row in rows]
            
            output_path.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')
            logger.info(f"Data exported to: {output_path}")
            return True
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        return False


def import_data_from_json(input_path: Path, tables: Optional[List[str]] = None) -> bool:
    """Import data from JSON file."""
    try:
        data = json.loads(input_path.read_text(encoding='utf-8'))
        conn = db.get_connection()
        
        try:
            conn.execute("BEGIN TRANSACTION")
            
            if tables is None:
                tables = list(data.keys())
            
            for table in tables:
                if table not in data:
                    continue
                
                # Clear existing data (optional - you might want to merge instead)
                # conn.execute(f"DELETE FROM {table}")
                
                # Insert data
                for row in data[table]:
                    columns = ', '.join(row.keys())
                    placeholders = ', '.join(['?' for _ in row])
                    values = list(row.values())
                    conn.execute(
                        f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
                        values
                    )
            
            conn.commit()
            logger.info(f"Data imported from: {input_path}")
            return True
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return False

