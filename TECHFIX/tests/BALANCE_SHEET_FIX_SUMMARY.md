# Balance Sheet Imbalance Fix - Summary

## Problem
The balance sheet was not balancing when transactions were entered using scan, scan image, and browse functions.

## Root Causes Identified

1. **Draft Transactions Not Included**: Transactions saved as "draft" are NOT included in the balance sheet calculation. Only transactions with status "posted" are included.

2. **User Confusion**: Users might be clicking "Save Draft" instead of "Record & Post" when entering transactions via scan/browse.

3. **Missing Diagnostics**: No clear feedback when the balance sheet doesn't balance, making it hard to identify the issue.

## Solutions Implemented

### 1. Diagnostic Function (`_diagnose_balance_sheet_imbalance`)
Added a comprehensive diagnostic function that checks for:
- Draft transactions that aren't included in balance sheet
- Unbalanced journal entries (debits ≠ credits)
- Entries with only one line (missing debit or credit)
- Entries with zero amounts
- Transactions not assigned to current period

### 2. Enhanced Balance Sheet Display
When the balance sheet doesn't balance, it now shows:
- A clear warning message
- The difference amount
- A list of possible issues with specific counts

### 3. User Reminders
Added reminders when using scan/browse functions:
- When a document is attached via "Browse", shows: "Document attached - Remember to click 'Record & Post' (not 'Save Draft') to include in balance sheet"
- When data is scanned successfully, shows: "Scan successful - Remember to click 'Record & Post' (not 'Save Draft') to include in balance sheet"

## How to Fix Your Current Data

### Step 1: Check for Draft Transactions
1. Go to the Journal tab
2. Look for entries with status "draft"
3. For each draft entry:
   - Review the transaction details
   - Click "Post" or "Record & Post" to change status to "posted"

### Step 2: Verify All Transactions Are Posted
1. Go to Financial Statements tab
2. Generate the Balance Sheet
3. If it shows a warning, check the "Possible Issues" section
4. Address each issue listed

### Step 3: Best Practices Going Forward
1. **Always use "Record & Post"** instead of "Save Draft" when entering transactions
2. **Verify the transaction is posted** by checking the Journal tab
3. **Check the balance sheet regularly** to catch issues early
4. **Review the diagnostic messages** if the balance sheet doesn't balance

## Technical Details

### Balance Sheet Calculation
The balance sheet only includes transactions with:
- `status = 'posted'` (drafts are excluded)
- `period_id = current_period_id` (assigned to current period)
- `is_permanent = 1` (only permanent accounts for balance sheet)

### Transaction Status
- **Draft**: Saved but not included in financial statements
- **Posted**: Included in all financial statements and calculations

## Files Modified
- `techfix/gui.py`:
  - Added `_diagnose_balance_sheet_imbalance()` method
  - Enhanced `_generate_balance_sheet()` to show diagnostics
  - Added reminders in `_apply_scanned_data()` and `_browse_source_document()`

## Testing
After making changes:
1. Enter a transaction using scan/browse
2. Verify the reminder message appears
3. Click "Record & Post" (not "Save Draft")
4. Generate the balance sheet
5. Verify it balances (or check diagnostics if it doesn't)

