#!/usr/bin/env python3
"""Test what the backend returns vs what GUI should display."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from techfix import db, accounting

root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")
conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    engine = accounting.AccountingEngine(conn=conn)
    engine.set_active_period(1)
    
    balance_sheet = engine.generate_balance_sheet('2025-12-31')
    
    print("BACKEND RETURNS:")
    print(f"  total_assets: {balance_sheet.get('total_assets', 0):,.2f}")
    print(f"  total_liabilities: {balance_sheet.get('total_liabilities', 0):,.2f}")
    print(f"  total_equity: {balance_sheet.get('total_equity', 0):,.2f}")
    print(f"  balance_check: {balance_sheet.get('balance_check', 0):,.2f}")
    print()
    
    print("ASSETS LIST:")
    assets = balance_sheet.get('assets', [])
    for asset in assets:
        print(f"  {asset.get('name')}: {asset.get('amount', 0):,.2f}")
    print()
    
    print("CALCULATED FROM ASSETS LIST:")
    calculated_assets = sum(asset.get('amount', 0.0) for asset in assets)
    print(f"  Sum of assets: {calculated_assets:,.2f}")
    print()
    
    print("LIABILITIES LIST:")
    liabilities = balance_sheet.get('liabilities', [])
    for liab in liabilities:
        print(f"  {liab.get('name')}: {liab.get('amount', 0):,.2f}")
    print()
    
    print("EQUITY LIST:")
    equity = balance_sheet.get('equity', [])
    for eq in equity:
        print(f"  {eq.get('name')}: {eq.get('amount', 0):,.2f}")
    print()
    
    calculated_liabilities = sum(liab.get('amount', 0.0) for liab in liabilities)
    calculated_equity = sum(eq.get('amount', 0.0) for eq in equity)
    
    print("COMPARISON:")
    print(f"  Backend total_assets: {balance_sheet.get('total_assets', 0):,.2f}")
    print(f"  Calculated from list: {calculated_assets:,.2f}")
    print(f"  Difference: {abs(balance_sheet.get('total_assets', 0) - calculated_assets):,.2f}")
    print()
    
    if abs(balance_sheet.get('total_assets', 0) - calculated_assets) > 0.01:
        print("⚠ MISMATCH DETECTED!")
        print("   The backend total_assets doesn't match the sum of assets list.")
        print("   The GUI fix should correct this by using the calculated sum.")
    else:
        print("✓ Backend totals match calculated sums.")
    
finally:
    conn.close()

