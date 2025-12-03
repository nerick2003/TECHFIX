TechFix

- Purpose: Desktop accounting practice app with SQLite storage and Tkinter GUI.
- Key modules: `techfix/db.py`, `techfix/accounting.py`, `techfix/gui.py`, entry `main.py`.

Features

- Responsive UI that adapts to different screen sizes and aspect ratios (PC monitors, laptops).
- Global Action button (bottom-left sidebar) opens an aspect ratio chooser window to quickly resize the main window to preset dimensions (laptop 16:9, desktop 16:9, square 4:3, tall/coding split).
- Sidebar automatically adjusts width based on window aspect ratio for optimal layout on wide vs. tall screens.
- Light/Dark theme support with system theme detection.

Setup

1. **Navigate to the project directory:**
   ```powershell
   cd "C:\Users\neric\Desktop\TechFix\TECHFIX"
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

4. **Install dependencies from requirements.txt:**
   ```powershell
   pip install -r requirements.txt
   ```
   This will install:
   - Pillow (image processing)
   - python-barcode and qrcode (barcode/QR code generation)
   - opencv-python and pyzbar (image scanning)
   - openpyxl (Excel export)
   - reportlab (PDF generation)

5. **Verify installation (optional):**
   ```powershell
   pip list
   ```
   You should see all the packages listed above installed in your virtual environment.

Run

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

3. **Optional:** Set data directory via env var `TECHFIX_DATA_DIR` to change where `techfix.sqlite3` is stored:
   ```powershell
   $env:TECHFIX_DATA_DIR="C:\path\to\your\data"
   python TECHFIX\main.py
   ```

Tests

- Run: `python -m unittest discover -s tests -p "test_*.py" -v`.

Notes

- First launch seeds a chart of accounts and ensures the current period.
- Excel and CSV exports write to the chosen output path, creating parent folders.
- Window size and theme preferences are saved and restored on next launch.
- Use the Global Action button to quickly test the UI at different aspect ratios for development or presentation purposes.

Next steps

- Packaging (`pyproject.toml`) exists for installable CLI entry point.
- Add `.gitignore` for `*.sqlite3`, `__pycache__/`, and local artifacts.
- Continue adding type hints across modules and enable static checks.

Documentation

- Use the Export tab → "Export Documentation (PDF)" to generate a program overview PDF.
- The PDF includes purpose, features, modules, usage, and data/config notes.
