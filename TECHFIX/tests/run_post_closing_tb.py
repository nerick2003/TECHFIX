from datetime import date
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from techfix import db
from techfix.accounting import AccountingEngine

def main():
    eng = AccountingEngine()
    y = date.today().year
    eng.make_closing_entries(f"{y}-01-31")
    rows = db.compute_trial_balance(period_id=eng.current_period_id, include_temporary=False, conn=eng.conn)
    print('Post-Closing Trial Balance (January)')
    for r in rows:
        print(f"{r['code']:>3} {r['name']:<30} Dr {r['net_debit']:>10.2f}  Cr {r['net_credit']:>10.2f}")
    total_debit = sum(r['net_debit'] for r in rows)
    total_credit = sum(r['net_credit'] for r in rows)
    print(f"Totals: Dr {total_debit:.2f}  Cr {total_credit:.2f}")

if __name__ == '__main__':
    main()
