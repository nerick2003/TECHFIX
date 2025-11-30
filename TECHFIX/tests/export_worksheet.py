from datetime import date
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pathlib import Path
from openpyxl import Workbook
from techfix import db
from techfix.accounting import AccountingEngine, JournalLine

def _sum_side(conn, period_id, side, is_adjusting=None):
    where = "a.is_active=1 AND je.period_id = ?"
    params = [period_id]
    if is_adjusting is not None:
        where += " AND je.is_adjusting = ?"
        params.append(1 if is_adjusting else 0)
    balance = "(COALESCE(SUM(jl.debit),0) - COALESCE(SUM(jl.credit),0))"
    sql = f"""
        SELECT a.code, a.name, a.type,
               ROUND(CASE WHEN {balance} > 0 THEN {balance} ELSE 0 END,2) AS net_debit,
               ROUND(CASE WHEN {balance} < 0 THEN -({balance}) ELSE 0 END,2) AS net_credit
        FROM accounts a
        LEFT JOIN journal_lines jl ON jl.account_id = a.id
        LEFT JOIN journal_entries je ON je.id = jl.entry_id
        WHERE {where}
        GROUP BY a.id, a.code, a.name, a.type
        ORDER BY a.code
    """
    cur = conn.execute(sql, params)
    return cur.fetchall()

def build_worksheet():
    db.init_db(reset=True)
    eng = AccountingEngine()
    db.seed_chart_of_accounts(eng.conn)

    get = lambda name: db.get_account_by_name(name, eng.conn)['id']
    y = date.today().year
    cash = get('Cash')
    cap = get("Owner's Capital")
    supplies = get('Supplies')
    equip = get('Equipment')
    ap = get('Accounts Payable')
    ar = get('Accounts Receivable')
    rev = get('Service Revenue')
    util = get('Utilities Expense')
    util_pay = get('Utilities Payable')
    draw = get("Owner's Drawings")
    sup_exp = get('Supplies Expense')
    dep_exp = get('Depreciation Expense')
    acc_dep = get('Accumulated Depreciation - Equipment')

    def post(d, desc, lines):
        eng.record_entry(d, desc, [JournalLine(*ln) for ln in lines], status='posted')

    post(f"{y}-01-01", 'Owner investment', [(cash, 100000.0, 0.0), (cap, 0.0, 100000.0)])
    post(f"{y}-01-03", 'Bought supplies (cash)', [(supplies, 5000.0, 0.0), (cash, 0.0, 5000.0)])
    post(f"{y}-01-05", 'Purchased equipment on account', [(equip, 40000.0, 0.0), (ap, 0.0, 40000.0)])
    post(f"{y}-01-10", 'Service revenue (cash)', [(cash, 15000.0, 0.0), (rev, 0.0, 15000.0)])
    post(f"{y}-01-12", 'Service revenue (billed)', [(ar, 20000.0, 0.0), (rev, 0.0, 20000.0)])
    post(f"{y}-01-15", 'Paid utilities', [(util, 3000.0, 0.0), (cash, 0.0, 3000.0)])
    post(f"{y}-01-20", 'Received collection from AR', [(cash, 10000.0, 0.0), (ar, 0.0, 10000.0)])
    post(f"{y}-01-25", 'Paid accounts payable', [(ap, 5000.0, 0.0), (cash, 0.0, 5000.0)])
    post(f"{y}-01-30", 'Owner withdrawal', [(draw, 4000.0, 0.0), (cash, 0.0, 4000.0)])

    eng.record_entry(
        f"{y}-01-31",
        'Adjust supplies used',
        [JournalLine(account_id=sup_exp, debit=3000.0), JournalLine(account_id=supplies, credit=3000.0)],
        is_adjusting=True,
        status='posted',
    )
    eng.record_entry(
        f"{y}-01-31",
        'Record depreciation',
        [JournalLine(account_id=dep_exp, debit=2000.0), JournalLine(account_id=acc_dep, credit=2000.0)],
        is_adjusting=True,
        status='posted',
    )
    eng.record_entry(
        f"{y}-01-31",
        'Accrue utilities',
        [JournalLine(account_id=util, debit=1000.0), JournalLine(account_id=util_pay, credit=1000.0)],
        is_adjusting=True,
        status='posted',
    )

    unadj = _sum_side(eng.conn, eng.current_period_id, 'both', is_adjusting=False)
    adjs = _sum_side(eng.conn, eng.current_period_id, 'both', is_adjusting=True)
    adj_tb = db.compute_trial_balance(period_id=eng.current_period_id, conn=eng.conn)

    un_by_code = {r['code']: r for r in unadj}
    adj_by_code = {r['code']: r for r in adjs}
    adjtb_by_code = {r['code']: r for r in adj_tb}

    wb = Workbook()
    ws = wb.active
    ws.title = 'Worksheet'
    ws.append(['Account No.', 'Account Title', 'Unadjusted Trial Balance Dr', 'Unadjusted Trial Balance Cr', 'Adjustments Dr', 'Adjustments Cr', 'Adjusted Trial Balance Dr', 'Adjusted Trial Balance Cr', 'Statement of Financial Performance Dr', 'Statement of Financial Performance Cr', 'Statement of Financial Position Dr', 'Statement of Financial Position Cr'])

    codes = sorted(set(list(un_by_code.keys()) + list(adj_by_code.keys()) + list(adjtb_by_code.keys())))
    total = {'un_dr':0.0,'un_cr':0.0,'aj_dr':0.0,'aj_cr':0.0,'ad_dr':0.0,'ad_cr':0.0,'is_dr':0.0,'is_cr':0.0,'sfp_dr':0.0,'sfp_cr':0.0}
    for code in codes:
        row_u = un_by_code.get(code)
        row_a = adj_by_code.get(code)
        row_t = adjtb_by_code.get(code)
        name = (row_t or row_u or row_a)['name']
        typ = (row_t or row_u or row_a)['type']
        un_dr = float(row_u['net_debit']) if row_u else 0.0
        un_cr = float(row_u['net_credit']) if row_u else 0.0
        aj_dr = float(row_a['net_debit']) if row_a else 0.0
        aj_cr = float(row_a['net_credit']) if row_a else 0.0
        ad_dr = float(row_t['net_debit']) if row_t else 0.0
        ad_cr = float(row_t['net_credit']) if row_t else 0.0
        is_dr = ad_dr if typ.lower() in ('expense','revenue') and ad_dr>0 else 0.0
        is_cr = ad_cr if typ.lower() in ('expense','revenue') and ad_cr>0 else 0.0
        sfp_dr = ad_dr if typ.lower() not in ('expense','revenue') and ad_dr>0 else 0.0
        sfp_cr = ad_cr if typ.lower() not in ('expense','revenue') and ad_cr>0 else 0.0
        ws.append([code, name, un_dr, un_cr, aj_dr, aj_cr, ad_dr, ad_cr, is_dr, is_cr, sfp_dr, sfp_cr])
        total['un_dr'] += un_dr; total['un_cr'] += un_cr
        total['aj_dr'] += aj_dr; total['aj_cr'] += aj_cr
        total['ad_dr'] += ad_dr; total['ad_cr'] += ad_cr
        total['is_dr'] += is_dr; total['is_cr'] += is_cr
        total['sfp_dr'] += sfp_dr; total['sfp_cr'] += sfp_cr

    ws.append(['TOTAL','', total['un_dr'], total['un_cr'], total['aj_dr'], total['aj_cr'], total['ad_dr'], total['ad_cr'], total['is_dr'], total['is_cr'], total['sfp_dr'], total['sfp_cr']])
    net_income = round(total['is_cr'] - total['is_dr'], 2)
    if net_income != 0:
        ws.append(['PROFIT/LOSS','', '', '', '', '', '', '', 0.0 if net_income>0 else abs(net_income), net_income if net_income>0 else 0.0, '', ''])
        ws.append(['TOTAL','', total['un_dr'], total['un_cr'], total['aj_dr'], total['aj_cr'], total['ad_dr'], total['ad_cr'], total['is_dr'] + (0.0 if net_income>0 else abs(net_income)), total['is_cr'] + (net_income if net_income>0 else 0.0), total['sfp_dr'], total['sfp_cr']])

    out_path = Path(os.path.dirname(__file__)) / '..' / 'worksheet.xlsx'
    wb.save(str(out_path.resolve()))
    print(str(out_path.resolve()))

if __name__ == '__main__':
    build_worksheet()
