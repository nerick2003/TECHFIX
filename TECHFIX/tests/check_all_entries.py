"""
Check all entries in database to see what's actually there
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from techfix import db
from techfix.accounting import AccountingEngine
from datetime import date

PESO_SYMBOL = "₱ "

def format_currency(amount):
    return f"{PESO_SYMBOL}{amount:,.2f}"

def main():
    eng = AccountingEngine()
    conn = eng.conn
    
    print("=" * 80)
    print("CHECKING ALL ENTRIES IN DATABASE")
    print("=" * 80)
    print()
    
    # Check all periods
    periods = conn.execute("SELECT id, name, start_date, end_date FROM accounting_periods ORDER BY id").fetchall()
    print(f"Total Periods: {len(periods)}")
    for p in periods:
        print(f"  Period {p['id']}: {p['name']} ({p['start_date']} to {p['end_date']})")
    print()
    
    # Check entries by period
    for period in periods:
        period_id = period['id']
        cur = conn.execute("""
            SELECT COUNT(*) as cnt, 
                   MIN(date) as min_date, 
                   MAX(date) as max_date,
                   SUM(CASE WHEN status = 'posted' THEN 1 ELSE 0 END) as posted,
                   SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft
            FROM journal_entries 
            WHERE period_id = ?
        """, (period_id,))
        result = cur.fetchone()
        print(f"Period {period_id} ({period['name']}):")
        print(f"  Total entries: {result['cnt']}")
        print(f"  Posted: {result['posted']}, Draft: {result['draft']}")
        print(f"  Date range: {result['min_date']} to {result['max_date']}")
        
        # Get account balances for this period
        rows = db.compute_trial_balance(
            period_id=period_id,
            include_temporary=False,
            conn=conn
        )
        
        # Calculate totals
        total_assets = 0.0
        total_liabilities = 0.0
        total_equity = 0.0
        
        for r in rows:
            acc_type = (r["type"] or "").lower()
            net_debit = float(r["net_debit"] or 0.0)
            net_credit = float(r["net_credit"] or 0.0)
            balance = net_debit - net_credit
            
            if acc_type == "asset":
                total_assets += balance
            elif acc_type == "contra asset":
                total_assets -= balance  # Contra assets reduce assets
            elif acc_type == "liability":
                total_liabilities += abs(balance)  # Liabilities are credit balance
            elif acc_type == "equity":
                total_equity += abs(balance)  # Equity is credit balance
        
        print(f"  Balance Sheet Totals:")
        print(f"    Assets: {format_currency(total_assets)}")
        print(f"    Liabilities: {format_currency(total_liabilities)}")
        print(f"    Equity: {format_currency(total_equity)}")
        balance_check = total_assets - (total_liabilities + total_equity)
        print(f"    Balance Check: {format_currency(abs(balance_check))} {'✅' if abs(balance_check) < 0.05 else '❌'}")
        print()
    
    # Check entries with specific dates that match user's GUI
    print("=" * 80)
    print("CHECKING ENTRIES AS OF 2025-12-06")
    print("=" * 80)
    print()
    
    # Get all entries up to 2025-12-06 across all periods
    cur = conn.execute("""
        SELECT je.id, je.date, je.description, je.period_id, je.status,
               SUM(jl.debit) as total_debit, SUM(jl.credit) as total_credit
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE date(je.date) <= date('2025-12-06')
          AND (je.status = 'posted' OR je.status IS NULL)
        GROUP BY je.id
        ORDER BY je.date, je.id
    """)
    entries = cur.fetchall()
    
    print(f"Total entries up to 2025-12-06: {len(entries)}")
    print()
    print("Recent entries (last 10):")
    for entry in entries[-10:]:
        print(f"  Entry #{entry['id']}: {entry['date']} - {entry['description']}")
        print(f"    Period: {entry['period_id']}, Status: {entry['status']}")
        print(f"    Debit: {format_currency(float(entry['total_debit'] or 0))}, Credit: {format_currency(float(entry['total_credit'] or 0))}")
    print()
    
    # Calculate balance sheet as of 2025-12-06 across ALL periods
    rows_all = db.compute_trial_balance(
        up_to_date="2025-12-06",
        include_temporary=False,
        period_id=None,  # All periods
        conn=conn
    )
    
    print("Balance Sheet as of 2025-12-06 (ALL PERIODS):")
    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0
    
    assets_list = []
    liabilities_list = []
    equity_list = []
    
    for r in rows_all:
        acc_type = (r["type"] or "").lower()
        net_debit = float(r["net_debit"] or 0.0)
        net_credit = float(r["net_credit"] or 0.0)
        balance = net_debit - net_credit
        
        if acc_type == "asset":
            if abs(balance) > 0.005:
                assets_list.append((r['name'], balance))
                total_assets += balance
        elif acc_type == "contra asset":
            if abs(balance) > 0.005:
                assets_list.append((r['name'], -balance))  # Contra assets are negative
                total_assets -= balance
        elif acc_type == "liability":
            if abs(balance) > 0.005:
                liabilities_list.append((r['name'], abs(balance)))
                total_liabilities += abs(balance)
        elif acc_type == "equity":
            if abs(balance) > 0.005:
                equity_list.append((r['name'], abs(balance)))
                total_equity += abs(balance)
    
    print("ASSETS:")
    for name, amt in assets_list:
        print(f"  {name:<40} {format_currency(amt)}")
    print(f"  {'Total Assets':<40} {format_currency(total_assets)}")
    print()
    
    print("LIABILITIES:")
    if liabilities_list:
        for name, amt in liabilities_list:
            print(f"  {name:<40} {format_currency(amt)}")
    else:
        print("  (none)")
    print(f"  {'Total Liabilities':<40} {format_currency(total_liabilities)}")
    print()
    
    print("EQUITY:")
    for name, amt in equity_list:
        print(f"  {name:<40} {format_currency(amt)}")
    print(f"  {'Total Equity':<40} {format_currency(total_equity)}")
    print()
    
    balance_check = total_assets - (total_liabilities + total_equity)
    print(f"Balance Check: {format_currency(abs(balance_check))} {'✅' if abs(balance_check) < 0.05 else '❌'}")
    print()
    print(f"This should match what you see in the GUI:")
    print(f"  Assets: {format_currency(total_assets)}")
    print(f"  Equity: {format_currency(total_equity)}")

if __name__ == '__main__':
    main()

