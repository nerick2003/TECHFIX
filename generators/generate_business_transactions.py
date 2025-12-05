"""
Business Transaction Generator for TechFix
Generates realistic one month of business transactions covering:
- Owner's investment
- Cash and credit sales
- Purchases (supplies, inventory, or equipment)
- Payment of expenses
- Collection from customers
- Owner's withdrawals
- Adjusting entries (depreciation, accrued expenses, accrued taxes)
Also generates financial statements (Income Statement, Balance Sheet, Statement of Owner's Equity)
"""

import os
import json
import random
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from pathlib import Path
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image

# Account names from the app's Chart of Accounts (must stay in sync with techfix.db.seed_chart_of_accounts)
ASSET_ACCOUNTS = [
    "Cash",
    "Accounts Receivable",
    "Input Tax",
    "Office Equipment",
    "Accumulated Depreciation",
]
LIABILITY_ACCOUNTS = [
    "Accounts Payable",
    "Utilities Payable",
    "Withholding Taxes Payable",
    "SSS, PhilHealth, and Pag-Ibig Payable",
    "Expanded Withholding Tax Payable",
    "Accrued Percentage Tax Payable",
]
EQUITY_ACCOUNTS = [
    "Owner's Capital",
    "Owner's Drawings",
]
REVENUE_ACCOUNTS = [
    "Service Income",
]
EXPENSE_ACCOUNTS = [
    "Salaries & Wages",
    "Rent Expense",
    "Utilities Expense",
    "Supplies Expense",
    "PhilHealth, Pag-Ibig and SSS Contributions",
    "Depreciation Expense",
    "Transportation Expense",
    "Percentage Tax Expense",
]

# Transaction types for business simulation
TRANSACTION_TYPES = {
    "owner_investment": {
        "description": "Owner's investment in business",
        "debit_account": "Cash",
        "credit_account": "Owner's Capital",
        "source_type": "Bank",
        "amount_range": (5000.0, 50000.0),
        "frequency": 1,  # Usually happens once at start of month
    },
    "cash_sale": {
        "description": "Cash sale - {client_name}",
        "debit_account": "Cash",
        "credit_account": "Service Income",
        "source_type": "Invoice",
        "amount_range": (100.0, 5000.0),
        "frequency": 4,  # Multiple cash sales throughout month
    },
    "credit_sale": {
        "description": "Credit sale - {client_name}",
        "debit_account": "Accounts Receivable",
        "credit_account": "Service Income",
        "source_type": "Invoice",
        "amount_range": (200.0, 8000.0),
        "frequency": 3,  # Several credit sales
    },
    "collection": {
        "description": "Collection from customer - {client_name}",
        "debit_account": "Cash",
        "credit_account": "Accounts Receivable",
        "source_type": "Bank",
        "amount_range": (150.0, 6000.0),
        "frequency": 2,  # Collections from previous credit sales
    },
    "purchase_supplies": {
        "description": "Purchase of office supplies",
        "debit_account": "Supplies Expense",
        "credit_account": "Cash",
        "source_type": "Receipt",
        "amount_range": (50.0, 500.0),
        "frequency": 2,
    },
    "purchase_equipment": {
        "description": "Purchase of office equipment",
        "debit_account": "Office Equipment",
        "credit_account": "Cash",
        "source_type": "Receipt",
        "amount_range": (500.0, 5000.0),
        "frequency": 1,
    },
    "purchase_on_account": {
        "description": "Purchase on account - {vendor_name}",
        "debit_account": "Supplies Expense",
        "credit_account": "Accounts Payable",
        "source_type": "Receipt",
        "amount_range": (100.0, 2000.0),
        "frequency": 1,
    },
    "pay_expense_rent": {
        "description": "Payment of rent expense",
        "debit_account": "Rent Expense",
        "credit_account": "Cash",
        "source_type": "Bank",
        "amount_range": (1000.0, 5000.0),
        "frequency": 1,
    },
    "pay_expense_utilities": {
        "description": "Payment of utilities expense",
        "debit_account": "Utilities Expense",
        "credit_account": "Cash",
        "source_type": "Bank",
        "amount_range": (100.0, 800.0),
        "frequency": 1,
    },
    "pay_expense_salaries": {
        "description": "Payment of salaries and wages",
        "debit_account": "Salaries & Wages",
        "credit_account": "Cash",
        "source_type": "Payroll",
        "amount_range": (2000.0, 10000.0),
        "frequency": 1,
    },
    "pay_accounts_payable": {
        "description": "Payment to vendor - {vendor_name}",
        "debit_account": "Accounts Payable",
        "credit_account": "Cash",
        "source_type": "Bank",
        "amount_range": (100.0, 2000.0),
        "frequency": 1,
    },
    "owner_withdrawal": {
        "description": "Owner's withdrawal",
        "debit_account": "Owner's Drawings",
        "credit_account": "Cash",
        "source_type": "Bank",
        "amount_range": (500.0, 3000.0),
        "frequency": 1,
    },
    # Adjusting entries (typically at month end)
    "adjust_depreciation": {
        "description": "Adjusting entry - Depreciation expense",
        "debit_account": "Depreciation Expense",
        "credit_account": "Accumulated Depreciation",
        "source_type": "Adjust",
        "amount_range": (100.0, 1000.0),
        "frequency": 1,
        "is_adjusting": True,
    },
    "adjust_accrued_utilities": {
        "description": "Adjusting entry - Accrued utilities expense",
        "debit_account": "Utilities Expense",
        "credit_account": "Utilities Payable",
        "source_type": "Adjust",
        "amount_range": (50.0, 400.0),
        "frequency": 1,
        "is_adjusting": True,
    },
    "adjust_accrued_salaries": {
        "description": "Adjusting entry - Accrued salaries expense",
        "debit_account": "Salaries & Wages",
        "credit_account": "SSS, PhilHealth, and Pag-Ibig Payable",
        "source_type": "Adjust",
        "amount_range": (200.0, 1500.0),
        "frequency": 1,
        "is_adjusting": True,
    },
    "adjust_percentage_tax": {
        "description": "Adjusting entry - Accrued percentage tax",
        "debit_account": "Percentage Tax Expense",
        "credit_account": "Accrued Percentage Tax Payable",
        "source_type": "Adjust",
        "amount_range": (50.0, 500.0),
        "frequency": 1,
        "is_adjusting": True,
    },
}

# Client and vendor names for realistic transactions
CLIENT_NAMES = [
    "ABC Corporation",
    "XYZ Services Inc.",
    "Tech Solutions Ltd.",
    "Global Enterprises",
    "Local Business Co.",
    "Startup Innovations",
    "Digital Marketing Pro",
    "Consulting Group",
]

VENDOR_NAMES = [
    "Office Supply Depot",
    "Equipment Warehouse",
    "Business Services Co.",
    "Supply Chain Solutions",
    "Office Essentials Inc.",
]

DOCUMENT_EXTENSIONS = {
    "Invoice": [".pdf", ".doc", ".docx"],
    "Receipt": [".pdf", ".jpg", ".png"],
    "Bank": [".pdf", ".xls", ".xlsx"],
    "Adjust": [".pdf", ".json"],
    "Payroll": [".pdf", ".docx", ".xlsx"],
    "Other": [".pdf", ".txt"],
}


class BusinessTransactionGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Business Transaction Generator for TechFix")
        self.root.geometry("800x650")
        self.root.minsize(700, 600)
        
        # Create output directories
        self.base_dir = Path(__file__).parent
        self.mock_codes_dir = self.base_dir / "mock_codes"
        self.sample_docs_dir = self.base_dir / "SampleSourceDocs"
        
        self._create_directories()
        self._build_ui()
        
    def _create_directories(self):
        """Create output directories if they don't exist"""
        self.mock_codes_dir.mkdir(exist_ok=True)
        self.sample_docs_dir.mkdir(exist_ok=True)
    
    def _build_ui(self):
        """Build the GUI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Business Transaction Generator", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle_label = ttk.Label(
            main_frame,
            text="Generates 15-20 realistic business transactions for one month",
            font=("Arial", 10),
            foreground="gray"
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Month and Year selection
        date_frame = ttk.LabelFrame(main_frame, text="Select Month", padding="10")
        date_frame.pack(fill=tk.X, pady=10)
        
        date_selection_frame = ttk.Frame(date_frame)
        date_selection_frame.pack(fill=tk.X)
        
        ttk.Label(date_selection_frame, text="Month:").pack(side=tk.LEFT, padx=(0, 5))
        self.month_var = tk.StringVar(value=datetime.now().strftime("%B"))
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        month_combo = ttk.Combobox(date_selection_frame, textvariable=self.month_var, 
                                   values=months, state="readonly", width=12)
        month_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(date_selection_frame, text="Year:").pack(side=tk.LEFT, padx=(0, 5))
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        years = [str(y) for y in range(2020, 2030)]
        year_combo = ttk.Combobox(date_selection_frame, textvariable=self.year_var,
                                  values=years, state="readonly", width=8)
        year_combo.pack(side=tk.LEFT)
        
        # Transaction count (optional override)
        count_frame = ttk.LabelFrame(main_frame, text="Transaction Count (Optional)", padding="10")
        count_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(count_frame, text="Number of transactions (15-20 recommended):").pack(side=tk.LEFT, padx=(0, 10))
        self.count_var = tk.StringVar(value="18")
        count_entry = ttk.Entry(count_frame, textvariable=self.count_var, width=10)
        count_entry.pack(side=tk.LEFT)
        
        # Checkboxes for what to generate
        options_frame = ttk.LabelFrame(main_frame, text="Generate", padding="10")
        options_frame.pack(fill=tk.X, pady=10)
        
        self.generate_mock_codes = tk.BooleanVar(value=True)
        self.generate_sample_docs = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(
            options_frame, 
            text="mock_codes (QR + Barcode PNG + TXT)", 
            variable=self.generate_mock_codes
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Checkbutton(
            options_frame, 
            text="SampleSourceDocs (Documents + JSON)", 
            variable=self.generate_sample_docs
        ).pack(anchor=tk.W, pady=2)
        
        # Progress bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.pack(anchor=tk.W)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Status text
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(status_frame, text="Status:").pack(anchor=tk.W)
        
        # Create a frame for text and scrollbar
        text_scroll_frame = ttk.Frame(status_frame)
        text_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = tk.Text(
            text_scroll_frame,
            height=5,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_scroll_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Generate button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.generate_button = ttk.Button(
            button_frame,
            text="Generate Business Transactions",
            command=self._generate_files
        )
        self.generate_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Clear Status",
            command=self._clear_status
        ).pack(side=tk.LEFT, padx=5)
    
    def _log(self, message):
        """Log a message to the status text"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update()
    
    def _clear_status(self):
        """Clear the status text"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def _generate_files(self):
        """Generate all requested files"""
        try:
            count = int(self.count_var.get())
            if count < 15 or count > 30:
                if not messagebox.askyesno(
                    "Warning", 
                    f"You've requested {count} transactions. Recommended range is 15-20.\n\nContinue anyway?"
                ):
                    return
        except ValueError:
            messagebox.showerror("Error", "Invalid transaction count value")
            return
        
        if not any([
            self.generate_mock_codes.get(),
            self.generate_sample_docs.get()
        ]):
            messagebox.showwarning("Warning", "Please select at least one type to generate")
            return
        
        self.generate_button.config(state=tk.DISABLED)
        self._clear_status()
        
        try:
            # Generate transaction plan
            transactions = self._plan_transactions(count)
            
            # Calculate total files that will be generated
            total_files = 0
            if self.generate_mock_codes.get():
                total_files += len(transactions) * 4  # QR PNG, QR TXT, Barcode PNG, Barcode TXT
            if self.generate_sample_docs.get():
                total_files += len(transactions) * 2  # Document + JSON
            
            self.progress_bar.config(maximum=total_files, value=0)
            files_generated = 0
            
            if self.generate_mock_codes.get():
                self._log(f"Generating {len(transactions)} mock_codes transactions ({len(transactions) * 4} files)...")
                files_generated += self._generate_mock_codes(transactions, files_generated, total_files)
            
            if self.generate_sample_docs.get():
                self._log(f"Generating {len(transactions)} SampleSourceDocs transactions ({len(transactions) * 2} files)...")
                files_generated += self._generate_sample_docs(transactions, files_generated, total_files)
            
            self.progress_var.set("Complete!")
            self._log(f"\n{'='*70}")
            self._log(f"✓ GENERATION COMPLETE!")
            self._log(f"{'='*70}\n")
            
            # Generate comprehensive summary
            self._generate_summary(transactions, files_generated)
            
            messagebox.showinfo("Success", f"Generated {files_generated} files for {len(transactions)} transactions!")
            
        except Exception as e:
            self._log(f"Error: {str(e)}")
            import traceback
            self._log(traceback.format_exc())
            messagebox.showerror("Error", f"Generation failed: {str(e)}")
        finally:
            self.generate_button.config(state=tk.NORMAL)
            self.progress_bar.config(value=0)
    
    def _generate_summary(self, transactions, files_generated):
        """Generate comprehensive summary of generated transactions and files"""
        # Collect summary lines for file output
        summary_lines = []
        
        def add_line(text):
            """Add a line to both log and summary file"""
            self._log(text)
            summary_lines.append(text)
        
        # File generation summary
        add_line("FILE GENERATION SUMMARY")
        add_line("-" * 70)
        mock_codes_count = len(transactions) * 4 if self.generate_mock_codes.get() else 0
        sample_docs_count = len(transactions) * 2 if self.generate_sample_docs.get() else 0
        
        if self.generate_mock_codes.get():
            add_line(f"✓ mock_codes directory:")
            add_line(f"    - QR Code PNG files: {len(transactions)}")
            add_line(f"    - QR Code TXT files: {len(transactions)}")
            add_line(f"    - Barcode PNG files: {len(transactions)}")
            add_line(f"    - Barcode TXT files: {len(transactions)}")
            add_line(f"    Subtotal: {mock_codes_count} files")
        
        if self.generate_sample_docs.get():
            add_line(f"✓ SampleSourceDocs directory:")
            add_line(f"    - Document files: {len(transactions)}")
            add_line(f"    - JSON metadata files: {len(transactions)}")
            add_line(f"    Subtotal: {sample_docs_count} files")
        
        add_line(f"\nTotal Files Generated: {files_generated}")
        add_line(f"Total Transactions: {len(transactions)}\n")
        
        # Transaction details
        add_line("TRANSACTION DETAILS")
        add_line("-" * 70)
        total_debits = 0
        total_credits = 0
        
        for i, txn in enumerate(transactions, 1):
            total_debits += txn['amount']
            total_credits += txn['amount']
            add_line(f"{i:2d}. Date: {txn['date_str']}")
            add_line(f"     Type: {txn['source_type']}")
            add_line(f"     Description: {txn['description']}")
            add_line(f"     Debit:  {txn['debit_account']:40s} ₱{txn['amount']:>12,.2f}")
            add_line(f"     Credit: {txn['credit_account']:40s} ₱{txn['amount']:>12,.2f}")
            add_line(f"     Reference: {txn['external_ref']}")
            add_line("")
        
        # Financial summary
        add_line("FINANCIAL SUMMARY")
        add_line("-" * 70)
        add_line(f"Total Debits:  ₱{total_debits:>15,.2f}")
        add_line(f"Total Credits: ₱{total_credits:>15,.2f}")
        add_line(f"Balance Check: {'✓ Balanced' if abs(total_debits - total_credits) < 0.01 else '✗ Unbalanced'}\n")
        
        # Summary by account
        add_line("SUMMARY BY ACCOUNT")
        add_line("-" * 70)
        account_debits = {}
        account_credits = {}
        
        for txn in transactions:
            debit_acct = txn['debit_account']
            credit_acct = txn['credit_account']
            amount = txn['amount']
            
            account_debits[debit_acct] = account_debits.get(debit_acct, 0) + amount
            account_credits[credit_acct] = account_credits.get(credit_acct, 0) + amount
        
        all_accounts = sorted(set(list(account_debits.keys()) + list(account_credits.keys())))
        
        for account in all_accounts:
            debits = account_debits.get(account, 0)
            credits = account_credits.get(account, 0)
            net = debits - credits
            add_line(f"{account:45s} Debits: ₱{debits:>12,.2f}  Credits: ₱{credits:>12,.2f}  Net: ₱{net:>12,.2f}")
        
        add_line("")
        
        # Summary by transaction type
        add_line("SUMMARY BY TRANSACTION TYPE")
        add_line("-" * 70)
        
        # Map transaction types to display names
        type_mapping = {
            "owner_investment": "Owner's Investment",
            "cash_sale": "Cash Sales",
            "credit_sale": "Credit Sales",
            "collection": "Collections from Customers",
            "purchase_supplies": "Purchase Supplies",
            "purchase_equipment": "Purchase Equipment",
            "purchase_on_account": "Purchase on Account",
            "pay_expense_rent": "Pay Rent Expense",
            "pay_expense_utilities": "Pay Utilities Expense",
            "pay_expense_salaries": "Pay Salaries Expense",
            "pay_accounts_payable": "Pay Accounts Payable",
            "owner_withdrawal": "Owner's Withdrawal",
            "adjust_depreciation": "Adjusting Entry - Depreciation",
            "adjust_accrued_utilities": "Adjusting Entry - Accrued Utilities",
            "adjust_accrued_salaries": "Adjusting Entry - Accrued Salaries",
            "adjust_percentage_tax": "Adjusting Entry - Percentage Tax",
        }
        
        # Count transactions by type
        type_counts = {}
        type_totals = {}
        
        for txn in transactions:
            txn_type = txn.get('transaction_type', 'unknown')
            display_name = type_mapping.get(txn_type, txn_type.replace('_', ' ').title())
            type_counts[display_name] = type_counts.get(display_name, 0) + 1
            type_totals[display_name] = type_totals.get(display_name, 0) + txn['amount']
        
        for txn_type in sorted(type_counts.keys()):
            count = type_counts[txn_type]
            total = type_totals[txn_type]
            add_line(f"{txn_type:40s} Count: {count:3d}  Total: ₱{total:>15,.2f}")
        
        add_line("")
        
        # Summary by category
        add_line("SUMMARY BY CATEGORY")
        add_line("-" * 70)
        
        # Map transaction types to categories
        category_mapping = {
            "owner_investment": "Investments",
            "cash_sale": "Revenue",
            "credit_sale": "Revenue",
            "collection": "Collections",
            "purchase_supplies": "Purchases",
            "purchase_equipment": "Purchases",
            "purchase_on_account": "Purchases",
            "pay_expense_rent": "Expenses",
            "pay_expense_utilities": "Expenses",
            "pay_expense_salaries": "Expenses",
            "pay_accounts_payable": "Payments",
            "owner_withdrawal": "Withdrawals",
            "adjust_depreciation": "Adjusting Entries",
            "adjust_accrued_utilities": "Adjusting Entries",
            "adjust_accrued_salaries": "Adjusting Entries",
            "adjust_percentage_tax": "Adjusting Entries",
        }
        
        category_counts = {}
        category_totals = {}
        
        for txn in transactions:
            txn_type = txn.get('transaction_type', 'unknown')
            category = category_mapping.get(txn_type, "Other")
            category_counts[category] = category_counts.get(category, 0) + 1
            category_totals[category] = category_totals.get(category, 0) + txn['amount']
        
        for category in sorted(category_counts.keys()):
            count = category_counts[category]
            total = category_totals[category]
            add_line(f"{category:30s} Count: {count:3d}  Total: ₱{total:>15,.2f}")
        
        add_line("")
        
        # Adjusting Entries Section
        add_line("ADJUSTING ENTRIES")
        add_line("-" * 70)
        adjusting_entries = [txn for txn in transactions if txn.get('is_adjusting', False)]
        
        if adjusting_entries:
            add_line("The following adjusting entries have been generated and should be posted:")
            add_line("")
            for i, adj in enumerate(adjusting_entries, 1):
                add_line(f"{i}. {adj['description']}")
                add_line(f"   Date: {adj['date_str']}")
                add_line(f"   Debit:  {adj['debit_account']:40s} ₱{adj['amount']:>12,.2f}")
                add_line(f"   Credit: {adj['credit_account']:40s} ₱{adj['amount']:>12,.2f}")
                add_line(f"   Reference: {adj['external_ref']}")
                add_line("")
            add_line("Note: Adjusting entries are typically posted at the end of the accounting period")
            add_line("      to ensure revenues and expenses are recorded in the correct period.")
        else:
            add_line("No adjusting entries were generated for this period.")
        
        add_line("")
        
        # Financial Statements
        add_line("FINANCIAL STATEMENTS")
        add_line("=" * 70)
        
        try:
            financials = self._calculate_financial_statements(transactions)
            
            # Income Statement
            add_line("")
            add_line("INCOME STATEMENT")
            add_line(f"For the month ended {financials['period']}")
            add_line("-" * 70)
            add_line("REVENUES")
            for account, amount in financials['income_statement']['revenue'].items():
                if amount > 0:
                    add_line(f"  {account:45s} ₱{amount:>15,.2f}")
            add_line(f"  {'Total Revenue':45s} ₱{financials['income_statement']['total_revenue']:>15,.2f}")
            add_line("")
            add_line("EXPENSES")
            for account, amount in financials['income_statement']['expenses'].items():
                if amount > 0:
                    add_line(f"  {account:45s} ₱{amount:>15,.2f}")
            add_line(f"  {'Total Expenses':45s} ₱{financials['income_statement']['total_expenses']:>15,.2f}")
            add_line("-" * 70)
            net_income = financials['income_statement']['net_income']
            income_label = "NET INCOME" if net_income >= 0 else "NET LOSS"
            add_line(f"  {income_label:45s} ₱{abs(net_income):>15,.2f}")
            add_line("")
            
            # Statement of Owner's Equity
            add_line("STATEMENT OF OWNER'S EQUITY")
            add_line(f"For the month ended {financials['period']}")
            add_line("-" * 70)
            equity = financials['statement_of_equity']
            add_line(f"  Owner's Capital, Beginning        ₱{equity['beginning_capital']:>15,.2f}")
            if equity['additions'] > 0:
                add_line(f"  Add: Owner's Investment          ₱{equity['additions']:>15,.2f}")
            if equity['net_income'] > 0:
                add_line(f"  Add: Net Income                  ₱{equity['net_income']:>15,.2f}")
            elif equity['net_income'] < 0:
                add_line(f"  Less: Net Loss                   ₱{abs(equity['net_income']):>15,.2f}")
            if equity['drawings'] > 0:
                add_line(f"  Less: Owner's Drawings           ₱{equity['drawings']:>15,.2f}")
            add_line("-" * 70)
            add_line(f"  Owner's Capital, Ending           ₱{equity['ending_capital']:>15,.2f}")
            add_line("")
            
            # Balance Sheet
            add_line("BALANCE SHEET")
            add_line(f"As of {financials['period']}")
            add_line("-" * 70)
            add_line("ASSETS")
            bs = financials['balance_sheet']
            if bs['assets'].get('Cash', 0) > 0:
                add_line(f"  Cash                              ₱{bs['assets']['Cash']:>15,.2f}")
            if bs['assets'].get('Accounts Receivable', 0) > 0:
                add_line(f"  Accounts Receivable               ₱{bs['assets']['Accounts Receivable']:>15,.2f}")
            if bs['assets'].get('Input Tax', 0) > 0:
                add_line(f"  Input Tax                         ₱{bs['assets']['Input Tax']:>15,.2f}")
            if bs['office_equipment_net'] > 0:
                add_line(f"  Office Equipment                  ₱{bs['assets'].get('Office Equipment', 0):>15,.2f}")
                if bs['assets'].get('Accumulated Depreciation', 0) < 0:
                    add_line(f"  Less: Accumulated Depreciation    ₱{abs(bs['assets']['Accumulated Depreciation']):>15,.2f}")
                add_line(f"  Office Equipment (Net)            ₱{bs['office_equipment_net']:>15,.2f}")
            add_line(f"  {'Total Assets':45s} ₱{bs['total_assets']:>15,.2f}")
            add_line("")
            add_line("LIABILITIES")
            for account, amount in sorted(bs['liabilities'].items()):
                if amount > 0:
                    add_line(f"  {account:45s} ₱{amount:>15,.2f}")
            add_line(f"  {'Total Liabilities':45s} ₱{bs['total_liabilities']:>15,.2f}")
            add_line("")
            add_line("OWNER'S EQUITY")
            for account, amount in bs['equity'].items():
                if account != "Total Owner's Equity" and amount != 0:
                    if account == "Owner's Drawings":
                        add_line(f"  {account:45s} ₱{abs(amount):>15,.2f}")
                    else:
                        add_line(f"  {account:45s} ₱{amount:>15,.2f}")
            add_line(f"  {'Total Owner\'s Equity':45s} ₱{bs['equity']['Total Owner\'s Equity']:>15,.2f}")
            add_line("-" * 70)
            add_line(f"  {'Total Liabilities and Equity':45s} ₱{bs['total_liabilities_equity']:>15,.2f}")
            add_line("")
            
            # Balance check
            balance_check = abs(bs['total_assets'] - bs['total_liabilities_equity'])
            if balance_check < 0.01:
                add_line("✓ Balance Sheet is balanced")
            else:
                add_line(f"⚠ Balance Sheet difference: ₱{balance_check:,.2f}")
            add_line("")
            
        except Exception as e:
            add_line(f"Error calculating financial statements: {str(e)}")
            import traceback
            add_line(traceback.format_exc())
            add_line("")
        
        # Expected output summary
        add_line("EXPECTED OUTPUT")
        add_line("-" * 70)
        add_line(f"✓ All transactions are saved in chronological order")
        add_line(f"✓ Each transaction includes:")
        add_line(f"    - Date, description, source type")
        add_line(f"    - Debit and credit accounts")
        add_line(f"    - Amounts (balanced)")
        add_line(f"    - Document references")
        
        if self.generate_mock_codes.get():
            add_line(f"\n✓ mock_codes directory contains:")
            add_line(f"    - QR code images (PNG) for scanning")
            add_line(f"    - QR code text files (JSON data)")
            add_line(f"    - Barcode images (PNG)")
            add_line(f"    - Barcode text files (JSON data)")
        
        if self.generate_sample_docs.get():
            add_line(f"\n✓ SampleSourceDocs directory contains:")
            add_line(f"    - Document files (PDF, DOCX, etc.)")
            add_line(f"    - JSON metadata files with transaction details")
        
        add_line(f"\n✓ All transactions cover:")
        add_line(f"    - Owner's investment")
        add_line(f"    - Cash and credit sales")
        add_line(f"    - Purchases (supplies, equipment, on account)")
        add_line(f"    - Payment of expenses (rent, utilities, salaries)")
        add_line(f"    - Collection from customers")
        add_line(f"    - Owner's withdrawals")
        add_line(f"    - Adjusting entries (depreciation, accrued expenses)")
        
        add_line(f"\n{'='*70}")
        
        # Add step-by-step instructions
        add_line("")
        add_line("STEP-BY-STEP INSTRUCTIONS: HOW TO ENTER GENERATED DATA INTO TECHFIX")
        add_line("=" * 70)
        add_line("")
        add_line("This guide will walk you through entering all the generated transactions")
        add_line("from recording entries all the way to reversing entry schedule.")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 1: SET UP YOUR ACCOUNTING PERIOD")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("1. Open TechFix application")
        add_line("2. Make sure the current accounting period matches the month/year you selected")
        add_line("   in the generator (e.g., December 2025)")
        add_line("3. If you need to create a new period:")
        add_line("   - Go to the Periods/Setup section")
        add_line("   - Create a new accounting period for the correct month and year")
        add_line("   - Set it as the active period")
        add_line("4. Verify the period is open (not closed) before proceeding")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 2: RECORD REGULAR TRANSACTIONS (Non-Adjusting Entries)")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("For each transaction listed in the \"TRANSACTION DETAILS\" section above,")
        add_line("EXCEPT the adjusting entries (those dated on the last day of the month):")
        add_line("")
        add_line("1. Go to the \"Transactions\" tab in TechFix")
        add_line("2. Click \"New Entry\" or \"Record Transaction\"")
        add_line("3. Fill in the transaction details:")
        add_line("   ")
        add_line("   For each transaction, enter:")
        add_line("   - Date: Use the date from the transaction (e.g., 2025-12-02)")
        add_line("   - Description: Copy from \"Description\" field")
        add_line("   - Source Type: Select from dropdown (Bank, Invoice, Receipt, Payroll, etc.)")
        add_line("   - Document Reference: Enter the \"Reference\" (e.g., BAN-10000)")
        add_line("   - External Reference: Same as Document Reference")
        add_line("   ")
        add_line("   DEBIT SIDE:")
        add_line("   - Debit Account: Select from dropdown (e.g., \"Cash\", \"Accounts Receivable\")")
        add_line("   - Debit Amount: Enter the amount shown")
        add_line("   ")
        add_line("   CREDIT SIDE:")
        add_line("   - Credit Account: Select from dropdown (e.g., \"Owner's Capital\", \"Service Income\")")
        add_line("   - Credit Amount: Enter the same amount (must match debit)")
        add_line("   ")
        add_line("4. OPTIONAL: Attach source document if you generated SampleSourceDocs")
        add_line("   - Click \"Attach Document\" or \"Browse\"")
        add_line("   - Navigate to: TECHFIX/SampleSourceDocs/")
        add_line("   - Find the file matching the transaction date and reference")
        add_line("   - Attach the document file (.pdf, .docx, etc.)")
        add_line("   ")
        add_line("5. OPTIONAL: Use QR/Barcode scanning for faster entry")
        add_line("   - If you generated mock_codes, you can scan the QR code or barcode")
        add_line("   - Click \"Scan\" or \"Prefill from Document\"")
        add_line("   - The system should auto-fill the transaction details")
        add_line("   ")
        add_line("6. Review all fields to ensure accuracy")
        add_line("7. Click \"Record\" or \"Post\" to save the entry")
        add_line("8. You should see a confirmation message with the entry ID")
        add_line("")
        add_line("REPEAT for ALL regular transactions (typically transactions 1-18 in the list above)")
        add_line("")
        add_line("TIP: You can enter transactions in any order, but chronological order is recommended.")
        add_line("     The system will organize them by date automatically.")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 3: VERIFY TRANSACTIONS IN THE JOURNAL")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("1. Go to the \"Journal\" tab")
        add_line("2. Review all entries you've recorded")
        add_line("3. Verify:")
        add_line("   - All transactions are present")
        add_line("   - Dates are correct")
        add_line("   - Debit and credit amounts match")
        add_line("   - Account names are correct")
        add_line("4. If you find any errors:")
        add_line("   - Note the entry ID")
        add_line("   - You may need to make a correcting entry (debit/credit reversal)")
        add_line("   - Or delete and re-enter if the system allows")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 4: GENERATE UNADJUSTED TRIAL BALANCE")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("1. Go to the \"Trial Balance\" tab")
        add_line("2. Click \"Generate Trial Balance\" or \"Refresh\"")
        add_line("3. Review the trial balance:")
        add_line("   - Total Debits should equal Total Credits")
        add_line("   - Compare with the \"SUMMARY BY ACCOUNT\" section above")
        add_line("   - Verify account balances match expected values")
        add_line("4. If totals don't balance:")
        add_line("   - Go back to Journal tab")
        add_line("   - Check each entry for errors")
        add_line("   - Common errors: wrong account, wrong amount, missing entry")
        add_line("5. Once balanced, you can mark this step as complete in the Accounting Cycle")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 5: POST ADJUSTING ENTRIES")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("IMPORTANT: Adjusting entries are dated on the LAST DAY of the month")
        add_line("(e.g., 2025-12-31). Post these AFTER all regular transactions.")
        add_line("")
        add_line("For each adjusting entry listed in the \"ADJUSTING ENTRIES\" section above:")
        add_line("")
        add_line("1. Go to the \"Transactions\" tab (or \"Adjustments\" tab if available)")
        add_line("2. Click \"New Entry\" or \"Record Transaction\"")
        add_line("3. CHECK THE BOX: \"Is Adjusting Entry\" or \"Adjusting Entry\"")
        add_line("   - This is CRITICAL - it marks the entry as an adjustment")
        add_line("4. Fill in the transaction details:")
        add_line("   ")
        add_line("   - Date: Use the LAST DAY of the month (e.g., 2025-12-31)")
        add_line("   - Description: Copy from adjusting entry description")
        add_line("   - Source Type: Select \"Adjust\" from dropdown")
        add_line("   - Document Reference: Enter the reference (e.g., ADJ-10018)")
        add_line("   - External Reference: Same as Document Reference")
        add_line("   ")
        add_line("   DEBIT SIDE:")
        add_line("   - Debit Account: Select the expense account (e.g., \"Depreciation Expense\")")
        add_line("   - Debit Amount: Enter the amount shown")
        add_line("   ")
        add_line("   CREDIT SIDE:")
        add_line("   - Credit Account: Select the corresponding account (e.g., \"Accumulated Depreciation\")")
        add_line("   - Credit Amount: Enter the same amount")
        add_line("   ")
        add_line("5. Review all fields")
        add_line("6. Click \"Record\" or \"Post\" to save the adjusting entry")
        add_line("")
        add_line("REPEAT for ALL adjusting entries (typically 4 entries at month end)")
        add_line("")
        add_line("ADJUSTING ENTRIES TO POST (from above):")
        add_line("1. Depreciation Expense → Accumulated Depreciation")
        add_line("2. Utilities Expense → Utilities Payable")
        add_line("3. Salaries & Wages → SSS, PhilHealth, and Pag-Ibig Payable")
        add_line("4. Percentage Tax Expense → Accrued Percentage Tax Payable")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 6: GENERATE ADJUSTED TRIAL BALANCE")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("1. Go to the \"Trial Balance\" tab")
        add_line("2. Click \"Generate Trial Balance\" or \"Refresh\"")
        add_line("3. The trial balance should now include the adjusting entries")
        add_line("4. Verify:")
        add_line("   - Total Debits still equal Total Credits")
        add_line("   - Adjusting entry accounts appear with their balances")
        add_line("   - Compare with the \"SUMMARY BY ACCOUNT\" section above")
        add_line("5. Mark this step as complete in the Accounting Cycle")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 7: GENERATE FINANCIAL STATEMENTS")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("1. Go to the \"Fin. Statements\" or \"Financial Statements\" tab")
        add_line("2. Generate each statement:")
        add_line("")
        add_line("   A. INCOME STATEMENT:")
        add_line("      - Click \"Generate Income Statement\"")
        add_line("      - Select the period (start and end dates)")
        add_line("      - Review and compare with the \"INCOME STATEMENT\" section above")
        add_line("      - Verify:")
        add_line("        * Total Revenue matches")
        add_line("        * Total Expenses matches")
        add_line("        * Net Income (or Net Loss) matches")
        add_line("   ")
        add_line("   B. STATEMENT OF OWNER'S EQUITY:")
        add_line("      - Click \"Generate Statement of Owner's Equity\"")
        add_line("      - Review and compare with the \"STATEMENT OF OWNER'S EQUITY\" section above")
        add_line("      - Verify:")
        add_line("        * Beginning Capital")
        add_line("        * Owner's Investment (additions)")
        add_line("        * Net Income (or Net Loss)")
        add_line("        * Owner's Drawings")
        add_line("        * Ending Capital")
        add_line("   ")
        add_line("   C. BALANCE SHEET:")
        add_line("      - Click \"Generate Balance Sheet\"")
        add_line("      - Review and compare with the \"BALANCE SHEET\" section above")
        add_line("      - Verify:")
        add_line("        * Total Assets matches")
        add_line("        * Total Liabilities matches")
        add_line("        * Total Owner's Equity matches")
        add_line("        * Assets = Liabilities + Equity (balanced)")
        add_line("3. If any statement doesn't match:")
        add_line("   - Go back and check your entries")
        add_line("   - Verify adjusting entries were posted correctly")
        add_line("   - Check account classifications")
        add_line("4. Mark this step as complete in the Accounting Cycle")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 8: PERFORM CLOSING ENTRIES")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("1. Go to the \"Closing\" tab")
        add_line("2. Review the closing entries that will be created:")
        add_line("   - Revenue accounts will be closed (debited) to Income Summary")
        add_line("   - Expense accounts will be closed (credited) to Income Summary")
        add_line("   - Income Summary will be closed to Owner's Capital")
        add_line("   - Owner's Drawings will be closed to Owner's Capital")
        add_line("3. Click \"Make Closing Entries\" or \"Close Period\"")
        add_line("4. The system will automatically create the closing entries")
        add_line("5. Review the closing entries in the Journal tab")
        add_line("6. Verify they were created correctly")
        add_line("7. Mark this step as complete in the Accounting Cycle")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 9: GENERATE POST-CLOSING TRIAL BALANCE")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("1. Go to the \"Post-Closing\" tab")
        add_line("2. Click \"Generate Post-Closing Trial Balance\"")
        add_line("3. Review the trial balance:")
        add_line("   - Only permanent accounts should appear (Assets, Liabilities, Equity)")
        add_line("   - Temporary accounts (Revenue, Expenses, Drawings) should have zero balances")
        add_line("   - Total Debits should equal Total Credits")
        add_line("4. Mark this step as complete in the Accounting Cycle")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 10: SET UP REVERSING ENTRY SCHEDULE")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("IMPORTANT: Reversing entries are for ACCRUAL-TYPE adjusting entries only.")
        add_line("They reverse the adjusting entry on the first day of the next period.")
        add_line("")
        add_line("For the adjusting entries that need reversing:")
        add_line("- Accrued Utilities Expense (Utilities Payable)")
        add_line("- Accrued Salaries Expense (SSS, PhilHealth, and Pag-Ibig Payable)")
        add_line("- Accrued Percentage Tax (Accrued Percentage Tax Payable)")
        add_line("")
        add_line("NOTE: Depreciation does NOT get reversed (it's a permanent adjustment)")
        add_line("")
        add_line("METHOD 1: Using Reversing Entry Schedule Tab")
        add_line("")
        add_line("1. Go to the \"Reversing Schedule\" or \"Post-Closing\" tab")
        add_line("2. Find the section for \"Reversing Entry Schedule\"")
        add_line("3. For each accrual adjusting entry:")
        add_line("   ")
        add_line("   a. Find the adjusting entry ID from the Journal tab")
        add_line("   ")
        add_line("   b. Click \"Schedule Reversing Entry\" or \"Add to Reversing Schedule\"")
        add_line("   ")
        add_line("   c. Enter:")
        add_line("      - Original Entry ID: The adjusting entry ID")
        add_line("      - Reverse On: First day of next month (e.g., 2026-01-01)")
        add_line("      - Deadline On: Same as Reverse On date")
        add_line("      - Reminder On: One day before (e.g., 2025-12-31)")
        add_line("      - Category: Select \"Accrual\"")
        add_line("      - Memo: \"Reverse [description]\" (e.g., \"Reverse accrued utilities\")")
        add_line("   ")
        add_line("   d. Click \"Schedule\" or \"Save\"")
        add_line("")
        add_line("METHOD 2: When Recording Adjusting Entry")
        add_line("")
        add_line("1. When posting the adjusting entry in Step 5:")
        add_line("2. Look for \"Schedule Reversing Entry\" checkbox or field")
        add_line("3. Check the box if available")
        add_line("4. Enter:")
        add_line("   - Reverse On: First day of next month")
        add_line("   - Deadline On: Same date")
        add_line("   - Reminder On: One day before")
        add_line("5. The system will automatically schedule the reversal")
        add_line("")
        add_line("VERIFY THE SCHEDULE:")
        add_line("")
        add_line("1. Go to the \"Reversing Schedule\" tab")
        add_line("2. Review the list of scheduled reversals")
        add_line("3. You should see entries for:")
        add_line("   - Accrued Utilities (reverse on first day of next month)")
        add_line("   - Accrued Salaries (reverse on first day of next month)")
        add_line("   - Accrued Percentage Tax (reverse on first day of next month)")
        add_line("4. Status should show \"pending\"")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("STEP 11: PROCESS REVERSING ENTRIES (Next Period)")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("When the next accounting period begins (e.g., January 2026):")
        add_line("")
        add_line("1. Create and activate the new accounting period")
        add_line("2. Go to the \"Reversing Schedule\" or \"Post-Closing\" tab")
        add_line("3. Review the pending reversing entries")
        add_line("4. Click \"Process Reversing Schedule\" or \"Post Reversing Entries\"")
        add_line("5. Enter the \"As Of\" date (first day of new period, e.g., 2026-01-01)")
        add_line("6. Click \"Process\" or \"Post\"")
        add_line("7. The system will automatically:")
        add_line("   - Create reversing entries for each scheduled reversal")
        add_line("   - Reverse the debits and credits")
        add_line("   - Update the status to \"completed\"")
        add_line("8. Verify the reversing entries in the Journal tab")
        add_line("9. They should appear as new entries dated the first day of the new period")
        add_line("")
        add_line("EXAMPLE REVERSING ENTRY:")
        add_line("Original (Dec 31):  Utilities Expense (Dr) → Utilities Payable (Cr)")
        add_line("Reversal (Jan 1):   Utilities Payable (Dr) → Utilities Expense (Cr)")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("TROUBLESHOOTING TIPS")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("PROBLEM: Trial Balance doesn't balance")
        add_line("SOLUTION:")
        add_line("- Check each entry has equal debits and credits")
        add_line("- Verify account names are spelled correctly")
        add_line("- Check for missing entries")
        add_line("- Review the Journal tab for errors")
        add_line("")
        add_line("PROBLEM: Financial statements don't match expected values")
        add_line("SOLUTION:")
        add_line("- Verify all adjusting entries were posted")
        add_line("- Check that adjusting entries are marked as \"adjusting\"")
        add_line("- Review account classifications (Asset, Liability, Equity, Revenue, Expense)")
        add_line("- Ensure closing entries were made")
        add_line("")
        add_line("PROBLEM: Can't find an account in the dropdown")
        add_line("SOLUTION:")
        add_line("- Check the account name spelling (exact match required)")
        add_line("- Verify the Chart of Accounts includes the account")
        add_line("- Some accounts may need to be created first")
        add_line("")
        add_line("PROBLEM: Reversing entries not processing")
        add_line("SOLUTION:")
        add_line("- Verify the \"Reverse On\" date has passed")
        add_line("- Check the entry status is \"pending\"")
        add_line("- Ensure the new period is active")
        add_line("- Review the reversing schedule for errors")
        add_line("")
        add_line("PROBLEM: QR/Barcode scanning not working")
        add_line("SOLUTION:")
        add_line("- Ensure the QR code or barcode file is in mock_codes directory")
        add_line("- Check the file format (PNG for images, TXT for text)")
        add_line("- Try manual entry if scanning fails")
        add_line("- Verify the JSON format in the TXT file is correct")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("QUICK REFERENCE CHECKLIST")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        add_line("□ Step 1: Set up accounting period")
        add_line("□ Step 2: Record all regular transactions (1-18)")
        add_line("□ Step 3: Verify in Journal tab")
        add_line("□ Step 4: Generate unadjusted trial balance")
        add_line("□ Step 5: Post adjusting entries (4 entries on last day)")
        add_line("□ Step 6: Generate adjusted trial balance")
        add_line("□ Step 7: Generate financial statements (Income, Equity, Balance Sheet)")
        add_line("□ Step 8: Perform closing entries")
        add_line("□ Step 9: Generate post-closing trial balance")
        add_line("□ Step 10: Set up reversing entry schedule (3 accruals)")
        add_line("□ Step 11: Process reversing entries (next period)")
        add_line("")
        add_line("═══════════════════════════════════════════════════════════════════════")
        add_line("")
        
        # Write summary to file
        summary_file_path = self.base_dir / "DATA_SUMMARY.txt"
        try:
            with open(summary_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(summary_lines))
            add_line(f"\n✓ Summary saved to: {summary_file_path}")
        except Exception as e:
            self._log(f"\n⚠ Warning: Could not save summary to file: {str(e)}")
    
    def _plan_transactions(self, target_count):
        """Plan realistic business transactions for the month"""
        transactions = []
        
        # Get selected month and year
        month_name = self.month_var.get()
        year = int(self.year_var.get())
        month_num = datetime.strptime(month_name, "%B").month
        
        # Calculate first and last day of the month
        if month_num == 12:
            first_day = datetime(year, month_num, 1)
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            first_day = datetime(year, month_num, 1)
            last_day = datetime(year, month_num + 1, 1) - timedelta(days=1)
        
        days_in_month = (last_day - first_day).days + 1
        
        # Build transaction list ensuring we cover all required types
        transaction_plan = []
        
        # 1. Owner's investment (early in month, usually day 1-3)
        transaction_plan.append({
            "type": "owner_investment",
            "day": random.randint(1, 3),
            "priority": 1
        })
        
        # 2. Cash sales (distributed throughout month)
        cash_sale_count = min(4, max(2, target_count // 5))
        for _ in range(cash_sale_count):
            transaction_plan.append({
                "type": "cash_sale",
                "day": random.randint(1, days_in_month),
                "priority": 2
            })
        
        # 3. Credit sales (distributed throughout month, but not too late)
        credit_sale_count = min(3, max(2, target_count // 6))
        for _ in range(credit_sale_count):
            transaction_plan.append({
                "type": "credit_sale",
                "day": random.randint(1, days_in_month - 5),  # Leave time for collection
                "priority": 2
            })
        
        # 4. Collections (later in month, after credit sales)
        collection_count = min(2, max(1, credit_sale_count - 1))
        for _ in range(collection_count):
            transaction_plan.append({
                "type": "collection",
                "day": random.randint(10, days_in_month),
                "priority": 3
            })
        
        # 5. Purchases - supplies (throughout month)
        transaction_plan.append({
            "type": "purchase_supplies",
            "day": random.randint(5, days_in_month - 10),
            "priority": 2
        })
        transaction_plan.append({
            "type": "purchase_supplies",
            "day": random.randint(15, days_in_month),
            "priority": 2
        })
        
        # 6. Purchase equipment (mid-month)
        transaction_plan.append({
            "type": "purchase_equipment",
            "day": random.randint(8, days_in_month - 8),
            "priority": 2
        })
        
        # 7. Purchase on account (early-mid month)
        transaction_plan.append({
            "type": "purchase_on_account",
            "day": random.randint(5, days_in_month - 10),
            "priority": 2
        })
        
        # 8. Pay expenses - rent (early month, usually day 1-5)
        transaction_plan.append({
            "type": "pay_expense_rent",
            "day": random.randint(1, 5),
            "priority": 1
        })
        
        # 9. Pay expenses - utilities (mid-month)
        transaction_plan.append({
            "type": "pay_expense_utilities",
            "day": random.randint(10, 20),
            "priority": 2
        })
        
        # 10. Pay salaries (mid-month, usually around 15th)
        transaction_plan.append({
            "type": "pay_expense_salaries",
            "day": random.randint(12, 18),
            "priority": 1
        })
        
        # 11. Pay accounts payable (later in month)
        transaction_plan.append({
            "type": "pay_accounts_payable",
            "day": random.randint(15, days_in_month),
            "priority": 3
        })
        
        # 12. Owner withdrawal (late month)
        transaction_plan.append({
            "type": "owner_withdrawal",
            "day": random.randint(days_in_month - 7, days_in_month),
            "priority": 3
        })
        
        # Fill remaining slots with random business transactions
        remaining = target_count - len(transaction_plan) - 4  # Reserve 4 slots for adjusting entries
        if remaining > 0:
            additional_types = ["cash_sale", "credit_sale", "purchase_supplies", "collection"]
            for _ in range(remaining):
                transaction_plan.append({
                    "type": random.choice(additional_types),
                    "day": random.randint(1, days_in_month),
                    "priority": 4
                })
        
        # Add adjusting entries at the end of the month (last day)
        adjusting_entry_types = [
            "adjust_depreciation",
            "adjust_accrued_utilities",
            "adjust_accrued_salaries",
            "adjust_percentage_tax"
        ]
        for adj_type in adjusting_entry_types:
            transaction_plan.append({
                "type": adj_type,
                "day": days_in_month,  # Last day of month
                "priority": 5  # After all regular transactions
            })
        
        # Sort by day, then by priority
        transaction_plan.sort(key=lambda x: (x["day"], x["priority"]))
        
        # Generate actual transaction data
        doc_ref_counter = 10000
        accounts_payable_balance = 0.0  # Track Accounts Payable balance
        accounts_receivable_balance = 0.0  # Track Accounts Receivable balance
        
        for plan_item in transaction_plan:
            txn_type = plan_item["type"]
            txn_config = TRANSACTION_TYPES[txn_type]
            
            # Generate date
            date = datetime(year, month_num, plan_item["day"])
            
            # Generate amount - special handling for payments that depend on balances
            if txn_type == "pay_accounts_payable":
                # Payment cannot exceed Accounts Payable balance
                if accounts_payable_balance <= 0:
                    # No AP balance, skip this payment or use a minimal amount
                    # Skip by not adding to transactions
                    continue
                # Use the full balance or a portion of it (at least 50% of balance)
                max_payment = accounts_payable_balance
                min_payment = max(accounts_payable_balance * 0.5, txn_config["amount_range"][0])
                amount = round(random.uniform(min(min_payment, max_payment), max_payment), 2)
                # Update balance
                accounts_payable_balance -= amount
            elif txn_type == "collection":
                # Collection cannot exceed Accounts Receivable balance
                if accounts_receivable_balance <= 0:
                    # No AR balance, skip this collection
                    continue
                # Use the full balance or a portion of it
                max_collection = accounts_receivable_balance
                min_collection = max(accounts_receivable_balance * 0.5, txn_config["amount_range"][0])
                amount = round(random.uniform(min(min_collection, max_collection), max_collection), 2)
                # Update balance
                accounts_receivable_balance -= amount
            else:
                # Regular transaction - generate random amount
                amount = round(random.uniform(*txn_config["amount_range"]), 2)
                
                # Update tracking balances
                if txn_type == "purchase_on_account":
                    accounts_payable_balance += amount
                elif txn_type == "credit_sale":
                    accounts_receivable_balance += amount
            
            # Generate description
            description = txn_config["description"]
            if "{client_name}" in description:
                description = description.format(client_name=random.choice(CLIENT_NAMES))
            elif "{vendor_name}" in description:
                description = description.format(vendor_name=random.choice(VENDOR_NAMES))
            
            # Generate document reference
            doc_ref = doc_ref_counter
            doc_ref_counter += 1
            ext_ref = f"{txn_config['source_type'][:3].upper()}-{doc_ref}"
            
            transactions.append({
                "date": date,
                "date_str": date.strftime("%Y-%m-%d"),
                "transaction_type": txn_type,
                "source_type": txn_config["source_type"],
                "document_ref": str(doc_ref),
                "external_ref": ext_ref,
                "description": description,
                "debit_account": txn_config["debit_account"],
                "credit_account": txn_config["credit_account"],
                "amount": amount,
                "memo": f"Business transaction: {description}",
                "is_adjusting": txn_config.get("is_adjusting", False)
            })
        
        return transactions
    
    def _generate_mock_codes(self, transactions, start_progress, total):
        """Generate mock_codes (QR + Barcode PNG + TXT)"""
        files_generated = 0
        
        for i, txn in enumerate(transactions, 1):
            data = {
                "date": txn["date_str"],
                "source_type": txn["source_type"],
                "document_ref": txn["document_ref"],
                "external_ref": txn["external_ref"],
                "description": txn["description"],
                "debit_amount": txn["amount"],
                "credit_amount": txn["amount"],
                "memo": txn["memo"]
            }
            
            json_str = json.dumps(data, separators=(',', ':'))
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json_str)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.convert('RGB')
            
            qr_path = self.mock_codes_dir / f"txn_{i}_qr.png"
            qr_img.save(qr_path)
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
            
            # Save QR text
            txt_path = self.mock_codes_dir / f"txn_{i}_qr.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
            
            # Generate barcode
            try:
                barcode = Code128(txn["document_ref"], writer=ImageWriter())
                barcode_path = self.mock_codes_dir / f"txn_{i}_code128"
                barcode.save(str(barcode_path))
                
                saved_file = None
                for ext in ['.png', '.svg']:
                    test_path = barcode_path.with_suffix(ext)
                    if test_path.exists():
                        saved_file = test_path
                        break
                
                if saved_file and saved_file.suffix == '.png':
                    final_path = self.mock_codes_dir / f"txn_{i}_code128.png"
                    if saved_file != final_path:
                        saved_file.rename(final_path)
                    files_generated += 1
                    self._update_progress(start_progress + files_generated, total)
                elif saved_file:
                    from PIL import Image, ImageDraw
                    img = Image.new('RGB', (200, 100), color='white')
                    draw = ImageDraw.Draw(img)
                    draw.text((10, 40), f"BARCODE-{txn['document_ref']}", fill='black')
                    final_path = self.mock_codes_dir / f"txn_{i}_code128.png"
                    img.save(final_path)
                    saved_file.unlink()
                    files_generated += 1
                    self._update_progress(start_progress + files_generated, total)
            except Exception as e:
                self._log(f"  Warning: Failed to generate barcode {i}: {str(e)}")
                try:
                    from PIL import Image, ImageDraw
                    img = Image.new('RGB', (200, 100), color='white')
                    draw = ImageDraw.Draw(img)
                    draw.text((10, 40), f"BARCODE-{txn['document_ref']}", fill='black')
                    final_path = self.mock_codes_dir / f"txn_{i}_code128.png"
                    img.save(final_path)
                    files_generated += 1
                    self._update_progress(start_progress + files_generated, total)
                except Exception:
                    pass
            
            # Save barcode text
            barcode_txt_path = self.mock_codes_dir / f"txn_{i}_code128.txt"
            with open(barcode_txt_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
        
        return files_generated
    
    def _generate_sample_docs(self, transactions, start_progress, total):
        """Generate SampleSourceDocs (Documents + JSON)"""
        files_generated = 0
        
        for i, txn in enumerate(transactions, 1):
            date_str = txn["date_str"]
            source_type = txn["source_type"]
            doc_no = txn["document_ref"]
            description = txn["description"]
            description_clean = description.replace(" ", "_").replace("-", "_").replace(",", "")
            
            # Generate filename
            filename_base = f"{date_str}_{source_type}_{doc_no}_{description_clean}"
            ext = random.choice(DOCUMENT_EXTENSIONS.get(source_type, [".pdf"]))
            filename = filename_base + ext
            
            # Create document file
            doc_path = self.sample_docs_dir / filename
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(f"Business Document: {description}\n")
                f.write(f"Document Reference: {txn['external_ref']}\n")
                f.write(f"Date: {date_str}\n")
                f.write(f"Amount: ₱{txn['amount']:.2f}\n")
                f.write(f"Debit Account: {txn['debit_account']}\n")
                f.write(f"Credit Account: {txn['credit_account']}\n")
                if txn.get('memo'):
                    f.write(f"Memo: {txn['memo']}\n")
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
            
            # Generate JSON sidecar
            json_data = {
                "date": date_str,
                "description": description,
                "source_type": source_type,
                "document_ref": txn["external_ref"],
                "debit_account": txn["debit_account"],
                "credit_account": txn["credit_account"],
                "debit_amount": f"{txn['amount']:.2f}",
                "credit_amount": f"{txn['amount']:.2f}"
            }
            
            if txn.get('memo'):
                json_data["memo"] = txn["memo"]
            
            json_path = self.sample_docs_dir / f"{filename_base}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
        
        return files_generated
    
    def _update_progress(self, current, total):
        """Update progress bar"""
        self.progress_bar.config(value=current)
        self.progress_var.set(f"Progress: {current}/{total} files ({current*100//total}%)")
        self.root.update()
    
    def _calculate_account_balances(self, transactions):
        """Calculate ending balances for all accounts"""
        account_balances = {}
        
        for txn in transactions:
            debit_acct = txn['debit_account']
            credit_acct = txn['credit_account']
            amount = txn['amount']
            
            # Debit increases assets/expenses, decreases liabilities/equity/revenue
            if debit_acct not in account_balances:
                account_balances[debit_acct] = 0
            account_balances[debit_acct] += amount
            
            # Credit increases liabilities/equity/revenue, decreases assets/expenses
            if credit_acct not in account_balances:
                account_balances[credit_acct] = 0
            account_balances[credit_acct] -= amount
        
        return account_balances
    
    def _calculate_financial_statements(self, transactions):
        """Calculate Income Statement, Balance Sheet, and Statement of Owner's Equity"""
        balances = self._calculate_account_balances(transactions)
        
        # Get month and year for reporting period
        month_name = self.month_var.get()
        year = int(self.year_var.get())
        
        # Income Statement
        # Revenue accounts have credit balance (negative in our calculation)
        revenue_balance = balances.get("Service Income", 0)
        revenue_total = abs(revenue_balance) if revenue_balance < 0 else 0
        
        # Expense accounts have debit balance (positive in our calculation)
        expenses = {
            "Salaries & Wages": max(0, balances.get("Salaries & Wages", 0)),
            "Rent Expense": max(0, balances.get("Rent Expense", 0)),
            "Utilities Expense": max(0, balances.get("Utilities Expense", 0)),
            "Supplies Expense": max(0, balances.get("Supplies Expense", 0)),
            "Depreciation Expense": max(0, balances.get("Depreciation Expense", 0)),
            "Percentage Tax Expense": max(0, balances.get("Percentage Tax Expense", 0)),
            "Transportation Expense": max(0, balances.get("Transportation Expense", 0)),
            "PhilHealth, Pag-Ibig and SSS Contributions": max(0, balances.get("PhilHealth, Pag-Ibig and SSS Contributions", 0)),
        }
        total_expenses = sum(expenses.values())
        net_income = revenue_total - total_expenses
        
        # Balance Sheet - Assets (debit balance = positive)
        cash_balance = max(0, balances.get("Cash", 0))
        ar_balance = max(0, balances.get("Accounts Receivable", 0))
        input_tax_balance = max(0, balances.get("Input Tax", 0))
        office_equipment_balance = max(0, balances.get("Office Equipment", 0))
        # Accumulated Depreciation is a contra asset (credit balance = negative)
        acc_dep_balance = min(0, balances.get("Accumulated Depreciation", 0))
        
        # Calculate net office equipment
        office_equipment_net = office_equipment_balance + acc_dep_balance
        total_assets = cash_balance + ar_balance + input_tax_balance + max(0, office_equipment_net)
        
        assets = {
            "Cash": cash_balance,
            "Accounts Receivable": ar_balance,
            "Input Tax": input_tax_balance,
            "Office Equipment": office_equipment_balance,
            "Accumulated Depreciation": acc_dep_balance,
        }
        
        # Balance Sheet - Liabilities (credit balance = negative in our calc, so negate)
        # Note: If a liability has a debit balance (overpayment), it means more was paid than owed
        # This is an error condition that should be prevented in transaction generation
        ap_balance = balances.get("Accounts Payable", 0)
        # Accounts Payable should only show as a liability if it has a credit balance
        # If it has a debit balance (overpayment), show 0 and the imbalance will be caught
        ap_liability = max(0, -ap_balance) if ap_balance <= 0 else 0
        
        liabilities = {
            "Accounts Payable": ap_liability,
            "Utilities Payable": max(0, -balances.get("Utilities Payable", 0)),
            "Withholding Taxes Payable": max(0, -balances.get("Withholding Taxes Payable", 0)),
            "SSS, PhilHealth, and Pag-Ibig Payable": max(0, -balances.get("SSS, PhilHealth, and Pag-Ibig Payable", 0)),
            "Expanded Withholding Tax Payable": max(0, -balances.get("Expanded Withholding Tax Payable", 0)),
            "Accrued Percentage Tax Payable": max(0, -balances.get("Accrued Percentage Tax Payable", 0)),
        }
        total_liabilities = sum(liabilities.values())
        
        # If Accounts Payable was overpaid (debit balance), add it to assets as prepaid
        # This ensures the balance sheet balances correctly
        if ap_balance > 0:
            prepaid_ap = ap_balance
            total_assets += prepaid_ap
            # Add to assets dictionary for reporting
            assets["Prepaid (AP Overpayment)"] = prepaid_ap
        
        # Balance Sheet - Equity (credit balance = negative in our calc, so negate)
        owner_capital_balance = balances.get("Owner's Capital", 0)
        owner_capital = max(0, -owner_capital_balance) if owner_capital_balance < 0 else 0
        owner_drawings_balance = balances.get("Owner's Drawings", 0)
        owner_drawings = max(0, owner_drawings_balance)
        
        # Calculate ending equity
        owner_equity = owner_capital - owner_drawings + net_income
        total_liabilities_equity = total_liabilities + owner_equity
        
        # Statement of Owner's Equity
        # Beginning capital = ending capital - net income + drawings - additions
        # For simplicity, assume beginning capital is owner_capital (before any additions)
        beginning_capital = owner_capital
        # Calculate additions (investments during the period)
        additions = 0
        for txn in transactions:
            if txn.get('transaction_type') == 'owner_investment':
                additions += txn['amount']
        if additions > 0:
            beginning_capital = max(0, owner_capital - additions)
        
        return {
            "period": f"{month_name} {year}",
            "income_statement": {
                "revenue": {"Service Income": revenue_total},
                "total_revenue": revenue_total,
                "expenses": expenses,
                "total_expenses": total_expenses,
                "net_income": net_income,
            },
            "balance_sheet": {
                "assets": assets,
                "office_equipment_net": office_equipment_net,
                "total_assets": total_assets,
                "liabilities": liabilities,
                "total_liabilities": total_liabilities,
                "equity": {
                    "Owner's Capital": owner_capital,
                    "Owner's Drawings": owner_drawings,
                    "Net Income": net_income,
                    "Total Owner's Equity": owner_equity,
                },
                "total_liabilities_equity": total_liabilities_equity,
            },
            "statement_of_equity": {
                "beginning_capital": beginning_capital,
                "additions": additions,
                "net_income": net_income,
                "drawings": owner_drawings,
                "ending_capital": owner_equity,
            },
        }


def main():
    try:
        root = tk.Tk()
        app = BusinessTransactionGenerator(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()

