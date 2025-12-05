# GUI Showing Different Outputs - Troubleshooting Guide

## Problem
The GUI shows different balance sheet values than expected or different from command-line tools.

## Common Causes

### 1. **Different Database Files**
The application uses the database file based on the **current working directory** when you run it.

**How to Check:**
- Look at the top of the Balance Sheet in the GUI - it now shows the database path
- Compare it with the path shown by diagnostic tools

**Solution:**
- Always run the GUI from the same directory: `TECHFIX\TECHFIX\`
- Or set the `TECHFIX_DATA_DIR` environment variable to use a specific database location

### 2. **Stale Data / Not Refreshed**
The balance sheet might show old data if it hasn't been regenerated after making changes.

**Solution:**
1. Go to **Financial Statements** tab
2. Click **"Generate Financial Statements"** button
3. Or switch to a different tab and back to refresh

### 3. **Closing Entries Not Posted**
If closing entries haven't been posted, the balance sheet will include temporary accounts (revenues/expenses) which causes imbalance.

**Solution:**
1. Go to **Closing** tab
2. Click **"Make Closing Entries"**
3. Verify entries were created and posted
4. Regenerate balance sheet

### 4. **Different Period Selected**
The balance sheet shows data for the current period. If you're comparing with a different period, values will differ.

**Solution:**
- Check which period is active in the GUI
- Make sure you're comparing the same period

## Quick Diagnostic Steps

1. **Check Database Path:**
   - Look at Balance Sheet header - it shows the database path
   - Compare with: `python tests/diagnose_balance_sheet.py`

2. **Verify Closing Entries:**
   ```powershell
   python tests/diagnose_balance_sheet.py
   ```
   This will tell you if closing entries are missing

3. **Refresh Balance Sheet:**
   - Go to Financial Statements tab
   - Click "Generate Financial Statements"
   - Check the values again

4. **Compare Values:**
   - GUI Balance Sheet shows: Total Assets, Total Liabilities, Total Equity
   - Diagnostic tool shows the same values
   - They should match if using the same database

## Expected Behavior

After closing entries are posted:
- **Total Assets** = Sum of all asset account balances
- **Total Liabilities** = Sum of all liability account balances  
- **Total Equity** = Owner's Capital (includes net income and is reduced by drawings)
- **Balance Check** = Assets - (Liabilities + Equity) = 0.00

## If Still Having Issues

1. **Export the balance sheet** from GUI (Export button in Financial Statements tab)
2. **Run diagnostic tool** and compare outputs
3. **Check Help tab** in GUI - it shows database path and other diagnostic info
4. **Verify you're using the same database** - check the path shown in Balance Sheet header

## Database Location

The database file location is determined by:
- `TECHFIX_DATA_DIR` environment variable (if set)
- Otherwise: current working directory where you run the application

**Default location when running from `TECHFIX\TECHFIX\`:**
- `TECHFIX\TECHFIX\techfix.sqlite3`

**If running from parent directory:**
- `FOR VIDEO\techfix.sqlite3`

Make sure you're always running from the same directory or set `TECHFIX_DATA_DIR` to use a consistent location.

