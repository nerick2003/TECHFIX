# TechFix Accounting System - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Entering Transactions](#entering-transactions)
3. [Using Scan/Browse Features](#using-scanbrowse-features)
4. [Verifying Transactions](#verifying-transactions)
5. [Generating Financial Statements](#generating-financial-statements)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### 1. Launch the Application
- Navigate to the `TECHFIX\TECHFIX\` folder
- Run: `python main.py` or double-click the executable
- The application will automatically:
  - Create/connect to the database
  - Set up the chart of accounts
  - Create a default accounting period if none exists

### 2. Check Your Current Period
- Look at the top of the window for the current accounting period
- Make sure you're working in the correct period
- To change periods, go to **Settings** or **Periods** tab

---

## Entering Transactions

### Step-by-Step Process

#### **Step 1: Open Transactions Tab**
- Click on the **"Transactions"** tab in the main window

#### **Step 2: Fill in Transaction Details**

**Required Fields:**
- **Date**: Enter the transaction date (format: YYYY-MM-DD)
- **Description**: Brief description of the transaction
- **Source Type**: Select from dropdown (Bank, Invoice, Receipt, etc.)
- **Document Reference**: Reference number (e.g., INV-001, CHK-123)
- **External Reference**: Same as Document Reference (optional)

**Debit Side:**
- **Debit Account**: Select the account to debit (e.g., Cash, Accounts Receivable)
- **Debit Amount**: Enter the amount

**Credit Side:**
- **Credit Account**: Select the account to credit (e.g., Service Income, Accounts Payable)
- **Credit Amount**: Enter the amount (must equal debit amount)

**Important Rules:**
- ✅ Debit amount MUST equal Credit amount
- ✅ Both accounts must be selected
- ✅ Both amounts must be entered

#### **Step 3: Attach Source Document (Optional)**
- Click **"Browse..."** to select a document file
- Or use **"Scan"** to scan from camera
- Or use **"Scan Image"** to scan from an image file

#### **Step 4: Save the Transaction**

**⚠️ CRITICAL: Always use "Record & Post" NOT "Save Draft"**

- Click **"Record & Post"** button (or press `Ctrl+Enter`)
- This saves the transaction with status = "posted"
- Only posted transactions appear in financial statements

**❌ DO NOT use "Save Draft"** unless you're still working on the entry
- Draft transactions are NOT included in balance sheet
- Draft transactions are NOT included in financial statements
- You must post them later to include them

#### **Step 5: Verify the Entry**
- You should see a confirmation message: "Journal entry #X recorded"
- Check the **Journal** tab to see your entry
- Verify the entry appears with status "posted"

---

## Using Scan/Browse Features

### Method 1: Browse for Document

1. Click **"Browse..."** button in the Document section
2. Select your source document file (PDF, image, etc.)
3. The system will attempt to:
   - Extract date from filename or document
   - Extract amounts if available
   - Pre-fill account suggestions based on document type
4. **Review all fields** - the system may not fill everything correctly
5. **Complete any missing fields** manually
6. **Click "Record & Post"** (not "Save Draft")

### Method 2: Scan from Camera

1. Click **"Scan"** button
2. Allow camera access if prompted
3. Point camera at QR code or barcode on document
4. Wait for scan to complete
5. Review pre-filled data
6. **Complete any missing fields**
7. **Click "Record & Post"**

### Method 3: Scan from Image File

1. Click **"Scan Image"** button
2. Select an image file containing QR code or barcode
3. Wait for scan to complete
4. Review pre-filled data
5. **Complete any missing fields**
6. **Click "Record & Post"**

### ⚠️ Important Reminders

- The system will show a reminder: *"Remember to click 'Record & Post' (not 'Save Draft') to include in balance sheet"*
- **Always verify** the pre-filled data is correct
- **Always complete** debit and credit accounts and amounts
- **Always use "Record & Post"** to save transactions

---

## Verifying Transactions

### Check the Journal

1. Go to **"Journal"** tab
2. Review all entries
3. Verify:
   - All entries have status "posted" (not "draft")
   - Debits equal credits for each entry
   - Dates are correct
   - Accounts are correct

### Check for Draft Transactions

1. In the Journal tab, look for entries with status "draft"
2. For each draft entry:
   - Click on it to open
   - Review the details
   - Click **"Post"** to change status to "posted"
   - Or delete it if it's a mistake

### Check Trial Balance

1. Go to **"Trial Balance"** tab
2. The trial balance loads automatically, or click **"Refresh"** to update it
3. Optionally set a date in the "As of" field to see the trial balance as of a specific date
4. Verify:
   - Total Debits = Total Credits
   - All accounts show correct balances

---

## Generating Financial Statements

### Step 1: Ensure All Transactions Are Posted

- Check the Journal tab
- Make sure NO entries have status "draft"
- Post any draft entries before generating statements

### Step 2: Generate Financial Statements

1. Go to **"Financial Statements"** tab
2. Click **"Generate Financial Statements"** button
3. The system will generate:
   - Income Statement
   - Balance Sheet
   - Cash Flow Statement

### Step 3: Verify Balance Sheet

**The Balance Sheet should show:**
- ✅ Total Assets = Total Liabilities + Total Equity
- ✅ Balance Check = ₱0.00
- ✅ No warning messages

**If you see a warning:**
- Check the "Possible Issues" section below the balance sheet
- Address each issue listed
- Most common issues:
  - Draft transactions need to be posted
  - Unbalanced entries need to be fixed
  - Missing debit or credit lines

### Step 4: Review All Statements

- **Income Statement**: Shows revenues and expenses
- **Balance Sheet**: Shows assets, liabilities, and equity
- **Cash Flow**: Shows cash movements

---

## Best Practices

### ✅ DO:

1. **Always use "Record & Post"** when entering transactions
2. **Verify debits equal credits** before posting
3. **Attach source documents** for audit trail
4. **Review transactions** in the Journal after posting
5. **Generate financial statements regularly** to catch errors early
6. **Check for draft transactions** before closing a period
7. **Use descriptive descriptions** for transactions
8. **Enter transactions in chronological order**

### ❌ DON'T:

1. **Don't use "Save Draft"** unless you're still working on the entry
2. **Don't post transactions** without verifying debits = credits
3. **Don't skip entering transactions** - enter all business transactions
4. **Don't ignore warnings** - fix issues immediately
5. **Don't change account balances directly** - use journal entries
6. **Don't delete posted entries** - use adjusting entries instead

### Transaction Entry Checklist

Before clicking "Record & Post", verify:
- [ ] Date is correct
- [ ] Description is clear
- [ ] Debit account is selected
- [ ] Credit account is selected
- [ ] Debit amount = Credit amount
- [ ] Source document attached (if available)
- [ ] All fields reviewed and correct

---

## Troubleshooting

### Problem: Balance Sheet Doesn't Balance

**Solution:**
1. Check the "Possible Issues" section in the Balance Sheet
2. Look for draft transactions - post them
3. Check for unbalanced entries - fix them
4. Verify all transactions are in the current period
5. Regenerate the balance sheet

### Problem: Transactions Not Appearing in Balance Sheet

**Possible Causes:**
- Transaction saved as "draft" instead of "posted"
- Transaction assigned to wrong period
- Transaction date is after balance sheet date

**Solution:**
- Check Journal tab for draft entries
- Post any draft entries
- Verify period assignment
- Check transaction dates

### Problem: Scan/Browse Not Working

**Solution:**
1. Check that document file exists and is readable
2. For scanning, ensure camera permissions are granted
3. For image scanning, ensure image file is valid
4. Try manual entry if scanning fails

### Problem: Can't Find an Account

**Solution:**
1. Check account name spelling
2. Verify account is active (not inactive)
3. Use account code if available
4. Check Chart of Accounts tab

### Problem: Amounts Don't Match

**Solution:**
1. Verify debit amount = credit amount
2. Check for typos in amounts
3. Verify currency format (no currency symbols in amount field)
4. Check for rounding differences (should be minimal)

---

## Quick Reference

### Keyboard Shortcuts

- `Ctrl+Enter`: Record & Post transaction
- `Ctrl+Shift+Enter`: Save as Draft
- `F11`: Toggle fullscreen
- `Esc`: Exit fullscreen

### Important Buttons

- **"Record & Post"**: Saves transaction and includes in financial statements
- **"Save Draft"**: Saves transaction but does NOT include in financial statements
- **"Generate Financial Statements"**: Creates income statement, balance sheet, and cash flow
- **"Post"**: Changes draft entry to posted status

### Status Indicators

- **Posted**: Transaction is included in financial statements ✅
- **Draft**: Transaction is NOT included in financial statements ⚠️

---

## Workflow Example

### Daily Transaction Entry Workflow

1. **Morning**: Open application, check current period
2. **During Day**: Enter transactions as they occur:
   - Receive invoice → Enter transaction → Record & Post
   - Pay bill → Enter transaction → Record & Post
   - Make sale → Enter transaction → Record & Post
3. **End of Day**: 
   - Review Journal tab
   - Check for any draft entries
   - Post any drafts
   - Check trial balance to verify (it loads automatically, or click Refresh)
4. **End of Month**:
   - Enter all adjusting entries
   - Make closing entries
   - Generate financial statements
   - Verify balance sheet balances

### Monthly Closing Process

1. Enter all transactions for the month
2. Post all adjusting entries
3. Check adjusted trial balance (go to Trial Balance tab and click Refresh if needed)
4. Review financial statements
5. Make closing entries
6. Check post-closing trial balance (go to Post-Closing tab)
7. Verify balance sheet balances
8. Close the period

---

## Need Help?

If you encounter issues:

1. Check the "Possible Issues" section in the Balance Sheet
2. Review the Journal tab for errors
3. Verify all transactions are posted
4. Check that debits equal credits for all entries
5. Ensure you're using "Record & Post" not "Save Draft"

Remember: **The most common cause of balance sheet imbalance is draft transactions that haven't been posted!**

