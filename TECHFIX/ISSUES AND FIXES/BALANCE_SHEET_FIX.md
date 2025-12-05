# Balance Sheet Imbalance Fix

## Problem Identified

The generator was creating a balance sheet imbalance of ₱391.78 due to **Accounts Payable overpayment**.

### Root Cause

In the generated transactions:
- **Transaction 10**: Purchase on account created ₱140.55 in Accounts Payable
- **Transaction 11**: Payment to vendor paid ₱532.33 to Accounts Payable

This resulted in:
- Accounts Payable balance: ₱140.55 (credit) - ₱532.33 (debit) = **-₱391.78 (debit balance)**
- A debit balance in a liability account means more was paid than was owed
- This created a balance sheet imbalance: Assets ≠ Liabilities + Equity

## Solution Implemented

### 1. Transaction Generation Fix

The generator now **tracks running balances** for:
- **Accounts Payable**: Tracks what's owed to vendors
- **Accounts Receivable**: Tracks what customers owe

**Key Changes:**
- When generating a `pay_accounts_payable` transaction:
  - Checks current Accounts Payable balance
  - Payment amount cannot exceed the balance
  - If no balance exists, the payment transaction is skipped
  - Payment is typically 50-100% of the current balance

- When generating a `collection` transaction:
  - Checks current Accounts Receivable balance
  - Collection amount cannot exceed the balance
  - If no balance exists, the collection transaction is skipped
  - Collection is typically 50-100% of the current balance

### 2. Balance Sheet Calculation Fix

The balance sheet calculation now handles edge cases:
- If Accounts Payable has a debit balance (overpayment), it's treated as a prepaid asset
- This ensures the balance sheet equation: **Assets = Liabilities + Equity**
- The overpayment is shown as "Prepaid (AP Overpayment)" in assets

## How to Fix Your Current Data

Your current `DATA_SUMMARY.txt` still has the imbalance. To fix it:

1. **Regenerate transactions** using the updated generator:
   ```bash
   python generators/generate_business_transactions.py
   ```

2. The new transactions will:
   - Have balanced Accounts Payable (payments won't exceed what's owed)
   - Have balanced Accounts Receivable (collections won't exceed what's owed)
   - Produce a balanced balance sheet

## Verification

After regenerating, check:
1. **Trial Balance**: Total Debits = Total Credits ✓
2. **Balance Sheet**: Assets = Liabilities + Equity ✓
3. **Accounts Payable**: Should have a credit balance (or zero) ✓
4. **Accounts Receivable**: Should have a debit balance (or zero) ✓

## Technical Details

### Code Changes

**File**: `generators/generate_business_transactions.py`

**Method**: `_plan_transactions()` (lines 1277-1330)

- Added balance tracking variables
- Added conditional logic for payment/collection transactions
- Ensures payments/collections don't exceed balances

**Method**: `_calculate_financial_statements()` (lines 1568-1585)

- Enhanced Accounts Payable calculation
- Handles overpayment edge case
- Adds prepaid asset if overpayment occurs

## Expected Behavior

### Before Fix:
- Random payment amounts could exceed Accounts Payable balance
- Balance sheet imbalance: ₱391.78 (or similar)
- Accounts Payable shows debit balance (incorrect)

### After Fix:
- Payment amounts are constrained by Accounts Payable balance
- Balance sheet always balances: Assets = Liabilities + Equity
- Accounts Payable shows credit balance (correct) or zero

## Notes

- If a `pay_accounts_payable` transaction is scheduled but there's no balance, it will be skipped
- This may result in slightly fewer transactions than the target count, but ensures accuracy
- The same logic applies to `collection` transactions for Accounts Receivable

