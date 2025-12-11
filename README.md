# TechFix Accounting System

A comprehensive desktop accounting practice application with SQLite storage and Tkinter GUI. TechFix implements the complete accounting cycle with double-entry bookkeeping, financial statement generation, and document management.

## Purpose

TechFix is designed as a desktop accounting practice application that provides:
- Complete accounting cycle implementation (all 10 steps)
- Double-entry bookkeeping with validation
- Financial statement generation (Income Statement, Balance Sheet, Cash Flow)
- Source document scanning and management
- Export capabilities (Excel, CSV, PDF)
- User authentication and security
- Data backup and restore
- Responsive UI for different screen sizes

## Project Structure

```
TECHFIX/
├── techfix/
│   ├── main.py                 # Application entry point
│   ├── techfix/
│   │   ├── __init__.py
│   │   ├── __main__.py         # CLI entry point
│   │   ├── db.py               # Database operations and schema
│   │   ├── accounting.py       # Accounting logic and calculations
│   │   ├── gui.py              # Tkinter GUI implementation
│   │   ├── auth.py             # Authentication and security
│   │   ├── backup.py           # Backup and restore functionality
│   │   ├── search.py           # Search and filtering
│   │   ├── analytics.py        # Analytics and dashboard
│   │   ├── import_data.py      # Data import functionality
│   │   ├── undo.py             # Undo/redo operations
│   │   ├── validation.py       # Input validation
│   │   └── notifications.py    # Notification system
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

### Security & Authentication

- **User Authentication**: Login system with password protection
- **Password Management**: Secure password hashing (bcrypt when available)
- **Session Management**: Automatic session timeout (8-hour default)
- **Data Encryption**: Optional encryption support for sensitive data

### Data Management

- **Backup & Restore**: Create and restore database backups
- **Data Import**: Import transactions from Excel (.xlsx, .xls) and CSV files
- **Undo/Redo**: Undo and redo operations for data entry
- **Search & Filter**: Global search across all data with advanced filtering

### Analytics & Reporting

- **Dashboard**: View key financial metrics and overview
- **Financial Metrics**: Real-time calculation of key performance indicators
- **Audit Log**: Track accounting cycle status and changes

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
   cd "C:\Users\neric\Desktop\TECHFIX"
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

5. **Install optional dependencies (recommended for enhanced security):**
   ```powershell
   pip install bcrypt cryptography pandas
   ```
   
   Optional packages:
   - **bcrypt** (≥4.0.0) - Enhanced password hashing
   - **cryptography** (≥41.0.0) - Data encryption support
   - **pandas** (≥2.0.0) - Required for data import feature

6. **Verify installation (optional):**
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
   python techfix\main.py
   ```
   
   Or use the package entry point (after installation):
   ```powershell
   techfix
   ```

3. **Optional:** Set data directory via environment variable `TECHFIX_DATA_DIR` to change where `techfix.sqlite3` is stored:
   ```powershell
   $env:TECHFIX_DATA_DIR="C:\path\to\your\data"
   python techfix\main.py
   ```
   
   On Linux/macOS:
   ```bash
   export TECHFIX_DATA_DIR="/path/to/your/data"
   python techfix/main.py
   ```

4. **First Launch:**
   - Default admin credentials: username `admin`, password `admin`
   - You will be prompted to change the password on first login
   - The application will automatically create the database and seed initial data

## Testing

Run the test suite:
```powershell
python -m unittest discover -s techfix\tests -p "test_*.py" -v
```

Or run individual test files:
```powershell
python techfix\tests\test_accounting_cycle.py
python techfix\tests\test_techfix.py
```

## Mock Data Generation

The `generators/` directory contains tools for generating mock data:

- **generate_mock_data.py**: GUI application to generate large quantities of mock data files
- **generate_business_transactions.py**: Generate business transaction data

See `generators/GENERATOR_README.md` for detailed usage instructions.

## Important Notes

- **First Launch**: 
  - Default admin credentials: username `admin`, password `admin`
  - The application automatically seeds a chart of accounts and creates a default accounting period if none exists
  - You will be prompted to change the password on first login
  
- **Data Storage**: 
  - By default, `techfix.sqlite3` is stored in the project root
  - Use `TECHFIX_DATA_DIR` environment variable to change the location
  - Backups are stored in `backups/` directory relative to the database location
  
- **Preferences**: 
  - Window size and theme preferences are saved and restored on next launch
  - Session timeout is set to 8 hours by default
  
- **Export Paths**: 
  - Excel and CSV exports write to the chosen output path, creating parent folders as needed
  - PDF exports are generated on-demand
  
- **Balance Validation**: 
  - The Balance Sheet includes automatic balance validation (should equal ₱0.00)
  - All double-entry transactions are validated before posting
  
- **Entry Status**: 
  - Only posted entries appear in financial statements
  - Use "Record & Post" instead of "Save Draft" for entries to be included in reports
  - Draft entries can be edited before posting

## Keyboard Shortcuts

- **F11**: Toggle fullscreen mode
- **Escape**: Exit fullscreen mode
- **Ctrl+Z**: Undo last operation
- **Ctrl+Y**: Redo operation
- **Ctrl+F**: Open search dialog
- **Ctrl+D**: Open dashboard
- **Ctrl+I**: Import data
- **Ctrl+1-0**: Navigate to tabs (1-10)

## Documentation

- **User Guide**: See `techfix/tests/USER_GUIDE.md` for detailed usage instructions
- **Quick Start**: See `techfix/tests/QUICK_START_GUIDE.md` for a 5-minute getting started guide
- **Features Access**: See `techfix/ISSUES AND FIXES/FEATURES_ACCESS.md` for how to access each feature
- **Export Documentation**: Use the Export tab → "Export Documentation (PDF)" to generate a program overview PDF
- **Accounting Cycle**: The application implements all 10 steps of the standard accounting cycle (see `techfix/ISSUES AND FIXES/ACCOUNTING_CYCLE_AUDIT.md`)
- **Reversing Schedule**: See `techfix/docs/reversing_schedule.md` for information about reversing entries

## Package Installation

The project includes `pyproject.toml` for package installation. After installation, you can run:

```powershell
techfix
```

This uses the CLI entry point defined in `techfix.__main__`.

## Troubleshooting

### Common Issues

1. **Database locked error**: Close all instances of the application and try again
2. **Import fails**: Ensure pandas is installed: `pip install pandas`
3. **Scanning not working**: Verify opencv-python and pyzbar are installed correctly
4. **Password reset**: Use `python techfix/techfix/reset_admin.py` to reset admin password

### Getting Help

- Check the **User Guide** (`techfix/tests/USER_GUIDE.md`) for detailed instructions
- Review the **Quick Start Guide** (`techfix/tests/QUICK_START_GUIDE.md`) for common workflows
- See troubleshooting documentation in `techfix/ISSUES AND FIXES/` directory

## Development

### Project Status

- ✅ All 10 accounting cycle steps implemented
- ✅ Complete double-entry bookkeeping system
- ✅ Financial statement generation
- ✅ User authentication and security
- ✅ Data backup and restore
- ✅ Export capabilities (Excel, CSV, PDF)
- ✅ Document scanning and management
- ✅ Search and filtering
- ✅ Undo/redo functionality

### Contributing

When contributing to this project:
1. Follow the existing code style
2. Add type hints to new functions
3. Update tests for new features
4. Update documentation as needed

## Next Steps / Future Improvements

- Enhanced multi-user support with role-based access
- Cloud backup integration
- Additional export formats (JSON, XML)
- Advanced reporting and analytics
- Mobile companion app
- API for third-party integrations

## License

[Add your license information here]

## Support

For issues, questions, or contributions, please refer to the project documentation or create an issue in the project repository.
