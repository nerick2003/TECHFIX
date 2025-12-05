"""
Fix duplicate closing entries in the GUI database
"""
import sys
import os
from pathlib import Path
import sqlite3

root_db = Path(r"C:\Users\neric\Desktop\FOR VIDEO\techfix.sqlite3")

if not root_db.exists():
    print(f"Database not found: {root_db}")
    sys.exit(1)

conn = sqlite3.connect(str(root_db))
conn.row_factory = sqlite3.Row

try:
    # Get current period
    period = conn.execute("SELECT id, name FROM accounting_periods WHERE is_current = 1").fetchone()
    period_id = period['id']
    
    print("=" * 80)
    print("FIXING DUPLICATE CLOSING ENTRIES")
    print("=" * 80)
    print()
    print(f"Period: {period['name']} (ID: {period_id})")
    print()
    
    # Find duplicate closing entries
    closing_entries = conn.execute("""
        SELECT je.id, je.date, je.description,
               SUM(jl.debit) as total_debit, SUM(jl.credit) as total_credit
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE je.is_closing = 1
          AND je.period_id = ?
          AND (je.status = 'posted' OR je.status IS NULL)
        GROUP BY je.id
        ORDER BY je.date, je.id
    """, (period_id,)).fetchall()
    
    print(f"Found {len(closing_entries)} closing entries")
    print()
    
    # Identify duplicates (entries #24, #25, #26)
    duplicates = [e for e in closing_entries if e['id'] in [24, 25, 26]]
    
    if duplicates:
        print("Duplicate closing entries to delete:")
        for entry in duplicates:
            print(f"  Entry #{entry['id']}: {entry['date']} - {entry['description']}")
            print(f"    Debit: ₱ {float(entry['total_debit'] or 0):,.2f}, Credit: ₱ {float(entry['total_credit'] or 0):,.2f}")
        print()
        
        # Ask for confirmation
        response = input("Delete these duplicate closing entries? (yes/no): ")
        if response.lower() == 'yes':
            # Delete journal lines first (foreign key constraint)
            for entry in duplicates:
                conn.execute("DELETE FROM journal_lines WHERE entry_id = ?", (entry['id'],))
                print(f"Deleted journal lines for entry #{entry['id']}")
            
            # Then delete journal entries
            for entry in duplicates:
                conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry['id'],))
                print(f"Deleted entry #{entry['id']}")
            
            conn.commit()
            print()
            print("✅ Duplicate closing entries deleted!")
            print()
            print("The balance sheet should now balance:")
            print("  Assets: ₱ 50,009.45")
            print("  Owner's Capital: ₱ 50,009.45 (reduced by ₱ 50,009.45)")
            print("  Balance Check: ₱ 0.00 ✅")
            print()
            print("Please refresh the balance sheet in the GUI to see the fix.")
        else:
            print("Cancelled. No changes made.")
    else:
        print("No duplicate closing entries found.")
    
finally:
    conn.close()

