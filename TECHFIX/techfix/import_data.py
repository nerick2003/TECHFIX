"""
Data Import Module
Handles importing data from Excel, CSV, and other formats.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import logging

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("pandas not available, CSV import disabled")

from . import db
from . import validation
from .accounting import AccountingEngine, JournalLine

logger = logging.getLogger(__name__)


def import_transactions_from_excel(
    file_path: Path,
    *,
    period_id: Optional[int] = None,
    default_status: str = "draft",
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[int, int, List[str]]:
    """Import transactions from Excel file.
    
    Returns: (success_count, error_count, error_messages)
    """
    if not PANDAS_AVAILABLE:
        return (0, 0, ["pandas library not available"])
    
    errors = []
    success_count = 0
    error_count = 0
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Expected columns: Date, Description, DebitAccount, DebitAmount, CreditAccount, CreditAmount
        required_columns = ['Date', 'Description', 'DebitAccount', 'DebitAmount', 'CreditAccount', 'CreditAmount']
        
        # Check columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return (0, 0, [f"Missing required columns: {', '.join(missing_cols)}"])
        
        engine = AccountingEngine(conn=conn)
        
        for idx, row in df.iterrows():
            try:
                # Validate and parse data
                date_str = str(row['Date']).strip()
                if pd.isna(row['Date']):
                    errors.append(f"Row {idx+2}: Missing date")
                    error_count += 1
                    continue
                
                # Convert date if needed
                if isinstance(row['Date'], pd.Timestamp):
                    date_str = row['Date'].strftime('%Y-%m-%d')
                elif isinstance(row['Date'], datetime):
                    date_str = row['Date'].strftime('%Y-%m-%d')
                
                valid_date, date_obj = validation.validate_date(date_str)
                if not valid_date:
                    errors.append(f"Row {idx+2}: Invalid date format: {date_str}")
                    error_count += 1
                    continue
                
                description = validation.sanitize_string(str(row['Description']), max_length=500)
                if not description:
                    errors.append(f"Row {idx+2}: Missing description")
                    error_count += 1
                    continue
                
                # Parse amounts
                valid_debit, debit_amt = validation.validate_amount(str(row['DebitAmount']))
                valid_credit, credit_amt = validation.validate_amount(str(row['CreditAmount']))
                
                if not valid_debit or not valid_credit:
                    errors.append(f"Row {idx+2}: Invalid amounts")
                    error_count += 1
                    continue
                
                if debit_amt == 0 and credit_amt == 0:
                    errors.append(f"Row {idx+2}: Both amounts cannot be zero")
                    error_count += 1
                    continue
                
                # Get account IDs
                debit_acct = str(row['DebitAccount']).strip()
                credit_acct = str(row['CreditAccount']).strip()
                
                # Resolve account IDs (simplified - would need proper account lookup)
                debit_id = _resolve_account_id(debit_acct, conn=conn)
                credit_id = _resolve_account_id(credit_acct, conn=conn)
                
                if not debit_id:
                    errors.append(f"Row {idx+2}: Debit account not found: {debit_acct}")
                    error_count += 1
                    continue
                
                if not credit_id:
                    errors.append(f"Row {idx+2}: Credit account not found: {credit_acct}")
                    error_count += 1
                    continue
                
                # Create journal lines
                lines = []
                if debit_amt > 0:
                    lines.append(JournalLine(account_id=debit_id, debit=debit_amt, credit=0.0))
                if credit_amt > 0:
                    lines.append(JournalLine(account_id=credit_id, debit=0.0, credit=credit_amt))
                
                # Validate lines
                valid, error_msg = validation.validate_journal_entry_lines(lines)
                if not valid:
                    errors.append(f"Row {idx+2}: {error_msg}")
                    error_count += 1
                    continue
                
                # Record entry
                engine.record_entry(
                    date=date_str,
                    description=description,
                    lines=lines,
                    status=default_status,
                    period_id=period_id
                )
                
                success_count += 1
                
            except Exception as e:
                errors.append(f"Row {idx+2}: {str(e)}")
                error_count += 1
                logger.error(f"Error importing row {idx+2}: {e}", exc_info=True)
        
        return (success_count, error_count, errors)
    
    except Exception as e:
        logger.error(f"Excel import error: {e}", exc_info=True)
        return (0, 0, [f"Import error: {str(e)}"])


def import_transactions_from_csv(
    file_path: Path,
    *,
    period_id: Optional[int] = None,
    default_status: str = "draft",
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[int, int, List[str]]:
    """Import transactions from CSV file.
    
    Returns: (success_count, error_count, error_messages)
    """
    if not PANDAS_AVAILABLE:
        return (0, 0, ["pandas library not available"])
    
    try:
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Use same logic as Excel import
        return import_transactions_from_excel(
            file_path,
            period_id=period_id,
            default_status=default_status,
            conn=conn
        )
    except Exception as e:
        logger.error(f"CSV import error: {e}", exc_info=True)
        return (0, 0, [f"Import error: {str(e)}"])


def _resolve_account_id(account_identifier: str, *, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
    """Resolve account identifier (code or name) to account ID."""
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        # Try by code first
        cur = conn.execute("SELECT id FROM accounts WHERE code = ? AND is_active = 1", (account_identifier,))
        row = cur.fetchone()
        if row:
            return int(row['id'])
        
        # Try by name
        cur = conn.execute("SELECT id FROM accounts WHERE name = ? AND is_active = 1", (account_identifier,))
        row = cur.fetchone()
        if row:
            return int(row['id'])
        
        return None
    except Exception as e:
        logger.error(f"Error resolving account: {e}", exc_info=True)
        return None
    finally:
        if not owned:
            conn.close()

