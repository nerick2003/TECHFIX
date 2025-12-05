"""Quick test to verify _balance_to_columns fix"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from techfix import db
from techfix.accounting import AccountingEngine

eng = AccountingEngine()
rows = db.compute_trial_balance(period_id=eng.current_period_id, include_temporary=True, conn=eng.conn)
print(f'Trial balance rows: {len(rows)}')

# Simulate the _balance_to_columns logic
def test_balance_to_columns(row):
    try:
        acc_type = (row['type'] if 'type' in row.keys() and row['type'] else '').lower()
        normal = (row['normal_side'] if 'normal_side' in row.keys() and row['normal_side'] else 'debit').lower()
        net_debit = float(row['net_debit'] if 'net_debit' in row.keys() and row['net_debit'] is not None else 0)
        net_credit = float(row['net_credit'] if 'net_credit' in row.keys() and row['net_credit'] is not None else 0)
        
        if acc_type == 'contra asset':
            if net_credit > 0:
                return (0.0, net_credit)
            elif net_debit > 0:
                return (net_debit, 0.0)
            else:
                return (0.0, 0.0)
        
        if normal == 'debit':
            bal = net_debit - net_credit
            if bal >= 0:
                return (bal, 0.0)
            else:
                return (0.0, abs(bal))
        else:
            bal = net_credit - net_debit
            if bal >= 0:
                return (0.0, bal)
            else:
                return (abs(bal), 0.0)
    except Exception as e:
        print(f"Error: {e}")
        return (0.0, 0.0)

active = []
for r in rows:
    d, c = test_balance_to_columns(r)
    if d != 0 or c != 0:
        active.append((r, d, c))

print(f'Active accounts: {len(active)}')
for r, d, c in active[:5]:
    print(f"  {r['code']} - {r['name']}: Dr {d:,.2f}, Cr {c:,.2f}")

eng.close()

