# Troubleshooting Balance Sheet Issues After Scanning

## Common Issues When Scanning Transactions

### 1. **Account Name Mismatches**

The most common issue is account names not matching exactly. The system uses exact name matching (case-sensitive).

**Problem**: Account names in scanned data don't match account names in your Chart of Accounts.

**Solution**: Check these account names match EXACTLY:

| Expected Name | Common Variations (WRONG) |
|--------------|-------------------------|
| `Owner's Capital` | `Owners Capital`, `Owner Capital`, `Capital` |
| `Owner's Drawings` | `Owners Drawings`, `Owner Drawings`, `Drawings` |
| `Salaries & Wages` | `Salaries and Wages`, `Salaries`, `Wages` |
| `SSS, PhilHealth, and Pag-Ibig Payable` | `SSS Payable`, `PhilHealth Payable`, etc. |
| `Accrued Percentage Tax Payable` | `Percentage Tax Payable`, `Accrued Tax` |
| `Service Income` | `Service Revenue`, `Revenue` |

**How to Fix**:
1. Go to Chart of Accounts
2. Verify exact account names
3. If account names don't match, either:
   - Update the account name in Chart of Accounts to match scanned data, OR
   - Manually correct the account name when entering scanned transactions

### 2. **Missing Transactions**

Some transactions might not have been scanned or entered.

**How to Check**:
1. Run the verification script: `python TECHFIX/tests/verify_transactions.py`
2. Check the "MISSING TRANSACTIONS" section
3. Manually enter any missing transactions

### 3. **Adjusting Entries Not Marked Correctly**

Adjusting entries (ADJ-10016 through ADJ-10019) must be marked as "Adjusting Entry".

**How to Fix**:
1. Find each adjusting entry in the Journal
2. Verify it has `is_adjusting = True` or checkbox is checked
3. If not, you may need to:
   - Delete and re-enter with "Adjusting Entry" checkbox checked, OR
   - Use a correcting entry

### 4. **Amount Errors**

Amounts might be entered incorrectly during scanning.

**How to Check**:
1. Compare each transaction amount with DATA_SUMMARY.txt
2. Verify debits equal credits for each entry
3. Check for decimal point errors (e.g., 4643.51 vs 464.351)

### 5. **Date Issues**

All transactions should be dated in December 2025 (2025-12-01 through 2025-12-31).

**How to Fix**:
1. Verify all transaction dates are correct
2. Adjusting entries should be dated 2025-12-31

## Step-by-Step Fix Process

### Step 1: Run Verification Script

```bash
cd TECHFIX
python TECHFIX/tests/verify_transactions.py
```

This will show you:
- Missing transactions
- Account balance mismatches
- Trial balance status
- Financial statement differences

### Step 2: Check Account Names

1. Open TechFix
2. Go to Chart of Accounts
3. Compare with these expected account names:

**Assets:**
- Cash
- Accounts Receivable
- Office Equipment
- Accumulated Depreciation (Contra Asset)

**Liabilities:**
- Accounts Payable
- Utilities Payable
- SSS, PhilHealth, and Pag-Ibig Payable
- Accrued Percentage Tax Payable

**Equity:**
- Owner's Capital
- Owner's Drawings

**Revenue:**
- Service Income

**Expenses:**
- Rent Expense
- Utilities Expense
- Salaries & Wages
- Supplies Expense
- Depreciation Expense
- Percentage Tax Expense

### Step 3: Verify Each Transaction

For each transaction in DATA_SUMMARY.txt:

1. Find it in your Journal (by document reference)
2. Verify:
   - Date matches
   - Debit account matches exactly
   - Credit account matches exactly
   - Debit amount matches
   - Credit amount matches
   - Document reference matches
   - For adjusting entries: "Adjusting Entry" checkbox is checked

### Step 4: Check Trial Balance

1. Generate Trial Balance
2. Verify:
   - Total Debits = Total Credits
   - Each account balance matches expected values from DATA_SUMMARY.txt

### Step 5: Check Financial Statements

1. Generate Income Statement (2025-12-01 to 2025-12-31)
   - Should show: Revenue ₱ 19,307.59, Expenses ₱ 14,013.86, Net Income ₱ 5,293.73

2. Generate Balance Sheet (as of 2025-12-31)
   - Should show: Assets ₱ 15,692.28, Liabilities ₱ 1,230.28, Equity ₱ 14,462.00
   - Balance check should be 0.00

## Quick Fixes for Common Problems

### Problem: Account not found when scanning

**Solution**: 
- Check exact spelling and punctuation
- Account names are case-sensitive
- Use "Find Account" feature to search for similar names
- Manually select the correct account from dropdown

### Problem: Trial balance doesn't balance

**Solution**:
1. Check each journal entry has equal debits and credits
2. Look for entries with missing debit or credit
3. Check for rounding errors
4. Verify no entries were partially entered

### Problem: Balance sheet doesn't match expected

**Solution**:
1. Ensure all 20 transactions are entered
2. Verify adjusting entries are marked correctly
3. Check account classifications (Asset, Liability, Equity, Revenue, Expense)
4. Run verification script to identify specific mismatches

## Expected Values Reference

### Trial Balance Totals
- Total Debits: ₱ 54,662.18
- Total Credits: ₱ 54,662.18

### Key Account Balances
- Cash: ₱ 10,062.27 (debit)
- Accounts Receivable: ₱ 3,187.49 (debit)
- Office Equipment: ₱ 3,083.52 (debit)
- Accumulated Depreciation: ₱ 641.00 (credit)
- Accounts Payable: ₱ 508.54 (credit)
- Owner's Capital: ₱ 10,711.72 (credit)
- Owner's Drawings: ₱ 1,543.45 (debit)
- Service Income: ₱ 19,307.59 (credit)
- Total Expenses: ₱ 14,013.86 (debit)

### Financial Statements
- **Income Statement**: Net Income = ₱ 5,293.73
- **Balance Sheet**: Assets = Liabilities + Equity = ₱ 15,692.28

## Still Having Issues?

1. **Export your Journal** to CSV/Excel
2. **Compare line by line** with DATA_SUMMARY.txt
3. **Check for**:
   - Duplicate entries
   - Missing entries
   - Wrong account names
   - Wrong amounts
   - Missing adjusting entry flags

4. **Re-enter problematic transactions manually** if needed

