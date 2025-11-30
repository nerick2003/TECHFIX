from datetime import date
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from techfix import db
from techfix.accounting import AccountingEngine, JournalLine

def main():
    db.init_db(reset=True)
    eng = AccountingEngine()
    db.seed_chart_of_accounts(eng.conn)

    get = lambda name: db.get_account_by_name(name, eng.conn)['id']
    cash = get('Cash')
    cap = get("Owner's Capital")
    supplies = get('Supplies')
    equip = get('Equipment')
    ap = get('Accounts Payable')
    ar = get('Accounts Receivable')
    rev = get('Service Revenue')
    util = get('Utilities Expense')
    draw = get("Owner's Drawings")

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
    total_debit = sum(r['net_debit'] for r in rows)
    total_credit = sum(r['net_credit'] for r in rows)
    rev_total = sum((r['net_credit'] - r['net_debit']) for r in rows if r['type'].lower() == 'revenue')
    exp_total = sum((r['net_debit'] - r['net_credit']) for r in rows if r['type'].lower() == 'expense')
    net_income = rev_total - exp_total

    print('Trial Balance (January)')
    for r in rows:
        print(f"{r['code']:>3} {r['name']:<30} Dr {r['net_debit']:>10.2f}  Cr {r['net_credit']:>10.2f}")
    print(f"Totals: Dr {total_debit:.2f}  Cr {total_credit:.2f}")
    print(f"Revenue: {rev_total:.2f}  Expense: {exp_total:.2f}  Net Income: {net_income:.2f}")

    # Show key balances
    key = {r['name']: (r['net_debit'], r['net_credit']) for r in rows}
    def bal(name):
        d, c = key.get(name, (0.0, 0.0))
        return round(d - c, 2)
    print('Balances')
    for nm in ['Cash','Supplies','Equipment','Accounts Receivable','Accounts Payable',"Owner's Capital","Owner's Drawings",'Service Revenue','Utilities Expense']:
        print(f"{nm}: {bal(nm):.2f}")

if __name__ == '__main__':
    main()
