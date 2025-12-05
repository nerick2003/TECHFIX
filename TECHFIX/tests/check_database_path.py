"""
Check which database file the GUI is actually using
"""
import sys
import os
from pathlib import Path

# Add the techfix module to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from techfix import db
from techfix.accounting import AccountingEngine

print("=" * 80)
print("CHECKING DATABASE PATH")
print("=" * 80)
print()

# Check environment variable
techfix_data_dir = os.environ.get("TECHFIX_DATA_DIR")
print(f"TECHFIX_DATA_DIR environment variable: {techfix_data_dir or '(not set)'}")
print()

# Check what db.py is using
print(f"db.DB_DIR: {db.DB_DIR}")
print(f"db.DB_PATH: {db.DB_PATH}")
print(f"Database file exists: {db.DB_PATH.exists()}")
print(f"Database file absolute path: {db.DB_PATH.resolve()}")
print()

# Check current working directory
print(f"Current working directory: {os.getcwd()}")
print()

# Now check what AccountingEngine uses
eng = AccountingEngine()
print("AccountingEngine connection info:")
print(f"  Connection object: {eng.conn}")
print(f"  Database path (from connection): {eng.conn.execute('PRAGMA database_list').fetchall()}")
print()

# Get database file from connection
db_list = eng.conn.execute("PRAGMA database_list").fetchall()
if db_list:
    print("Database files in use:")
    for db_info in db_list:
        print(f"  Name: {db_info['name']}, File: {db_info['file']}")
print()

# Check what data is in this database
print("=" * 80)
print("DATA IN THIS DATABASE")
print("=" * 80)
print()

# Check periods
periods = eng.conn.execute("SELECT id, name, start_date, end_date, is_current FROM accounting_periods").fetchall()
print(f"Accounting Periods: {len(periods)}")
for p in periods:
    current = " (CURRENT)" if p['is_current'] else ""
    print(f"  Period {p['id']}: {p['name']} ({p['start_date']} to {p['end_date']}){current}")
print()

# Check entries
entries = eng.conn.execute("""
    SELECT COUNT(*) as cnt, 
           MIN(date) as min_date, 
           MAX(date) as max_date,
           SUM(CASE WHEN status = 'posted' THEN 1 ELSE 0 END) as posted,
           SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft
    FROM journal_entries
""").fetchone()

print(f"Journal Entries:")
print(f"  Total: {entries['cnt']}")
print(f"  Posted: {entries['posted']}")
print(f"  Draft: {entries['draft']}")
print(f"  Date range: {entries['min_date']} to {entries['max_date']}")
print()

# Check current period balance sheet
if eng.current_period:
    period_id = eng.current_period_id
    print(f"Current Period: {eng.current_period['name']} (ID: {period_id})")
    print()
    
    # Get max date
    max_date = eng.conn.execute("""
        SELECT MAX(date) as max_date FROM journal_entries 
        WHERE period_id = ? AND status = 'posted'
    """, (period_id,)).fetchone()
    as_of_date = max_date['max_date'] if max_date and max_date['max_date'] else '2025-12-31'
    
    print(f"Balance Sheet as of: {as_of_date}")
    balance_sheet = eng.generate_balance_sheet(as_of_date)
    
    assets = balance_sheet.get('assets', [])
    liabilities = balance_sheet.get('liabilities', [])
    equity = balance_sheet.get('equity', [])
    
    total_assets = sum(a.get('amount', 0) for a in assets)
    total_liabilities = sum(l.get('amount', 0) for l in liabilities)
    total_equity = sum(e.get('amount', 0) for e in equity)
    
    print()
    print("ASSETS:")
    for asset in assets:
        if abs(asset.get('amount', 0)) > 0.005:
            print(f"  {asset.get('name'):<40} ₱ {asset.get('amount', 0):>12,.2f}")
    print(f"  {'Total Assets':<40} ₱ {total_assets:>12,.2f}")
    print()
    
    print("LIABILITIES:")
    for liab in liabilities:
        if abs(liab.get('amount', 0)) > 0.005:
            print(f"  {liab.get('name'):<40} ₱ {liab.get('amount', 0):>12,.2f}")
    if not liabilities or total_liabilities == 0:
        print("  (none)")
    print(f"  {'Total Liabilities':<40} ₱ {total_liabilities:>12,.2f}")
    print()
    
    print("EQUITY:")
    for eq in equity:
        if abs(eq.get('amount', 0)) > 0.005:
            print(f"  {eq.get('name'):<40} ₱ {eq.get('amount', 0):>12,.2f}")
    print(f"  {'Total Equity':<40} ₱ {total_equity:>12,.2f}")
    print()
    
    balance_check = total_assets - (total_liabilities + total_equity)
    print(f"Balance Check: ₱ {abs(balance_check):,.2f} {'✅' if abs(balance_check) < 0.05 else '❌'}")
    print()
    print(f"These values should match what you see in the GUI!")
    print(f"If they don't match, the GUI might be using a different database file.")

eng.close()
print()
print("=" * 80)

