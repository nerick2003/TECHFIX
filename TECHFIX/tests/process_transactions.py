"""
Process transactions from DATA_SUMMARY.txt and generate financial statements
"""
import os
import sys
import re
from datetime import datetime

# Add TECHFIX to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'TECHFIX')))

from techfix import db
from techfix.accounting import AccountingEngine, JournalLine


def parse_transactions_from_summary(file_path):
    """Parse transactions from DATA_SUMMARY.txt"""
    transactions = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the transaction details section
    lines = content.split('\n')
    in_transactions = False
    
    current_txn = None
    
    for i, line in enumerate(lines):
        # Check if we're in the transaction section
        if 'TRANSACTION DETAILS' in line:
            in_transactions = True
            continue
        
        if in_transactions and 'FINANCIAL SUMMARY' in line:
            break
        
        if not in_transactions:
            continue
        
        # Parse transaction number and date
        match = re.match(r'\s*(\d+)\.\s+Date:\s+(\d{4}-\d{2}-\d{2})', line)
        if match:
            if current_txn:
                transactions.append(current_txn)
            current_txn = {
                'num': int(match.group(1)),
                'date': match.group(2),
                'type': None,
                'description': None,
                'debit_account': None,
                'credit_account': None,
                'amount': None,
                'reference': None
            }
            continue
        
        if current_txn:
            # Parse type
            if 'Type:' in line:
                current_txn['type'] = line.split('Type:')[1].strip()
            
            # Parse description
            if 'Description:' in line:
                current_txn['description'] = line.split('Description:')[1].strip()
            
            # Parse debit
            if 'Debit:' in line:
                parts = line.split('₱')
                if len(parts) == 2:
                    account = parts[0].replace('Debit:', '').strip()
                    amount_str = parts[1].strip().replace(',', '')
                    current_txn['debit_account'] = account
                    current_txn['amount'] = float(amount_str)
            
            # Parse credit
            if 'Credit:' in line:
                parts = line.split('₱')
                if len(parts) == 2:
                    account = parts[0].replace('Credit:', '').strip()
                    current_txn['credit_account'] = account
            
            # Parse reference
            if 'Reference:' in line:
                current_txn['reference'] = line.split('Reference:')[1].strip()
    
    # Add last transaction
    if current_txn:
        transactions.append(current_txn)
    
    return transactions


def map_account_name(name):
    """Map account names from DATA_SUMMARY to database account names"""
    mapping = {
        'Service Income': 'Service Revenue',  # Generator uses "Service Income", DB has "Service Revenue"
        'Salaries & Wages': 'Salaries & Wages',
        'Rent Expense': 'Rent Expense',
        'Utilities Expense': 'Utilities Expense',
        'Supplies Expense': 'Supplies Expense',
        'Cash': 'Cash',
        'Accounts Receivable': 'Accounts Receivable',
        'Accounts Payable': 'Accounts Payable',
        "Owner's Capital": "Owner's Capital",
        "Owner's Drawings": "Owner's Drawings",
        'Office Equipment': 'Office Equipment',
        'Depreciation Expense': 'Depreciation Expense',
        'Accumulated Depreciation': 'Accumulated Depreciation',
        'Utilities Payable': 'Utilities Payable',
        'SSS, PhilHealth, and Pag-Ibig Payable': 'SSS, PhilHealth, and Pag-Ibig Payable',
        'Accrued Percentage Tax Payable': 'Accrued Percentage Tax Payable',
        'Percentage Tax Expense': 'Percentage Tax Expense',
    }
    return mapping.get(name, name)


def main():
    print("=" * 80)
    print("PROCESSING TRANSACTIONS FROM DATA_SUMMARY.txt")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    db.init_db(reset=True)
    eng = AccountingEngine()
    db.seed_chart_of_accounts(eng.conn)
    
    # Create December 2025 period
    print("2. Creating accounting period for December 2025...")
    period_id = eng.create_period(
        name="2025-12",
        start_date="2025-12-01",
        end_date="2025-12-31",
        make_current=True
    )
    print(f"   Created period: 2025-12 (ID: {period_id})")
    
    # Get account IDs helper
    def get_account_id(name):
        mapped_name = map_account_name(name)
        account = db.get_account_by_name(mapped_name, eng.conn)
        if account is None:
            raise ValueError(f"Account '{name}' (mapped to '{mapped_name}') not found in database")
        return account['id']
    
    # Parse transactions
    print("\n3. Parsing transactions from DATA_SUMMARY.txt...")
    # DATA_SUMMARY.txt is now in the generators folder
    summary_path = os.path.join(os.path.dirname(__file__), 'generators', 'DATA_SUMMARY.txt')
    transactions = parse_transactions_from_summary(summary_path)
    print(f"   Found {len(transactions)} transactions")
    
    # Post transactions
    print("\n4. Posting transactions...")
    for txn in transactions:
        try:
            debit_id = get_account_id(txn['debit_account'])
            credit_id = get_account_id(txn['credit_account'])
            
            # Determine if this is an adjusting entry
            # Adjusting entries have type "Adjust" or description contains "Adjusting entry"
            is_adjusting = (
                txn.get('type', '').strip().lower() == 'adjust' or
                'adjusting entry' in txn.get('description', '').lower()
            )
            
            eng.record_entry(
                date=txn['date'],
                description=txn['description'],
                lines=[
                    JournalLine(account_id=debit_id, debit=txn['amount']),
                    JournalLine(account_id=credit_id, credit=txn['amount'])
                ],
                source_type=txn['type'],
                external_ref=txn['reference'],
                is_adjusting=is_adjusting,  # CRITICAL: Mark adjusting entries correctly
                status='posted'
            )
            entry_type = " [ADJUSTING]" if is_adjusting else ""
            print(f"   [OK] {txn['num']:2d}. {txn['date']} - {txn['description'][:50]}{entry_type}")
        except Exception as e:
            print(f"   [ERROR] {txn['num']:2d}. ERROR: {str(e)}")
    
    # Generate Trial Balance
    print("\n5. Generating Trial Balance...")
    print("-" * 80)
    tb_rows = db.compute_trial_balance(
        period_id=eng.current_period_id,
        conn=eng.conn
    )
    
    print(f"{'Code':<6} {'Account Name':<40} {'Debit':>15} {'Credit':>15}")
    print("-" * 80)
    total_debit = 0
    total_credit = 0
    for r in tb_rows:
        if r['net_debit'] > 0.01 or r['net_credit'] > 0.01:
            print(f"{r['code']:<6} {r['name']:<40} {r['net_debit']:>15,.2f} {r['net_credit']:>15,.2f}")
            total_debit += r['net_debit']
            total_credit += r['net_credit']
    print("-" * 80)
    print(f"{'TOTAL':<47} {total_debit:>15,.2f} {total_credit:>15,.2f}")
    print(f"Balance Check: {'[BALANCED]' if abs(total_debit - total_credit) < 0.01 else '[UNBALANCED]'}")
    
    # Generate Income Statement
    print("\n6. Generating Income Statement...")
    print("=" * 80)
    income_stmt = eng.generate_income_statement("2025-12-01", "2025-12-31")
    
    print(f"\nINCOME STATEMENT")
    print(f"For the period ended December 31, 2025")
    print("-" * 80)
    
    print("\nREVENUES:")
    for rev in income_stmt['revenues']:
        print(f"  {rev['name']:<40} {rev['amount']:>15,.2f}")
    
    print(f"\n  {'Total Revenue':<40} {income_stmt['total_revenue']:>15,.2f}")
    
    print("\nEXPENSES:")
    for exp in income_stmt['expenses']:
        print(f"  {exp['name']:<40} {exp['amount']:>15,.2f}")
    
    print(f"\n  {'Total Expenses':<40} {income_stmt['total_expense']:>15,.2f}")
    print("-" * 80)
    print(f"  {'NET INCOME':<40} {income_stmt['net_income']:>15,.2f}")
    
    # Generate Balance Sheet
    print("\n7. Generating Balance Sheet...")
    print("=" * 80)
    balance_sheet = eng.generate_balance_sheet("2025-12-31")
    
    print(f"\nBALANCE SHEET")
    print(f"As of December 31, 2025")
    print("-" * 80)
    
    print("\nASSETS:")
    for asset in balance_sheet['assets']:
        print(f"  {asset['name']:<40} {abs(asset['amount']):>15,.2f}")
    print(f"\n  {'Total Assets':<40} {abs(balance_sheet['total_assets']):>15,.2f}")
    
    print("\nLIABILITIES:")
    for liability in balance_sheet['liabilities']:
        # Liabilities show as positive (credit balance)
        print(f"  {liability['name']:<40} {abs(liability['amount']):>15,.2f}")
    total_liabilities = abs(balance_sheet['total_liabilities'])
    print(f"\n  {'Total Liabilities':<40} {total_liabilities:>15,.2f}")
    
    print("\nEQUITY:")
    capital_balance = 0
    drawings_balance = 0
    for equity_item in balance_sheet['equity']:
        if "Capital" in equity_item['name']:
            capital_balance = abs(equity_item['amount'])
            print(f"  {equity_item['name']:<40} {capital_balance:>15,.2f}")
        elif "Drawings" in equity_item['name']:
            drawings_balance = abs(equity_item['amount'])
            print(f"  {equity_item['name']:<40} {drawings_balance:>15,.2f}")
    
    # Add net income to equity (before closing entries)
    print(f"  {'Net Income (not yet closed)':<40} {income_stmt['net_income']:>15,.2f}")
    
    # Calculate total equity including net income
    total_equity = capital_balance - drawings_balance + income_stmt['net_income']
    print(f"\n  {'Total Equity':<40} {total_equity:>15,.2f}")
    print("-" * 80)
    total_liab_equity = total_liabilities + total_equity
    print(f"  {'Total Liabilities & Equity':<40} {total_liab_equity:>15,.2f}")
    total_assets = abs(balance_sheet['total_assets'])
    balance_check = total_assets - total_liab_equity
    print(f"Balance Check: {'[BALANCED]' if abs(balance_check) < 0.01 else f'[UNBALANCED] (diff: {balance_check:,.2f})'}")
    
    # Generate Cash Flow Statement
    print("\n8. Generating Cash Flow Statement...")
    print("=" * 80)
    cash_flow = eng.generate_cash_flow("2025-12-01", "2025-12-31")
    
    print(f"\nSTATEMENT OF CASH FLOWS")
    print(f"For the period December 1-31, 2025")
    print("-" * 80)
    
    print("\nOPERATING ACTIVITIES:")
    for item in cash_flow['sections']['Operating']:
        date_str = item['date']
        print(f"  {date_str} {item['amount']:>15,.2f}")
    print(f"\n  {'Total Operating Activities':<40} {cash_flow['totals']['Operating']:>15,.2f}")
    
    print("\nINVESTING ACTIVITIES:")
    for item in cash_flow['sections']['Investing']:
        date_str = item['date']
        print(f"  {date_str} {item['amount']:>15,.2f}")
    print(f"\n  {'Total Investing Activities':<40} {cash_flow['totals']['Investing']:>15,.2f}")
    
    print("\nFINANCING ACTIVITIES:")
    for item in cash_flow['sections']['Financing']:
        date_str = item['date']
        print(f"  {date_str} {item['amount']:>15,.2f}")
    print(f"\n  {'Total Financing Activities':<40} {cash_flow['totals']['Financing']:>15,.2f}")
    print("-" * 80)
    print(f"  {'NET CHANGE IN CASH':<40} {cash_flow['net_change_in_cash']:>15,.2f}")
    
    # Statement of Owner's Equity
    print("\n9. Generating Statement of Owner's Equity...")
    print("=" * 80)
    
    # Get beginning capital (should be 0 for new business)
    # Get owner's capital balance
    capital_account = db.get_account_by_name("Owner's Capital", eng.conn)
    capital_id = capital_account['id']
    
    # Get net income from income statement
    net_income = income_stmt['net_income']
    
    # Get drawings
    drawings_account = db.get_account_by_name("Owner's Drawings", eng.conn)
    drawings_id = drawings_account['id']
    
    # Calculate drawings balance
    cur = eng.conn.execute(
        """
        SELECT COALESCE(SUM(debit) - SUM(credit), 0) AS balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        WHERE jl.account_id = ? AND je.period_id = ?
        """,
        (drawings_id, eng.current_period_id)
    )
    drawings_balance = float(cur.fetchone()['balance'])
    
    # Get owner's capital balance (credit balance, so negative in the calculation)
    capital_balance = abs(balance_sheet['total_equity']) - abs(drawings_balance)
    
    # Calculate beginning capital (should be 0 for new business)
    beginning_capital = 0.0
    
    # Calculate owner's investment
    owner_investment = capital_balance - net_income + drawings_balance
    
    # Calculate ending capital
    ending_capital = beginning_capital + owner_investment + net_income - drawings_balance
    
    print(f"\nSTATEMENT OF OWNER'S EQUITY")
    print(f"For the period ended December 31, 2025")
    print("-" * 80)
    print(f"  {'Beginning Capital, December 1, 2025':<40} {beginning_capital:>15,.2f}")
    print(f"  {'Add: Owner Investment':<40} {owner_investment:>15,.2f}")
    print(f"  {'Add: Net Income':<40} {net_income:>15,.2f}")
    print(f"  {'Less: Owner Drawings':<40} {drawings_balance:>15,.2f}")
    print("-" * 80)
    print(f"  {'Ending Capital, December 31, 2025':<40} {ending_capital:>15,.2f}")
    
    print("\n" + "=" * 80)
    print("[SUCCESS] FINANCIAL STATEMENTS GENERATION COMPLETE!")
    print("=" * 80)


if __name__ == '__main__':
    main()

