"""
Temporary helper to realign the current accounting period dates with the
existing journal entries in the database. This script:
1) Prints the existing accounting_periods table.
2) Updates period id=1 to cover the entry date range (2025-01-01 to 2025-12-31)
   and ensures it is marked as current.
3) Prints the accounting_periods table again for verification.
"""

import sqlite3
from pathlib import Path
import json

DB_PATH = Path(__file__).parent / "techfix.sqlite3"


def dump_periods(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, start_date, end_date, is_current, is_closed FROM accounting_periods ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("Before update:")
    print(json.dumps(dump_periods(conn), indent=2))

    # Use the built-in helper to realign the period.
    from techfix import db
    db.realign_period(
        1,
        name="2025",
        start_date="2025-01-01",
        end_date="2025-12-31",
        set_as_current=True,
        conn=conn,
    )

    print("\nAfter update:")
    print(json.dumps(dump_periods(conn), indent=2))


if __name__ == "__main__":
    main()

