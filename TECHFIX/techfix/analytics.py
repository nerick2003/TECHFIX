"""
Analytics and Dashboard Module
Provides data analytics, metrics, and dashboard functionality.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from . import db

logger = logging.getLogger(__name__)


def get_financial_metrics(
    period_id: Optional[int] = None,
    *,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """Get key financial metrics."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    metrics = {}
    
    try:
        if period_id:
            # Include transactions in the specified period OR transactions with no period assigned (NULL)
            period_filter = "AND (je.period_id = ? OR je.period_id IS NULL)"
            params = [period_id]
        else:
            period_filter = ""
            params = []
        
        # Total revenue (handles both Revenue and Contra Revenue accounts)
        # Revenue accounts: credit increases revenue, so use (credit - debit)
        # Contra Revenue accounts: debit reduces revenue, so subtract (debit - credit)
        # This matches the logic in accounting.py generate_income_statement()
        # Include both 'posted' and 'draft' status transactions
        cur = conn.execute(
            f"""
            SELECT 
                COALESCE(SUM(CASE WHEN a.type = 'Revenue' THEN jl.credit - jl.debit ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN a.type = 'Contra Revenue' THEN jl.debit - jl.credit ELSE 0 END), 0) as total
            FROM journal_lines jl
            JOIN journal_entries je ON jl.entry_id = je.id
            JOIN accounts a ON jl.account_id = a.id
            WHERE a.type IN ('Revenue', 'Contra Revenue')
              AND je.status IN ('posted', 'draft')
              {period_filter}
            """,
            params
        )
        row = cur.fetchone()
        metrics['total_revenue'] = float(row['total']) if row else 0.0
        
        # Total expenses
        # Include both 'posted' and 'draft' status transactions
        cur = conn.execute(
            f"""
            SELECT COALESCE(SUM(jl.debit - jl.credit), 0) as total
            FROM journal_lines jl
            JOIN journal_entries je ON jl.entry_id = je.id
            JOIN accounts a ON jl.account_id = a.id
            WHERE a.type = 'Expense'
              AND je.status IN ('posted', 'draft')
              {period_filter}
            """,
            params
        )
        row = cur.fetchone()
        metrics['total_expenses'] = float(row['total']) if row else 0.0
        
        # Net income
        metrics['net_income'] = metrics['total_revenue'] - metrics['total_expenses']
        
        # Total assets
        cur = conn.execute(
            f"""
            SELECT COALESCE(SUM(
                CASE 
                    WHEN a.type = 'Asset' THEN jl.debit - jl.credit
                    WHEN a.type = 'Contra Asset' THEN jl.credit - jl.debit
                    ELSE 0
                END
            ), 0) as total
            FROM journal_lines jl
            JOIN journal_entries je ON jl.entry_id = je.id
            JOIN accounts a ON jl.account_id = a.id
            WHERE a.type IN ('Asset', 'Contra Asset')
              AND je.status = 'posted'
              {period_filter}
            """,
            params
        )
        row = cur.fetchone()
        metrics['total_assets'] = float(row['total']) if row else 0.0
        
        # Total liabilities
        cur = conn.execute(
            f"""
            SELECT COALESCE(SUM(jl.credit - jl.debit), 0) as total
            FROM journal_lines jl
            JOIN journal_entries je ON jl.entry_id = je.id
            JOIN accounts a ON jl.account_id = a.id
            WHERE a.type = 'Liability'
              AND je.status = 'posted'
              {period_filter}
            """,
            params
        )
        row = cur.fetchone()
        metrics['total_liabilities'] = float(row['total']) if row else 0.0
        
        # Total equity
        cur = conn.execute(
            f"""
            SELECT COALESCE(SUM(jl.credit - jl.debit), 0) as total
            FROM journal_lines jl
            JOIN journal_entries je ON jl.entry_id = je.id
            JOIN accounts a ON jl.account_id = a.id
            WHERE a.type = 'Equity'
              AND je.status = 'posted'
              {period_filter}
            """,
            params
        )
        row = cur.fetchone()
        metrics['total_equity'] = float(row['total']) if row else 0.0
        
        # Transaction count
        if period_id:
            # Include transactions in the specified period OR transactions with no period assigned (NULL)
            count_filter = "AND (period_id = ? OR period_id IS NULL)"
            count_params = [period_id]
        else:
            count_filter = ""
            count_params = []
        
        cur = conn.execute(
            f"""
            SELECT COUNT(*) as count
            FROM journal_entries
            WHERE status IN ('posted', 'draft')
              {count_filter}
            """,
            count_params
        )
        row = cur.fetchone()
        metrics['transaction_count'] = int(row['count']) if row else 0
        
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}", exc_info=True)
        # Return default values on error
        if not metrics:
            metrics = {
                'total_revenue': 0.0,
                'total_expenses': 0.0,
                'net_income': 0.0,
                'total_assets': 0.0,
                'total_liabilities': 0.0,
                'total_equity': 0.0,
                'transaction_count': 0
            }
    finally:
        if not owned:
            conn.close()
    
    # Ensure all metrics are present
    if 'transaction_count' not in metrics:
        metrics['transaction_count'] = 0
    if 'net_income' not in metrics:
        metrics['net_income'] = metrics.get('total_revenue', 0.0) - metrics.get('total_expenses', 0.0)
    
    return metrics


def get_revenue_trend(
    days: int = 30,
    *,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """Get revenue trend over time."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    trend = []
    
    try:
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        
        cur = conn.execute(
            """
            SELECT 
                date(je.date) as day,
                COALESCE(SUM(CASE WHEN a.type = 'Revenue' THEN jl.credit - jl.debit ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN a.type = 'Contra Revenue' THEN jl.debit - jl.credit ELSE 0 END), 0) as revenue
            FROM journal_lines jl
            JOIN journal_entries je ON jl.entry_id = je.id
            JOIN accounts a ON jl.account_id = a.id
            WHERE a.type IN ('Revenue', 'Contra Revenue')
              AND je.status IN ('posted', 'draft')
              AND date(je.date) >= date(?)
            GROUP BY date(je.date)
            ORDER BY date(je.date)
            """,
            (start_date,)
        )
        
        for row in cur.fetchall():
            trend.append({
                'date': row['day'],
                'revenue': float(row['revenue'])
            })
    except Exception as e:
        logger.error(f"Error getting revenue trend: {e}", exc_info=True)
    finally:
        if not owned:
            conn.close()
    
    return trend


def get_expense_breakdown(
    period_id: Optional[int] = None,
    *,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """Get expense breakdown by account."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    breakdown = []
    
    try:
        period_filter = "AND je.period_id = ?" if period_id else ""
        params = [period_id] if period_id else []
        
        cur = conn.execute(
            f"""
            SELECT 
                a.id,
                a.code,
                a.name,
                COALESCE(SUM(jl.debit - jl.credit), 0) as total
            FROM journal_lines jl
            JOIN journal_entries je ON jl.entry_id = je.id
            JOIN accounts a ON jl.account_id = a.id
            WHERE a.type = 'Expense'
              AND je.status = 'posted'
              {period_filter}
            GROUP BY a.id, a.code, a.name
            HAVING total > 0
            ORDER BY total DESC
            LIMIT 20
            """,
            params
        )
        
        for row in cur.fetchall():
            breakdown.append({
                'account_id': row['id'],
                'account_code': row['code'],
                'account_name': row['name'],
                'amount': float(row['total'])
            })
    except Exception as e:
        logger.error(f"Error getting expense breakdown: {e}", exc_info=True)
    finally:
        if not owned:
            conn.close()
    
    return breakdown

