from datetime import date
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from techfix import db
from techfix.accounting import AccountingEngine, JournalLine

def main():
    db.init_db(reset=True)
    eng = AccountingEngine()
    db.seed_chart_of_accounts(eng.conn)

    def get(name):
        account = db.get_account_by_name(name, eng.conn)
        if account is None:
            raise ValueError(f"Account '{name}' not found in database")
        return account['id']
    cash = get('Cash')
    cap = get("Owner's Capital")
    supplies = get('Supplies')
    equip = get('Office Equipment')
    ap = get('Accounts Payable')
    ar = get('Accounts Receivable')
    rev = get('Service Revenue')
    util = get('Utilities Expense')
    util_pay = get('Utilities Payable')
    draw = get("Owner's Drawings")
    sup_exp = get('Supplies Expense')
    dep_exp = get('Depreciation Expense')
    acc_dep = get('Accumulated Depreciation')

    def post(d, desc, lines):
        eng.record_entry(d, desc, [JournalLine(*ln) for ln in lines], status='posted')

    y = date.today().year
    # Transactions
    post(f"{y}-01-01", 'Owner investment', [(cash, 100000.0, 0.0), (cap, 0.0, 100000.0)])
    post(f"{y}-01-03", 'Bought supplies (cash)', [(supplies, 5000.0, 0.0), (cash, 0.0, 5000.0)])
    post(f"{y}-01-05", 'Purchased equipment on account', [(equip, 40000.0, 0.0), (ap, 0.0, 40000.0)])
    post(f"{y}-01-10", 'Service revenue (cash)', [(cash, 15000.0, 0.0), (rev, 0.0, 15000.0)])
    post(f"{y}-01-12", 'Service revenue (billed)', [(ar, 20000.0, 0.0), (rev, 0.0, 20000.0)])
    post(f"{y}-01-15", 'Paid utilities', [(util, 3000.0, 0.0), (cash, 0.0, 3000.0)])
    post(f"{y}-01-20", 'Received collection from AR', [(cash, 10000.0, 0.0), (ar, 0.0, 10000.0)])
    post(f"{y}-01-25", 'Paid accounts payable', [(ap, 5000.0, 0.0), (cash, 0.0, 5000.0)])
    post(f"{y}-01-30", 'Owner withdrawal', [(draw, 4000.0, 0.0), (cash, 0.0, 4000.0)])

    rows = db.compute_trial_balance(period_id=eng.current_period_id, conn=eng.conn)
    print('Unadjusted Trial Balance (January)')
    for r in rows:
        print(f"{r['code']:>3} {r['name']:<30} Dr {r['net_debit']:>10.2f}  Cr {r['net_credit']:>10.2f}")
    total_debit = sum(r['net_debit'] for r in rows)
    total_credit = sum(r['net_credit'] for r in rows)
    print(f"Totals: Dr {total_debit:.2f}  Cr {total_credit:.2f}")

    # Adjustments (Step 5)
    eng.record_entry(
        f"{y}-01-31",
        'Adjust supplies used',
        [
            JournalLine(account_id=sup_exp, debit=3000.0),
            JournalLine(account_id=supplies, credit=3000.0),
        ],
        is_adjusting=True,
        status='posted',
    )
    eng.record_entry(
        f"{y}-01-31",
        'Record depreciation',
        [
            JournalLine(account_id=dep_exp, debit=2000.0),
            JournalLine(account_id=acc_dep, credit=2000.0),
        ],
        is_adjusting=True,
        status='posted',
    )
    eng.record_entry(
        f"{y}-01-31",
        'Accrue utilities',
        [
            JournalLine(account_id=util, debit=1000.0),
            JournalLine(account_id=util_pay, credit=1000.0),
        ],
        is_adjusting=True,
        status='posted',
    )

    rows2 = db.compute_trial_balance(period_id=eng.current_period_id, conn=eng.conn)
    print('Adjusted Trial Balance (January)')
    for r in rows2:
        print(f"{r['code']:>3} {r['name']:<30} Dr {r['net_debit']:>10.2f}  Cr {r['net_credit']:>10.2f}")
    total_debit2 = sum(r['net_debit'] for r in rows2)
    total_credit2 = sum(r['net_credit'] for r in rows2)
    print(f"Totals: Dr {total_debit2:.2f}  Cr {total_credit2:.2f}")

    rev_total = sum((r['net_credit'] - r['net_debit']) for r in rows2 if r['type'].lower() == 'revenue')
    exp_total = sum((r['net_debit'] - r['net_credit']) for r in rows2 if r['type'].lower() == 'expense')
    net_income = rev_total - exp_total
    print('Income Statement')
    print(f"Service Revenue: {rev_total:.2f}")
    print(f"Supplies Expense: 3000.00")
    print(f"Depreciation Expense: 2000.00")
    print(f"Utilities Expense: 4000.00")
    print(f"Net Income: {net_income:.2f}")

    # Statement of Owner's Equity
    print("Owner's Equity")
    print(f"Beginning Capital: 0.00")
    print(f"Investment: 100000.00")
    print(f"Net Income: {net_income:.2f}")
    print(f"Drawings: 4000.00")
    ending_capital = 100000.00 + net_income - 4000.00
    print(f"Ending Capital: {ending_capital:.2f}")

if __name__ == '__main__':
    main()
