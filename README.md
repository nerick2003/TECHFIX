# TechFix Accounting System

A comprehensive desktop accounting practice application with SQLite storage and Tkinter GUI. TechFix implements the complete accounting cycle with double-entry bookkeeping, financial statement generation, and document management.

## Purpose

TechFix is designed as a desktop accounting practice application that provides:
- Complete accounting cycle implementation (all 10 steps)
- Double-entry bookkeeping with validation
- Financial statement generation (Income Statement, Balance Sheet, Cash Flow)
- Source document scanning and management
- Export capabilities (Excel, CSV, PDF)
- Responsive UI for different screen sizes

## Project Structure

```
TECHFIX/
├── TECHFIX/
│   ├── main.py                 # Application entry point
│   ├── techfix/
│   │   ├── __init__.py
│   │   ├── __main__.py         # CLI entry point
│   │   ├── db.py               # Database operations and schema
│   │   ├── accounting.py       # Accounting logic and calculations
│   │   └── gui.py              # Tkinter GUI implementation
│   ├── tests/                  # Test suite and utilities
│   └── docs/                   # Additional documentation
├── generators/                 # Mock data generation tools
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Package configuration
└── README.md                   # This file
```

## Features

### Core Accounting Features

- **Complete Accounting Cycle**: Implements all 10 steps:
  1. Analyze transactions
  2. Journalize transactions
  3. Post to ledger
  4. Prepare unadjusted trial balance
  5. Record adjusting entries
  6. Prepare adjusted trial balance
  7. Prepare financial statements
  8. Record closing entries
  9. Prepare post-closing trial balance
  10. Schedule reversing entries

- **Transaction Management**:
  - Journal entries with debit/credit validation
  - Entry status tracking (draft, posted)
  - Entry types (adjusting, closing, reversing)
  - Source document attachments
  - Document references and external references
  - Memo/notes support

- **Account Management**:
  - Chart of accounts with account types
  - Account codes and names
  - Normal side tracking (debit/credit)
  - Permanent vs temporary account classification
  - Active/inactive account status
  - Contra accounts (contra asset, contra revenue)

- **Trial Balance**:
  - Unadjusted trial balance
  - Adjusted trial balance
  - Post-closing trial balance
  - Trial balance snapshots
  - Date range and period filtering

- **Financial Statements**:
  - Income Statement
  - Balance Sheet (with balance validation)
  - Cash Flow Statement
  - All statements support date range filtering

### User Interface Features

- **Responsive Design**: Adapts to different screen sizes and aspect ratios (PC monitors, laptops)
- **Global Action Button**: Bottom-left sidebar button opens an aspect ratio chooser window to quickly resize the main window to preset dimensions:
  - Laptop 16:9
  - Desktop 16:9
  - Square 4:3
  - Tall/coding split
- **Adaptive Sidebar**: Automatically adjusts width based on window aspect ratio for optimal layout on wide vs. tall screens
- **Theme Support**: Light/Dark theme support with system theme detection
- **Multiple Themes**: Blue, Dark, Green, Purple, Red, Orange, Teal, Pink, Amber themes available
- **Fullscreen Support**: Press F11 to toggle fullscreen mode, Escape to exit

### Application Tabs

The application includes the following main tabs:

1. **Transactions** - Enter and manage journal entries
2. **Journal** - View all journal entries
3. **Ledger** - View account ledgers
4. **Trial Balance** - Generate trial balances
5. **Adjusting** - Record adjusting entries
6. **Financial Statements** - Generate Income Statement, Balance Sheet, and Cash Flow Statement
7. **Closing** - Record closing entries
8. **Post-Closing** - View post-closing trial balance
9. **Export** - Export data to Excel, CSV, or PDF formats
10. **Audit Log** - View accounting cycle status and audit trail
11. **How to Use?** - Help and documentation

### Document Management

- **Source Document Scanning**: Scan QR codes and barcodes from source documents
- **Image Processing**: Support for PNG, JPG, and other image formats
- **Document Attachments**: Attach source documents to transactions
- **Barcode/QR Code Generation**: Generate barcodes and QR codes for documents

### Export Capabilities

- **Excel Export**: Export transactions, trial balances, and financial statements to Excel
- **CSV Export**: Export data to CSV format
- **PDF Export**: Generate PDF reports including:
  - Financial statements
  - Trial balances
  - Documentation overview

## Setup

### Prerequisites

- Python 3.10 or higher
- Windows, macOS, or Linux

### Installation Steps

1. **Navigate to the project directory:**
   ```powershell
   cd "C:\Users\neric\Desktop\FINAL REVISION MAYBE\TECHFIX"
   ```

2. **Create a virtual environment (recommended):**
   ```powershell
   python -m venv .venv
   ```

3. **Activate the virtual environment:**
   ```powershell
   .\.venv\Scripts\activate
   ```
   (You should see `(.venv)` in your terminal prompt when activated)

   On Linux/macOS:
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies from requirements.txt:**
   ```powershell
   pip install -r requirements.txt
   ```
   
   This will install:
   - **Pillow** (≥10.0.0) - Image processing
   - **python-barcode** (≥0.15.1) - Barcode generation
   - **qrcode** (≥7.4.2) - QR code generation
   - **opencv-python** (≥4.9.0) - Image processing and scanning
   - **pyzbar** (≥0.1.9) - Barcode/QR code scanning
   - **openpyxl** (≥3.1.0) - Excel export
   - **reportlab** (≥4.0.0) - PDF generation

5. **Verify installation (optional):**
   ```powershell
   pip list
   ```
   You should see all the packages listed above installed in your virtual environment.

## Running the Application

1. **Make sure your virtual environment is activated** (if you created one):
   ```powershell
   .\.venv\Scripts\activate
   ```

2. **Start the app:**
   ```powershell
   python TECHFIX\main.py
   ```
   
   Or from the project root:
   ```powershell
   python TECHFIX\TECHFIX\main.py
   ```

3. **Optional:** Set data directory via environment variable `TECHFIX_DATA_DIR` to change where `techfix.sqlite3` is stored:
   ```powershell
   $env:TECHFIX_DATA_DIR="C:\path\to\your\data"
   python TECHFIX\main.py
   ```
   
   On Linux/macOS:
   ```bash
   export TECHFIX_DATA_DIR="/path/to/your/data"
   python TECHFIX/main.py
   ```

## Testing

Run the test suite:
```powershell
python -m unittest discover -s TECHFIX\TECHFIX\tests -p "test_*.py" -v
```

## Mock Data Generation

The `generators/` directory contains tools for generating mock data:

- **generate_mock_data.py**: GUI application to generate large quantities of mock data files
- **generate_business_transactions.py**: Generate business transaction data

See `generators/GENERATOR_README.md` for detailed usage instructions.

## Important Notes

- **First Launch**: The application automatically seeds a chart of accounts and creates a default accounting period if none exists
- **Data Storage**: By default, `techfix.sqlite3` is stored in the project root. Use `TECHFIX_DATA_DIR` environment variable to change the location
- **Preferences**: Window size and theme preferences are saved and restored on next launch
- **Export Paths**: Excel and CSV exports write to the chosen output path, creating parent folders as needed
- **Balance Validation**: The Balance Sheet includes automatic balance validation (should equal ₱0.00)
- **Entry Status**: Only posted entries appear in financial statements. Use "Record & Post" instead of "Save Draft" for entries to be included

## Keyboard Shortcuts

- **F11**: Toggle fullscreen mode
- **Escape**: Exit fullscreen mode

## Documentation

- **User Guide**: See `TECHFIX/TECHFIX/tests/USER_GUIDE.md` for detailed usage instructions
- **Quick Start**: See `TECHFIX/TECHFIX/tests/QUICK_START_GUIDE.md` for a 5-minute getting started guide
- **Export Documentation**: Use the Export tab → "Export Documentation (PDF)" to generate a program overview PDF
- **Accounting Cycle**: The application implements all 10 steps of the standard accounting cycle (see `TECHFIX/TECHFIX/ISSUES AND FIXES/ACCOUNTING_CYCLE_AUDIT.md`)

## Package Installation

The project includes `pyproject.toml` for package installation. After installation, you can run:

```powershell
techfix
```

This uses the CLI entry point defined in `techfix.__main__`.

## Next Steps / Future Improvements

- Add `.gitignore` for `*.sqlite3`, `__pycache__/`, and local artifacts
- Continue adding type hints across modules and enable static type checking
- Enhanced error handling and user feedback
- Additional export formats
- Multi-user support
- Cloud backup integration

## License

[Add your license information here]

## Support

For issues, questions, or contributions, please refer to the project documentation or create an issue in the project repository.
