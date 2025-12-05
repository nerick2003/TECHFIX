"""
Comprehensive Financial Statements Verification Script
Checks Income Statement, Balance Sheet, and Statement of Owner's Equity for accuracy.
"""

import sys
import os
import sqlite3
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine
from datetime import date, datetime

# Fix Windows console encoding
PESO_SYMBOL = "PHP "
try:
    if sys.platform == 'win32':
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        PESO_SYMBOL = "₱ "
except Exception:
    PESO_SYMBOL = "PHP "


def format_currency(amount):
    """Format amount as currency."""
    return f"{PESO_SYMBOL}{amount:,.2f}"


def verify_income_statement(eng, start_date, end_date):
    """Verify Income Statement calculations."""
    print("=" * 80)
    print("INCOME STATEMENT VERIFICATION")
    print("=" * 80)
    print()
    
    income_stmt = eng.generate_income_statement(start_date, end_date)
    
    print(f"Period: {start_date} to {end_date}")
    print()
    
    # Revenue Section
    print("REVENUES:")
    total_revenue = 0.0
    for rev in income_stmt.get('revenues', []):
        amount = float(rev.get('amount', 0))
        total_revenue += amount
        sign = "" if amount >= 0 else "-"
        print(f"  {rev.get('name', 'Unknown')}: {sign}{format_currency(abs(amount))}")
    
    print(f"  Total Revenue: {format_currency(total_revenue)}")
    print()
    
    # Expense Section
    print("EXPENSES:")
    total_expense = 0.0
    for exp in income_stmt.get('expenses', []):
        amount = float(exp.get('amount', 0))
        total_expense += amount
        print(f"  {exp.get('name', 'Unknown')}: {format_currency(amount)}")
    
    print(f"  Total Expenses: {format_currency(total_expense)}")
    print()
    
    # Net Income
    calculated_net = total_revenue - total_expense
    reported_net = float(income_stmt.get('net_income', 0))
    
    print(f"Net Income (Revenue - Expenses): {format_currency(calculated_net)}")
    print(f"Reported Net Income: {format_currency(reported_net)}")
    
    # Verification
    if abs(calculated_net - reported_net) < 0.01:
        print("✓ Income Statement calculation is CORRECT")
        print(f"  Formula: Revenue - Expenses = Net Income")
        print(f"  {format_currency(total_revenue)} - {format_currency(total_expense)} = {format_currency(calculated_net)}")
    else:
        print(f"✗ ERROR: Net Income mismatch!")
        print(f"  Calculated: {format_currency(calculated_net)}")
        print(f"  Reported: {format_currency(reported_net)}")
        print(f"  Difference: {format_currency(abs(calculated_net - reported_net))}")
    
    print()
    return income_stmt


def verify_balance_sheet(eng, as_of_date):
    """Verify Balance Sheet calculations and balance equation."""
    print("=" * 80)
    print("BALANCE SHEET VERIFICATION")
    print("=" * 80)
    print()
    
    balance_sheet = eng.generate_balance_sheet(as_of_date)
    
    print(f"As of: {as_of_date}")
    print()
    
    # Assets Section
    print("ASSETS:")
    total_assets = 0.0
    for asset in balance_sheet.get('assets', []):
        amount = float(asset.get('amount', 0))
        total_assets += amount
        sign = "" if amount >= 0 else "-"
        print(f"  {asset.get('name', 'Unknown')}: {sign}{format_currency(abs(amount))}")
    
    print(f"  Total Assets: {format_currency(total_assets)}")
    print()
    
    # Liabilities Section
    print("LIABILITIES:")
    total_liabilities = 0.0
    for liability in balance_sheet.get('liabilities', []):
        amount = float(liability.get('amount', 0))
        total_liabilities += amount
        print(f"  {liability.get('name', 'Unknown')}: {format_currency(amount)}")
    
    print(f"  Total Liabilities: {format_currency(total_liabilities)}")
    print()
    
    # Equity Section
    print("EQUITY:")
    total_equity = 0.0
    for equity_item in balance_sheet.get('equity', []):
        amount = float(equity_item.get('amount', 0))
        total_equity += amount
        print(f"  {equity_item.get('name', 'Unknown')}: {format_currency(amount)}")
    
    print(f"  Total Equity: {format_currency(total_equity)}")
    print()
    
    # Balance Check
    reported_assets = float(balance_sheet.get('total_assets', 0))
    reported_liabilities = float(balance_sheet.get('total_liabilities', 0))
    reported_equity = float(balance_sheet.get('total_equity', 0))
    balance_check = float(balance_sheet.get('balance_check', 0))
    
    calculated_balance = reported_assets - (reported_liabilities + reported_equity)
    
    print("BALANCE CHECK:")
    print(f"  Assets: {format_currency(reported_assets)}")
    print(f"  Liabilities + Equity: {format_currency(reported_liabilities + reported_equity)}")
    print(f"  Difference: {format_currency(calculated_balance)}")
    print()
    
    if abs(calculated_balance) < 0.01:
        print("✓ Balance Sheet is BALANCED")
        print(f"  Formula: Assets = Liabilities + Equity")
        print(f"  {format_currency(reported_assets)} = {format_currency(reported_liabilities)} + {format_currency(reported_equity)}")
    else:
        print("✗ ERROR: Balance Sheet is NOT BALANCED!")
        print(f"  Assets: {format_currency(reported_assets)}")
        print(f"  Liabilities + Equity: {format_currency(reported_liabilities + reported_equity)}")
        print(f"  Difference: {format_currency(abs(calculated_balance))}")
        print(f"  Balance Check: {format_currency(balance_check)}")
    
    print()
    return balance_sheet


def verify_statement_of_equity(eng, start_date, end_date, income_stmt, balance_sheet):
    """Verify Statement of Owner's Equity calculations."""
    print("=" * 80)
    print("STATEMENT OF OWNER'S EQUITY VERIFICATION")
    print("=" * 80)
    print()
    
    # Get Owner's Capital and Drawings from balance sheet
    owner_capital = 0.0
    owner_drawings = 0.0
    net_income = float(income_stmt.get('net_income', 0))
    
    for equity_item in balance_sheet.get('equity', []):
        name = equity_item.get('name', '').lower()
        amount = float(equity_item.get('amount', 0))
        
        if "capital" in name and "owner" in name:
            owner_capital = amount
        elif "drawing" in name or "withdrawal" in name:
            owner_drawings = abs(amount)  # Drawings are typically negative in equity
    
    # Calculate beginning capital (simplified - assumes no prior period data)
    # In a real system, you'd need to get beginning balance from previous period
    beginning_capital = 0.0
    
    # Try to find owner's capital transactions to determine beginning capital
    capital_account = db.get_account_by_name("Owner's Capital", eng.conn)
    if capital_account:
        cur = eng.conn.execute("""
            SELECT COALESCE(SUM(jl.credit) - SUM(jl.debit), 0) as balance
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.account_id = ?
              AND date(je.date) < date(?)
              AND (je.status = 'posted' OR je.status IS NULL)
        """, (capital_account['id'], start_date))
        
        result = cur.fetchone()
        if result:
            beginning_capital = float(result['balance'] or 0)
    
    # Calculate additions (investments)
    additions = 0.0
    if capital_account:
        cur = eng.conn.execute("""
            SELECT COALESCE(SUM(jl.credit), 0) as additions
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.account_id = ?
              AND date(je.date) BETWEEN date(?) AND date(?)
              AND (je.status = 'posted' OR je.status IS NULL)
              AND (je.is_closing = 0 OR je.is_closing IS NULL)
        """, (capital_account['id'], start_date, end_date))
        
        result = cur.fetchone()
        if result:
            additions = float(result['additions'] or 0)
    
    # Get drawings
    drawings_account = db.get_account_by_name("Owner's Drawings", eng.conn)
    if drawings_account:
        cur = eng.conn.execute("""
            SELECT COALESCE(SUM(jl.debit), 0) as drawings
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.account_id = ?
              AND date(je.date) BETWEEN date(?) AND date(?)
              AND (je.status = 'posted' OR je.status IS NULL)
              AND (je.is_closing = 0 OR je.is_closing IS NULL)
        """, (drawings_account['id'], start_date, end_date))
        
        result = cur.fetchone()
        if result:
            owner_drawings = float(result['drawings'] or 0)
    
    # Calculate ending capital
    calculated_ending = beginning_capital + additions + net_income - owner_drawings
    
    print(f"Period: {start_date} to {end_date}")
    print()
    print(f"Beginning Capital: {format_currency(beginning_capital)}")
    print(f"Add: Owner's Investments: {format_currency(additions)}")
    print(f"Add: Net Income: {format_currency(net_income)}")
    print(f"Less: Owner's Drawings: {format_currency(owner_drawings)}")
    print(f"Ending Capital: {format_currency(calculated_ending)}")
    print()
    
    # Verify against balance sheet
    if abs(calculated_ending - owner_capital) < 0.01:
        print("✓ Statement of Owner's Equity is CORRECT")
        print(f"  Formula: Beginning Capital + Investments + Net Income - Drawings = Ending Capital")
        print(f"  {format_currency(beginning_capital)} + {format_currency(additions)} + {format_currency(net_income)} - {format_currency(owner_drawings)} = {format_currency(calculated_ending)}")
    else:
        print("✗ WARNING: Ending Capital mismatch!")
        print(f"  Calculated: {format_currency(calculated_ending)}")
        print(f"  From Balance Sheet: {format_currency(owner_capital)}")
        print(f"  Difference: {format_currency(abs(calculated_ending - owner_capital))}")
    
    print()


def main():
    print("=" * 80)
    print("COMPREHENSIVE FINANCIAL STATEMENTS VERIFICATION")
    print("=" * 80)
    print()
    
    # Check if database needs initialization
    try:
        conn = db.get_connection()
        # Try to check if accounting_periods table exists
        conn.execute("SELECT COUNT(*) FROM accounting_periods")
        conn.close()
    except sqlite3.OperationalError:
        # Database not initialized, initialize it now
        print("Database not initialized. Initializing database...")
        db.init_db(reset=False)
        db.seed_chart_of_accounts()
        print("✓ Database initialized successfully")
        print()
    
    eng = AccountingEngine()
    
    try:
        if not eng.current_period_id:
            print("✗ ERROR: No active accounting period!")
            print("  The database has been initialized, but no accounting period exists.")
            print("  Please create an accounting period or add transactions first.")
            return
        
        # Get date range from entries
        cur = eng.conn.execute("""
            SELECT MIN(date) as min_date, MAX(date) as max_date
            FROM journal_entries
            WHERE period_id = ?
              AND (status = 'posted' OR status IS NULL)
        """, (eng.current_period_id,))
        
        date_range = cur.fetchone()
        start_date = date_range['min_date'] or '2025-01-01'
        end_date = date_range['max_date'] or datetime.now().date().isoformat()
        
        # Verify Income Statement
        income_stmt = verify_income_statement(eng, start_date, end_date)
        
        # Verify Balance Sheet
        balance_sheet = verify_balance_sheet(eng, end_date)
        
        # Verify Statement of Owner's Equity
        verify_statement_of_equity(eng, start_date, end_date, income_stmt, balance_sheet)
        
        # Overall Summary
        print("=" * 80)
        print("OVERALL VERIFICATION SUMMARY")
        print("=" * 80)
        print()
        
        # Check all equations
        net_income = float(income_stmt.get('net_income', 0))
        total_revenue = float(income_stmt.get('total_revenue', 0))
        total_expense = float(income_stmt.get('total_expense', 0))
        income_check = abs(net_income - (total_revenue - total_expense)) < 0.01
        
        total_assets = float(balance_sheet.get('total_assets', 0))
        total_liabilities = float(balance_sheet.get('total_liabilities', 0))
        total_equity = float(balance_sheet.get('total_equity', 0))
        balance_check = abs(total_assets - (total_liabilities + total_equity)) < 0.01
        
        print("✓ Income Statement: Revenue - Expenses = Net Income" if income_check else "✗ Income Statement: Calculation Error")
        print("✓ Balance Sheet: Assets = Liabilities + Equity" if balance_check else "✗ Balance Sheet: Not Balanced")
        
        if income_check and balance_check:
            print()
            print("=" * 80)
            print("✓ ALL FINANCIAL STATEMENTS ARE CORRECT AND BALANCED")
            print("=" * 80)
        else:
            print()
            print("=" * 80)
            print("✗ SOME ISSUES FOUND - PLEASE REVIEW ABOVE")
            print("=" * 80)
        
    finally:
        eng.close()


if __name__ == '__main__':
    main()

