#!/usr/bin/env python3
"""Debug the balance sheet calculation to find the discrepancy."""

import sqlite3
import sys
from pathlib import Path

# Add the techfix module to path
sys.path.insert(0, str(Path(__file__).parent))

from techfix import db, accounting

root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")
conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    # Get current period
    period = conn.execute("SELECT id FROM accounting_periods WHERE is_current = 1").fetchone()
    period_id = period['id'] if period else None
    
    if not period_id:
        print("No current period")
        sys.exit(1)
    
    # Get max date
    max_date = conn.execute("""
        SELECT MAX(date) as max_date FROM journal_entries 
        WHERE period_id = ? AND status = 'posted'
    """, (period_id,)).fetchone()
    as_of_date = max_date['max_date'] if max_date and max_date['max_date'] else '2025-12-31'
    
    print(f"Period ID: {period_id}")
    print(f"As of date: {as_of_date}")
    print()
    
    # Generate balance sheet using the engine
    engine = accounting.AccountingEngine(conn=conn)
    engine.set_active_period(period_id)
    balance_sheet = engine.generate_balance_sheet(as_of_date)
    
    print("BALANCE SHEET FROM ENGINE:")
    print(f"Total Assets: {balance_sheet.get('total_assets', 0):,.2f}")
    print(f"Total Liabilities: {balance_sheet.get('total_liabilities', 0):,.2f}")
    print(f"Total Equity: {balance_sheet.get('total_equity', 0):,.2f}")
    print(f"Balance Check: {balance_sheet.get('balance_check', 0):,.2f}")
    print()
    
    print("ASSETS BREAKDOWN:")
    for asset in balance_sheet.get('assets', []):
        print(f"  {asset.get('name')}: {asset.get('amount', 0):,.2f}")
    print()
    
    print("LIABILITIES BREAKDOWN:")
    for liab in balance_sheet.get('liabilities', []):
        print(f"  {liab.get('name')}: {liab.get('amount', 0):,.2f}")
    print()
    
    print("EQUITY BREAKDOWN:")
    for eq in balance_sheet.get('equity', []):
        print(f"  {eq.get('name')}: {eq.get('amount', 0):,.2f}")
    print()
    
    # Check what the GUI might be showing
    print("GUI SHOULD SHOW:")
    print(f"Total Assets: {balance_sheet.get('total_assets', 0):,.2f}")
    print(f"Total Liabilities: {balance_sheet.get('total_liabilities', 0):,.2f}")
    print(f"Total Equity: {balance_sheet.get('total_equity', 0):,.2f}")
    total_liab_equity = balance_sheet.get('total_liabilities', 0) + balance_sheet.get('total_equity', 0)
    print(f"Total Liabilities + Equity: {total_liab_equity:,.2f}")
    print()
    
    # Compare with what user reported
    print("USER REPORTED (from GUI):")
    print("Total Assets: 44,086.39")
    print("Total Liabilities: 0.00")
    print("Total Equity: 50,009.45")
    print("Difference: 5,923.06")
    print()
    
    expected_assets = balance_sheet.get('total_assets', 0)
    reported_assets = 44086.39
    difference = expected_assets - reported_assets
    print(f"DIFFERENCE IN ASSETS: {difference:,.2f}")
    print(f"Expected: {expected_assets:,.2f}")
    print(f"Reported: {reported_assets:,.2f}")
    
finally:
    conn.close()

