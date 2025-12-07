"""
Notifications and Reminders Module
Handles system notifications, reminders, and alerts.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import logging

from . import db

logger = logging.getLogger(__name__)


def create_notification(
    user_id: Optional[int],
    title: str,
    message: str,
    notification_type: str = "info",
    *,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[int]:
    """Create a notification."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        cur = conn.execute(
            """
            INSERT INTO notifications (user_id, title, message, type, created_at, is_read)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                user_id,
                title,
                message,
                notification_type,
                datetime.now(timezone.utc).isoformat()
            )
        )
        conn.commit()
        return int(cur.lastrowid)
    except Exception as e:
        logger.error(f"Error creating notification: {e}", exc_info=True)
        return None
    finally:
        if not owned:
            conn.close()


def get_user_notifications(
    user_id: Optional[int],
    unread_only: bool = False,
    limit: int = 50,
    *,
    conn: Optional[sqlite3.Connection] = None
) -> List[sqlite3.Row]:
    """Get notifications for a user."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        conditions = ["(user_id = ? OR user_id IS NULL)"]
        params = [user_id]
        
        if unread_only:
            conditions.append("is_read = 0")
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
            SELECT * FROM notifications
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        
        cur = conn.execute(sql, params + [limit])
        return list(cur.fetchall())
    except Exception as e:
        logger.error(f"Error getting notifications: {e}", exc_info=True)
        return []
    finally:
        if not owned:
            conn.close()


def mark_notification_read(notification_id: int, *, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Mark a notification as read."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        conn.execute(
            "UPDATE notifications SET is_read = 1, read_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), notification_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error marking notification read: {e}", exc_info=True)
        return False
    finally:
        if not owned:
            conn.close()


def check_reversing_entry_reminders(*, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Check for reversing entries that need attention."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    reminders = []
    
    try:
        # Find reversing entries due soon (within 7 days)
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()
        
        cur = conn.execute(
            """
            SELECT req.*, je.description, je.date
            FROM reversing_entry_queue req
            JOIN journal_entries je ON req.original_entry_id = je.id
            WHERE req.status = 'pending'
              AND date(req.reverse_on) <= date(?)
              AND date(req.reverse_on) >= date('now')
            ORDER BY req.reverse_on
            """,
            (due_date,)
        )
        
        for row in cur.fetchall():
            reminders.append({
                'type': 'reversing_entry',
                'id': row['id'],
                'message': f"Reversing entry due: {row['reverse_on']}",
                'entry_description': row['description'],
                'due_date': row['reverse_on'],
            })
    except Exception as e:
        logger.error(f"Error checking reversing entry reminders: {e}", exc_info=True)
    finally:
        if not owned:
            conn.close()
    
    return reminders


def check_period_closing_reminders(*, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Check for periods that should be closed."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    reminders = []
    
    try:
        # Find periods past their end date that aren't closed
        cur = conn.execute(
            """
            SELECT id, name, end_date
            FROM accounting_periods
            WHERE is_closed = 0
              AND end_date IS NOT NULL
              AND date(end_date) < date('now')
            ORDER BY end_date
            """
        )
        
        for row in cur.fetchall():
            reminders.append({
                'type': 'period_closing',
                'id': row['id'],
                'message': f"Period '{row['name']}' ended on {row['end_date']} and should be closed",
                'period_name': row['name'],
                'end_date': row['end_date'],
            })
    except Exception as e:
        logger.error(f"Error checking period closing reminders: {e}", exc_info=True)
    finally:
        if not owned:
            conn.close()
    
    return reminders

