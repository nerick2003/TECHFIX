"""
Mock Data Generator for TechFix
Generates mock_codes, mock_codes_jpg, and SampleSourceDocs files
"""

import os
import json
import random
import io
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from pathlib import Path
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image

# Account names from chart of accounts
ASSET_ACCOUNTS = [
    "Cash", "Accounts Receivable", "Supplies", "Prepaid Rent", "Equipment"
]
LIABILITY_ACCOUNTS = [
    "Accounts Payable", "Utilities Payable", "Salaries Payable", "Unearned Revenue"
]
EQUITY_ACCOUNTS = [
    "Owner's Capital", "Owner's Drawings"
]
REVENUE_ACCOUNTS = [
    "Service Revenue", "Sales Revenue"
]
EXPENSE_ACCOUNTS = [
    "Rent Expense", "Salaries Expense", "Supplies Expense", 
    "Depreciation Expense", "Utilities Expense", "Cost of Goods Sold"
]

ALL_ACCOUNTS = ASSET_ACCOUNTS + LIABILITY_ACCOUNTS + EQUITY_ACCOUNTS + REVENUE_ACCOUNTS + EXPENSE_ACCOUNTS

SOURCE_TYPES = ["Invoice", "Receipt", "Bank", "Adjust", "Payroll", "Other"]

DESCRIPTION_TEMPLATES = {
    "Invoice": [
        "Client services - {month}",
        "Consulting services",
        "Professional fees",
        "Project completion",
        "Monthly retainer",
        "Service contract",
    ],
    "Receipt": [
        "Office supplies",
        "Utilities payment",
        "Office rent",
        "Equipment purchase",
        "Maintenance services",
        "Miscellaneous expenses",
    ],
    "Bank": [
        "Bank deposit",
        "Bank withdrawal",
        "Transfer",
        "Payment received",
        "Fee charged",
    ],
    "Adjust": [
        "Supplies adjustment",
        "Accrual adjustment",
        "Depreciation adjustment",
        "Prepaid adjustment",
    ],
    "Payroll": [
        "Payroll wages",
        "Employee salaries",
        "Payroll taxes",
        "Benefits payment",
    ],
    "Other": [
        "Miscellaneous transaction",
        "General entry",
        "Other transaction",
    ],
}

DOCUMENT_EXTENSIONS = {
    "Invoice": [".pdf", ".doc", ".docx"],
    "Receipt": [".pdf", ".jpg", ".png"],
    "Bank": [".pdf", ".xls", ".xlsx"],
    "Adjust": [".pdf", ".json"],
    "Payroll": [".pdf", ".docx", ".xlsx"],
    "Other": [".pdf", ".txt"],
}


class MockDataGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Mock Data Generator for TechFix")
        # Set a larger initial size to ensure all buttons are visible
        self.root.geometry("800x650")
        # Prevent window from being resized too small
        self.root.minsize(750, 600)
        # Prevent window from being resized too small
        self.root.minsize(700, 600)
        
        # Create output directories
        self.base_dir = Path(__file__).parent
        self.mock_codes_dir = self.base_dir / "mock_codes"
        self.mock_codes_jpg_dir = self.base_dir / "mock_codes_jpg"
        self.sample_docs_dir = self.base_dir / "SampleSourceDocs"
        
        self._create_directories()
        self._build_ui()
        
    def _create_directories(self):
        """Create output directories if they don't exist"""
        self.mock_codes_dir.mkdir(exist_ok=True)
        self.mock_codes_jpg_dir.mkdir(exist_ok=True)
        self.sample_docs_dir.mkdir(exist_ok=True)
    
    def _build_ui(self):
        """Build the GUI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Mock Data Generator", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Number of files input
        count_frame = ttk.Frame(main_frame)
        count_frame.pack(fill=tk.X, pady=10)
        
        # Mode selection
        mode_frame = ttk.Frame(count_frame)
        mode_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        self.count_mode = tk.StringVar(value="transactions")
        ttk.Radiobutton(
            mode_frame, 
            text="Transactions", 
            variable=self.count_mode, 
            value="transactions"
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            mode_frame, 
            text="Total Files", 
            variable=self.count_mode, 
            value="files"
        ).pack(side=tk.LEFT)
        
        ttk.Label(count_frame, text="Count:").pack(side=tk.LEFT, padx=(0, 10))
        self.count_var = tk.StringVar(value="100000")
        count_entry = ttk.Entry(count_frame, textvariable=self.count_var, width=15)
        count_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Preview label showing total files or transactions
        self.preview_var = tk.StringVar(value="")
        preview_label = ttk.Label(count_frame, textvariable=self.preview_var, foreground="gray")
        preview_label.pack(side=tk.LEFT)
        
        # Create checkbox variables BEFORE using them in update_preview
        self.generate_mock_codes = tk.BooleanVar(value=True)
        self.generate_mock_codes_jpg = tk.BooleanVar(value=True)
        self.generate_sample_docs = tk.BooleanVar(value=True)
        
        # Update preview when count changes
        def update_preview(*args):
            try:
                count = int(self.count_var.get()) if self.count_var.get() else 0
                if count > 0:
                    mode = self.count_mode.get()
                    if mode == "transactions":
                        # Calculate total files from transactions
                        total = 0
                        if self.generate_mock_codes.get():
                            total += count * 4  # QR PNG, QR TXT, Barcode PNG, Barcode TXT
                        if self.generate_mock_codes_jpg.get():
                            total += count
                        if self.generate_sample_docs.get():
                            total += count * 2  # Document + JSON
                        self.preview_var.set(f"→ {total:,} total files")
                    else:
                        # Calculate transactions from total files
                        files_per_txn = 0
                        if self.generate_mock_codes.get():
                            files_per_txn += 4
                        if self.generate_mock_codes_jpg.get():
                            files_per_txn += 1
                        if self.generate_sample_docs.get():
                            files_per_txn += 2
                        if files_per_txn > 0:
                            transactions = count // files_per_txn
                            remainder = count % files_per_txn
                            if remainder == 0:
                                self.preview_var.set(f"→ {transactions:,} transactions")
                            else:
                                self.preview_var.set(f"→ ~{transactions:,} transactions ({count} files)")
                        else:
                            self.preview_var.set("→ Select at least one type")
                else:
                    self.preview_var.set("")
            except ValueError:
                self.preview_var.set("(Invalid number)")
            except AttributeError:
                # Variables not created yet
                pass
        
        # Use trace_add for Tcl 9 compatibility
        try:
            self.count_var.trace_add('write', update_preview)
            self.count_mode.trace_add('write', update_preview)
            self.generate_mock_codes.trace_add('write', update_preview)
            self.generate_mock_codes_jpg.trace_add('write', update_preview)
            self.generate_sample_docs.trace_add('write', update_preview)
        except AttributeError:
            # Fallback for older Tcl versions
            self.count_var.trace('w', update_preview)
            self.count_mode.trace('w', update_preview)
            self.generate_mock_codes.trace('w', update_preview)
            self.generate_mock_codes_jpg.trace('w', update_preview)
            self.generate_sample_docs.trace('w', update_preview)
        
        update_preview()  # Initial update
        
        # Month and Year selection
        date_frame = ttk.LabelFrame(main_frame, text="Date Range", padding="10")
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
        
        # Checkboxes for what to generate
        options_frame = ttk.LabelFrame(main_frame, text="Generate", padding="10")
        options_frame.pack(fill=tk.X, pady=10)
        
        ttk.Checkbutton(
            options_frame, 
            text="mock_codes (QR + Barcode PNG + TXT)", 
            variable=self.generate_mock_codes
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Checkbutton(
            options_frame, 
            text="mock_codes_jpg (Barcode JPG)", 
            variable=self.generate_mock_codes_jpg
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
            height=5,  # Reduced height to make buttons visible
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_scroll_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Generate button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 10))  # Reduced top padding
        
        self.generate_button = ttk.Button(
            button_frame,
            text="Generate Files",
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
            if count <= 0:
                messagebox.showerror("Error", "Count must be greater than 0")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid count value")
            return
        
        if not any([
            self.generate_mock_codes.get(),
            self.generate_mock_codes_jpg.get(),
            self.generate_sample_docs.get()
        ]):
            messagebox.showwarning("Warning", "Please select at least one type to generate")
            return
        
        self.generate_button.config(state=tk.DISABLED)
        self._clear_status()
        
        try:
            mode = self.count_mode.get()
            
            # Calculate how many transactions to generate
            if mode == "transactions":
                transactions = count
            else:  # mode == "files"
                # Calculate files per transaction
                files_per_txn = 0
                if self.generate_mock_codes.get():
                    files_per_txn += 4
                if self.generate_mock_codes_jpg.get():
                    files_per_txn += 1
                if self.generate_sample_docs.get():
                    files_per_txn += 2
                
                if files_per_txn == 0:
                    messagebox.showerror("Error", "Please select at least one type to generate")
                    self.generate_button.config(state=tk.NORMAL)
                    return
                
                # Calculate transactions needed to get approximately the requested number of files
                transactions = max(1, count // files_per_txn)
                # If there's a remainder, add one more transaction to ensure we get at least the requested count
                if count % files_per_txn > 0:
                    transactions += 1
            
            # Calculate total files that will be generated
            total_files = 0
            if self.generate_mock_codes.get():
                total_files += transactions * 4  # QR PNG, QR TXT, Barcode PNG, Barcode TXT
            if self.generate_mock_codes_jpg.get():
                total_files += transactions
            if self.generate_sample_docs.get():
                total_files += transactions * 2  # Document + JSON
            
            self.progress_bar.config(maximum=total_files, value=0)
            files_generated = 0
            
            if self.generate_mock_codes.get():
                self._log(f"Generating {transactions} mock_codes transactions ({transactions * 4} files)...")
                files_generated += self._generate_mock_codes(transactions, files_generated, total_files)
            
            if self.generate_mock_codes_jpg.get():
                self._log(f"Generating {transactions} mock_codes_jpg transactions ({transactions} files)...")
                files_generated += self._generate_mock_codes_jpg(transactions, files_generated, total_files)
            
            if self.generate_sample_docs.get():
                self._log(f"Generating {transactions} SampleSourceDocs transactions ({transactions * 2} files)...")
                files_generated += self._generate_sample_docs(transactions, files_generated, total_files)
            
            self.progress_var.set("Complete!")
            self._log(f"\n✓ Generated {files_generated} files successfully!")
            messagebox.showinfo("Success", f"Generated {files_generated} files successfully!")
            
        except Exception as e:
            self._log(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Generation failed: {str(e)}")
        finally:
            self.generate_button.config(state=tk.NORMAL)
            self.progress_bar.config(value=0)
    
    def _generate_mock_codes(self, count, start_progress, total):
        """Generate mock_codes (QR + Barcode PNG + TXT)"""
        files_generated = 0
        
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
        
        for i in range(1, count + 1):
            # Generate transaction data - random day within selected month
            day = random.randint(1, days_in_month)
            date = datetime(year, month_num, day)
            source_type = random.choice(SOURCE_TYPES)
            doc_ref = random.randint(10000, 99999)
            ext_ref = f"{source_type[:3].upper()}-{doc_ref}"
            
            description = random.choice(DESCRIPTION_TEMPLATES[source_type]).format(
                month=date.strftime("%B")
            )
            amount = round(random.uniform(10.0, 5000.0), 2)
            
            # Select appropriate accounts based on source type
            if source_type == "Invoice":
                debit_acct = "Accounts Receivable"
                credit_acct = random.choice(REVENUE_ACCOUNTS)
            elif source_type == "Receipt":
                debit_acct = random.choice(EXPENSE_ACCOUNTS)
                credit_acct = "Cash"
            elif source_type == "Bank":
                if random.choice([True, False]):
                    debit_acct = "Cash"
                    credit_acct = random.choice(REVENUE_ACCOUNTS)
                else:
                    debit_acct = random.choice(EXPENSE_ACCOUNTS)
                    credit_acct = "Cash"
            elif source_type == "Payroll":
                debit_acct = "Salaries Expense"
                credit_acct = "Cash"
            else:
                debit_acct = random.choice(ALL_ACCOUNTS)
                credit_acct = random.choice(ALL_ACCOUNTS)
            
            data = {
                "date": date.strftime("%Y-%m-%d"),
                "source_type": source_type,
                "document_ref": str(doc_ref),
                "external_ref": ext_ref,
                "description": description,
                "debit_amount": amount,
                "credit_amount": amount,
                "memo": f"Transaction {i}"
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
            with open(txt_path, 'w') as f:
                f.write(json_str)
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
            
            # Generate barcode
            try:
                barcode = Code128(str(doc_ref), writer=ImageWriter())
                barcode_path = self.mock_codes_dir / f"txn_{i}_code128"
                # Save without extension - library adds it
                barcode.save(str(barcode_path))
                # Find the actual saved file (library adds .png extension)
                saved_file = None
                for ext in ['.png', '.svg']:
                    test_path = barcode_path.with_suffix(ext)
                    if test_path.exists():
                        saved_file = test_path
                        break
                # If we got a file, ensure it's named correctly
                if saved_file and saved_file.suffix == '.png':
                    final_path = self.mock_codes_dir / f"txn_{i}_code128.png"
                    if saved_file != final_path:
                        saved_file.rename(final_path)
                    files_generated += 1
                    self._update_progress(start_progress + files_generated, total)
                elif saved_file:
                    # SVG not supported, create placeholder
                    self._log(f"  Warning: SVG barcode not supported for {i}, creating placeholder")
                    from PIL import Image, ImageDraw
                    img = Image.new('RGB', (200, 100), color='white')
                    draw = ImageDraw.Draw(img)
                    draw.text((10, 40), f"BARCODE-{doc_ref}", fill='black')
                    final_path = self.mock_codes_dir / f"txn_{i}_code128.png"
                    img.save(final_path)
                    saved_file.unlink()
                    files_generated += 1
                    self._update_progress(start_progress + files_generated, total)
            except Exception as e:
                self._log(f"  Warning: Failed to generate barcode {i}: {str(e)}")
                # Create a placeholder image instead
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    img = Image.new('RGB', (200, 100), color='white')
                    draw = ImageDraw.Draw(img)
                    draw.text((10, 40), f"BARCODE-{doc_ref}", fill='black')
                    final_path = self.mock_codes_dir / f"txn_{i}_code128.png"
                    img.save(final_path)
                    files_generated += 1
                    self._update_progress(start_progress + files_generated, total)
                except Exception:
                    pass
            
            # Save barcode text
            barcode_txt_path = self.mock_codes_dir / f"txn_{i}_code128.txt"
            with open(barcode_txt_path, 'w') as f:
                f.write(json_str)
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
            
            if i % max(1, count // 100) == 0 or i == count:
                self._log(f"  Generated {i}/{count} mock_codes...")
        
        return files_generated
    
    def _generate_mock_codes_jpg(self, count, start_progress, total):
        """Generate mock_codes_jpg (Barcode JPG)"""
        files_generated = 0
        
        for i in range(1, count + 1):
            doc_ref = random.randint(10000, 99999)
            
            # Generate barcode
            try:
                barcode = Code128(str(doc_ref), writer=ImageWriter())
                temp_path = self.mock_codes_jpg_dir / f"barcode_{i}_temp"
                barcode.save(str(temp_path))
                
                # Convert to JPG
                # The barcode library saves as PNG, so we need to find the actual file
                possible_extensions = ['.png', '.svg']
                img_path = None
                for ext in possible_extensions:
                    test_path = temp_path.with_suffix(ext)
                    if test_path.exists():
                        img_path = test_path
                        break
                
                if img_path and img_path.exists():
                    if img_path.suffix == '.png':
                        img = Image.open(img_path)
                        img = img.convert('RGB')
                        jpg_path = self.mock_codes_jpg_dir / f"barcode_{i:05d}.jpg"
                        img.save(jpg_path, 'JPEG', quality=95)
                        img_path.unlink()  # Delete temporary file
                        files_generated += 1
                        self._update_progress(start_progress + files_generated, total)
                    elif img_path.suffix == '.svg':
                        # SVG not supported, create placeholder
                        img = Image.new('RGB', (200, 100), color='white')
                        from PIL import ImageDraw
                        draw = ImageDraw.Draw(img)
                        draw.text((10, 40), f"BARCODE-{doc_ref}", fill='black')
                        jpg_path = self.mock_codes_jpg_dir / f"barcode_{i:05d}.jpg"
                        img.save(jpg_path, 'JPEG', quality=95)
                        img_path.unlink()
                        files_generated += 1
                        self._update_progress(start_progress + files_generated, total)
            except Exception as e:
                self._log(f"  Warning: Failed to generate barcode JPG {i}: {str(e)}")
                # Create a placeholder image instead
                try:
                    img = Image.new('RGB', (200, 100), color='white')
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(img)
                    draw.text((10, 40), f"BARCODE-{doc_ref}", fill='black')
                    jpg_path = self.mock_codes_jpg_dir / f"barcode_{i:05d}.jpg"
                    img.save(jpg_path, 'JPEG', quality=95)
                    files_generated += 1
                    self._update_progress(start_progress + files_generated, total)
                except Exception:
                    pass
            
            if i % max(1, count // 100) == 0 or i == count:
                self._log(f"  Generated {i}/{count} mock_codes_jpg...")
        
        return files_generated
    
    def _generate_sample_docs(self, count, start_progress, total):
        """Generate SampleSourceDocs (Documents + JSON)"""
        files_generated = 0
        
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
        
        for i in range(1, count + 1):
            # Generate date - random day within selected month
            day = random.randint(1, days_in_month)
            date = datetime(year, month_num, day)
            date_str = date.strftime("%Y-%m-%d")
            
            # Generate source type and document number
            source_type = random.choice(SOURCE_TYPES)
            doc_no = random.randint(10000, 99999)
            
            # Generate description
            desc_template = random.choice(DESCRIPTION_TEMPLATES[source_type])
            description = desc_template.format(month=date.strftime("%B"))
            description_clean = description.replace(" ", "_").replace("-", "_")
            
            # Generate amount
            amount = round(random.uniform(10.0, 5000.0), 2)
            
            # Select appropriate accounts
            if source_type == "Invoice":
                debit_acct = "Accounts Receivable"
                credit_acct = random.choice(REVENUE_ACCOUNTS)
                doc_ref = f"INV-{doc_no}"
            elif source_type == "Receipt":
                debit_acct = random.choice(EXPENSE_ACCOUNTS)
                credit_acct = "Cash"
                doc_ref = f"RCP-{doc_no}"
            elif source_type == "Bank":
                if random.choice([True, False]):
                    debit_acct = "Cash"
                    credit_acct = random.choice(REVENUE_ACCOUNTS)
                else:
                    debit_acct = random.choice(EXPENSE_ACCOUNTS)
                    credit_acct = "Cash"
                doc_ref = f"BANK-{doc_no}"
            elif source_type == "Payroll":
                debit_acct = "Salaries Expense"
                credit_acct = "Cash"
                doc_ref = f"PAY-{doc_no}"
            elif source_type == "Adjust":
                debit_acct = random.choice(EXPENSE_ACCOUNTS)
                credit_acct = random.choice(ASSET_ACCOUNTS + LIABILITY_ACCOUNTS)
                doc_ref = f"ADJ-{doc_no}"
            else:
                debit_acct = random.choice(ALL_ACCOUNTS)
                credit_acct = random.choice(ALL_ACCOUNTS)
                doc_ref = f"OTH-{doc_no}"
            
            # Generate filename
            filename_base = f"{date_str}_{source_type}_{doc_no}_{description_clean}"
            ext = random.choice(DOCUMENT_EXTENSIONS[source_type])
            filename = filename_base + ext
            
            # Create a dummy document file (empty file with proper extension)
            doc_path = self.sample_docs_dir / filename
            with open(doc_path, 'w') as f:
                f.write(f"Mock document for {description}\n")
                f.write(f"Document Reference: {doc_ref}\n")
                f.write(f"Date: {date_str}\n")
                f.write(f"Amount: ${amount:.2f}\n")
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
            
            # Generate JSON sidecar
            json_data = {
                "date": date_str,
                "description": description,
                "source_type": source_type,
                "document_ref": doc_ref,
                "debit_account": debit_acct,
                "credit_account": credit_acct,
                "debit_amount": f"{amount:.2f}",
                "credit_amount": f"{amount:.2f}"
            }
            
            # Add memo sometimes
            if random.choice([True, False]):
                json_data["memo"] = f"Transaction {i} - {description}"
            
            json_path = self.sample_docs_dir / f"{filename_base}.json"
            with open(json_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            files_generated += 1
            self._update_progress(start_progress + files_generated, total)
            
            if i % max(1, count // 100) == 0 or i == count:
                self._log(f"  Generated {i}/{count} SampleSourceDocs...")
        
        return files_generated
    
    def _update_progress(self, current, total):
        """Update progress bar"""
        self.progress_bar.config(value=current)
        self.progress_var.set(f"Progress: {current}/{total} files ({current*100//total}%)")
        self.root.update()


def main():
    try:
        root = tk.Tk()
        app = MockDataGenerator(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()

