# Accounting Entry Processing Fixes

## Issues Identified and Fixed

### 1. **Missing `is_adjusting` Flag (CRITICAL)**
**Problem:** Adjusting entries were not being marked with `is_adjusting=True` when posted to the database. This caused:
- Adjusting entries to be treated as regular transactions
- Financial statements to potentially exclude or misclassify adjusting entries
- Trial balance calculations to be incorrect
- Closing entries to not properly handle adjusting entries

**Fix:** Added logic to detect adjusting entries and set the `is_adjusting` flag:
- Detects adjusting entries by checking if `type == "Adjust"` or if description contains "Adjusting entry"
- Sets `is_adjusting=True` when calling `eng.record_entry()` for adjusting entries
- Added visual indicator in output to show which entries are adjusting entries

**Location:** `process_transactions.py` lines 147-167

### 2. **Incomplete Account Name Mapping**
**Problem:** The account name mapping was missing several accounts that appear in transactions:
- Depreciation Expense
- Accumulated Depreciation
- Utilities Payable
- SSS, PhilHealth, and Pag-Ibig Payable
- Accrued Percentage Tax Payable
- Percentage Tax Expense

**Fix:** Added all missing accounts to the `map_account_name()` function mapping dictionary.

**Location:** `process_transactions.py` lines 94-109

## Changes Made

### File: `process_transactions.py`

1. **Enhanced Account Mapping** (lines 94-109):
   - Added mappings for all adjusting entry accounts
   - Added mappings for all liability accounts used in transactions
   - Added mappings for all expense accounts used in transactions

2. **Added Adjusting Entry Detection** (lines 147-167):
   - Detects adjusting entries by type ("Adjust") or description ("Adjusting entry")
   - Sets `is_adjusting=True` flag when posting adjusting entries
   - Added visual indicator in console output

## How to Verify the Fixes

1. **Run the transaction processor:**
   ```bash
   python process_transactions.py
   ```

2. **Check the output:**
   - Adjusting entries should show `[ADJUSTING]` tag in the console
   - All transactions should post without errors
   - Trial balance should balance

3. **Verify in the database:**
   - Check that adjusting entries have `is_adjusting = 1` in the `journal_entries` table
   - Verify all account names are correctly mapped
   - Confirm financial statements include adjusting entries

## Expected Behavior After Fixes

1. **Adjusting Entries:**
   - Transactions 17-20 (dated 2025-12-31) should be marked as adjusting entries
   - These entries should appear in adjusted trial balance
   - These entries should be included in financial statement calculations

2. **Account Mapping:**
   - All account names from DATA_SUMMARY.txt should map correctly to database account names
   - "Service Income" should map to "Service Revenue"
   - All other accounts should map correctly

3. **Financial Statements:**
   - Income Statement should include all expenses including adjusting entry expenses
   - Balance Sheet should show all liabilities including accrued liabilities
   - Trial Balance should balance (debits = credits)

## Notes

- The generator (`generate_business_transactions.py`) uses "Service Income" but the database uses "Service Revenue"
- The mapping function handles this conversion automatically
- Adjusting entries are critical for accurate financial reporting and must be marked correctly

