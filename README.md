TechFix

- Purpose: Desktop accounting practice app with SQLite storage and Tkinter GUI.
- Key modules: `techfix/db.py`, `techfix/accounting.py`, `techfix/gui.py`, entry `main.py`.

Setup

- Create a virtual environment.
- Install dependencies: `pip install -r TECHFIX/requirements.txt`.
- Optional Excel export requires `openpyxl` (already listed).

Run

- Start the app: `python TECHFIX/TECHFIX/main.py`.
- Set data directory via env var `TECHFIX_DATA_DIR` to change where `techfix.sqlite3` is stored.

Tests

- Run: `python -m unittest discover -s TECHFIX/TECHFIX/tests -p "test_*.py" -v`.

Notes

- First launch seeds a chart of accounts and ensures the current period.
- Excel and CSV exports write to the chosen output path, creating parent folders.

Next steps

- Add packaging (`pyproject.toml`) for installable CLI entry point.
- Add `.gitignore` for `*.sqlite3`, `__pycache__/`, and local artifacts.
- Add type hints across modules and enable static checks.
