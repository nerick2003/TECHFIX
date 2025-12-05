# Balance Sheet Troubleshooting Guide

## The Problem

Your balance sheet doesn't balance after completing the accounting cycle. This guide will help you identify and fix the issue.

## Quick Diagnostic

Run the diagnostic tool to identify the exact problem:

```bash
python TECHFIX/TECHFIX/tests/diagnose_balance_sheet.py
```

This will check:
1. ✅ Trial balance balance
2. ✅ Post-closing trial balance balance
3. ✅ Account balance calculations
4. ✅ Balance sheet calculation
5. ✅ Closing entries status
6. ✅ Reversing entries issues

## Common Causes & Fixes

### 1. **Reversing Entries Affecting Closing Entries** ⚠️ FIXED

**Problem**: Reversing entries were being included in closing entry calculations, causing incorrect closing amounts.

**Fix Applied**: Closing entries now exclude reversing entries from calculations.

**What to do**: 
- If you've already made closing entries, you may need to:
  1. Delete the closing entries
  2. Re-run closing entries (they will now calculate correctly)
  3. Regenerate balance sheet

### 2. **Trial Balance Doesn't Balance**

**Symptom**: Diagnostic shows "Trial Balance is NOT BALANCED"

**Causes**:
- Journal entries with unequal debits and credits
- Missing journal entries
- Incorrect amounts entered

**Fix**:
1. Go to Journal tab
2. Check each entry - debits must equal credits
3. Look for entries with missing debit or credit lines
4. Fix or delete unbalanced entries

### 3. **Closing Entries Not Posted**

**Symptom**: Diagnostic shows "Closing entries step is not marked as completed"

**Fix**:
1. Go to Closing tab
2. Click "Make Closing Entries"
3. Verify closing entries were created
4. Check that step 8 is marked as "completed"

### 4. **Revenue/Expense Accounts Not Closed**

**Symptom**: Diagnostic shows "Revenue/expense accounts found in permanent accounts"

**Causes**:
- Closing entries weren't posted
- Closing entries didn't close all revenue/expense accounts
- Reversing entries affected accounts after closing

**Fix**:
1. Check if closing entries were posted
2. Verify all revenue/expense accounts have zero balances after closing
3. If not, re-run closing entries

### 5. **Unbalanced Reversing Entries**

**Symptom**: Diagnostic shows "Unbalanced reversing entries found"

**Fix**:
1. Check the reversing entries in Journal
2. Each reversing entry must have equal debits and credits
3. Delete and re-create unbalanced reversing entries

### 6. **Owner's Capital Too High**

**Symptom**: Owner's Capital shows an unusually high amount (e.g., 41,301.50 instead of 10,711.72)

**Causes**:
- Unclosed revenue/expense accounts being included in equity
- Closing entries including reversing entry amounts
- Temporary accounts not properly closed

**Fix**:
1. Run diagnostic tool to identify the issue
2. Check if revenue/expense accounts have balances
3. Re-run closing entries if needed
4. Verify balance sheet only includes permanent accounts

## Step-by-Step Fix Process

### Step 1: Run Diagnostic

```bash
python TECHFIX/TECHFIX/tests/diagnose_balance_sheet.py
```

Review the output and identify which step has issues.

### Step 2: Fix Trial Balance (if needed)

If trial balance doesn't balance:
1. Go to Journal tab
2. Find entries with unequal debits/credits
3. Fix or delete them
4. Re-check trial balance

### Step 3: Verify Closing Entries

1. Go to Closing tab
2. Check if closing entries exist
3. If not, click "Make Closing Entries"
4. Verify step 8 is marked "completed"

### Step 4: Check Post-Closing Trial Balance

1. Go to Post-Closing Trial Balance tab
2. Verify it balances
3. Check that revenue/expense accounts show zero balances

### Step 5: Regenerate Balance Sheet

1. Go to Financial Statements tab
2. Click "Generate" or refresh
3. Check if balance sheet now balances

## Prevention Tips

1. **Always verify trial balance balances** before making closing entries
2. **Process reversing entries AFTER closing entries** (in the next period)
3. **Check closing entries** were created correctly
4. **Verify post-closing trial balance** before generating balance sheet
5. **Use the diagnostic tool** regularly to catch issues early

## Understanding the Accounting Equation

The balance sheet must follow this equation:

**Assets = Liabilities + Equity**

If this doesn't balance, something is wrong. Common issues:

- **Assets too high**: Missing liabilities or equity entries
- **Equity too high**: Unclosed revenue/expense accounts included
- **Both sides too high**: Double-counting or incorrect calculations

## What Was Fixed

✅ **Closing entries now exclude reversing entries** - This was causing closing entries to include reversed amounts, inflating Owner's Capital

✅ **Status filtering added** - Closing entries now only include posted entries

✅ **Balance sheet excludes temporary accounts** - After closing entries are completed, revenue/expense accounts are excluded

## Still Having Issues?

If the diagnostic tool doesn't identify the issue:

1. **Export your journal** to CSV/Excel
2. **Manually verify** each entry has equal debits and credits
3. **Check account balances** match expected values
4. **Review closing entries** to ensure they closed all revenue/expense accounts
5. **Verify reversing entries** are balanced and dated correctly

## Expected Values Reference

After completing the full cycle with DATA_SUMMARY.txt transactions:

- **Trial Balance**: Debits = Credits = ₱ 54,662.18
- **Post-Closing TB**: Debits = Credits (only permanent accounts)
- **Balance Sheet**:
  - Assets: ₱ 15,692.28
  - Liabilities: ₱ 1,230.28
  - Equity: ₱ 14,462.00
  - Balance Check: 0.00

If your values don't match, use the diagnostic tool to find where the difference occurs.

