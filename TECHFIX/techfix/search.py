"""
Search and Filter Module
Provides search and filtering functionality across the application.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import logging

from . import db

logger = logging.getLogger(__name__)


def search_journal_entries(
    query: str,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    period_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None
) -> List[sqlite3.Row]:
    """Search journal entries with filters."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        conditions = []
        params = []
        
        # Text search
        if query:
            conditions.append(
                "(je.description LIKE ? OR je.document_ref LIKE ? OR je.external_ref LIKE ? OR je.memo LIKE ?)"
            )
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        # Date range
        if date_from:
            conditions.append("date(je.date) >= date(?)")
            params.append(date_from)
        if date_to:
            conditions.append("date(je.date) <= date(?)")
            params.append(date_to)
        
        # Account filter
        if account_id:
            conditions.append("EXISTS (SELECT 1 FROM journal_lines jl WHERE jl.entry_id = je.id AND jl.account_id = ?)")
            params.append(account_id)
        
        # Status filter
        if status:
            conditions.append("je.status = ?")
            params.append(status)
        
        # Period filter
        if period_id:
            conditions.append("je.period_id = ?")
            params.append(period_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT DISTINCT je.*
            FROM journal_entries je
            WHERE {where_clause}
            ORDER BY je.date DESC, je.id DESC
            LIMIT 1000
        """
        
        cur = conn.execute(sql, params)
        return list(cur.fetchall())
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return []
    finally:
        if not owned:
            conn.close()


def search_accounts(
    query: str,
    *,
    account_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    conn: Optional[sqlite3.Connection] = None
) -> List[sqlite3.Row]:
    """Search accounts."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        conditions = []
        params = []
        
        if query:
            conditions.append("(name LIKE ? OR code LIKE ?)")
            search_term = f"%{query}%"
            params.extend([search_term, search_term])
        
        if account_type:
            conditions.append("type = ?")
            params.append(account_type)
        
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT * FROM accounts
            WHERE {where_clause}
            ORDER BY code
        """
        
        cur = conn.execute(sql, params)
        return list(cur.fetchall())
    except Exception as e:
        logger.error(f"Account search error: {e}", exc_info=True)
        return []
    finally:
        if not owned:
            conn.close()


def global_search(
    query: str,
    *,
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Perform global search across all entities."""
    results = {
        'journal_entries': [],
        'accounts': [],
        'customers': [],
        'vendors': [],
    }
    
    if not query or len(query.strip()) < 2:
        return results
    
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        search_term = f"%{query.strip()}%"
        
        # Search journal entries
        try:
            cur = conn.execute(
                """
                SELECT id, date, description, status
                FROM journal_entries
                WHERE description LIKE ? OR document_ref LIKE ? OR external_ref LIKE ?
                ORDER BY date DESC
                LIMIT ?
                """,
                (search_term, search_term, search_term, limit)
            )
            results['journal_entries'] = [dict(row) for row in cur.fetchall()]
        except Exception:
            pass
        
        # Search accounts
        try:
            cur = conn.execute(
                """
                SELECT id, code, name, type
                FROM accounts
                WHERE name LIKE ? OR code LIKE ?
                ORDER BY code
                LIMIT ?
                """,
                (search_term, search_term, limit)
            )
            results['accounts'] = [dict(row) for row in cur.fetchall()]
        except Exception:
            pass
        
        # Search customers
        try:
            cur = conn.execute(
                """
                SELECT id, code, name, contact, email
                FROM customers
                WHERE name LIKE ? OR code LIKE ? OR contact LIKE ? OR email LIKE ?
                ORDER BY name
                LIMIT ?
                """,
                (search_term, search_term, search_term, search_term, limit)
            )
            results['customers'] = [dict(row) for row in cur.fetchall()]
        except Exception:
            pass
        
        # Search vendors
        try:
            cur = conn.execute(
                """
                SELECT id, code, name, contact, email
                FROM vendors
                WHERE name LIKE ? OR code LIKE ? OR contact LIKE ? OR email LIKE ?
                ORDER BY name
                LIMIT ?
                """,
                (search_term, search_term, search_term, search_term, limit)
            )
            results['vendors'] = [dict(row) for row in cur.fetchall()]
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Global search error: {e}", exc_info=True)
    finally:
        if not owned:
            conn.close()
    
    return results

