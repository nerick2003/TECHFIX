import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, Optional, Tuple, Any, Dict, List
import json


DB_DIR = Path(os.environ.get("TECHFIX_DATA_DIR", "."))
DB_PATH = DB_DIR / "techfix.sqlite3"

ACCOUNTING_CYCLE_STEPS: List[str] = [
    "Analyze transactions",
    "Journalize transactions",
    "Post to ledger",
    "Prepare unadjusted trial balance",
    "Record adjusting entries",
    "Prepare adjusted trial balance",
    "Prepare financial statements",
    "Record closing entries",
    "Prepare post-closing trial balance",
    "Schedule reversing entries",
]


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(reset: bool = False) -> None:
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    conn = get_connection()
    try:
        _create_schema(conn)
        _apply_schema_updates(conn)
        conn.commit()
    finally:
        conn.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,                   -- Asset, Liability, Equity, Revenue, Expense, Contra Asset
            normal_side TEXT NOT NULL,            -- Debit or Credit
            is_active INTEGER NOT NULL DEFAULT 1,
            is_permanent INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            is_adjusting INTEGER NOT NULL DEFAULT 0,
            is_closing INTEGER NOT NULL DEFAULT 0,
            is_reversing INTEGER NOT NULL DEFAULT 0,
            document_ref TEXT,
            external_ref TEXT,
            memo TEXT,
            period_id INTEGER REFERENCES accounting_periods(id),
            source_type TEXT,
            status TEXT NOT NULL DEFAULT 'posted',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            posted_at TEXT,
            created_by TEXT DEFAULT 'system',
            posted_by TEXT
        );

        CREATE TABLE IF NOT EXISTS journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            debit REAL NOT NULL DEFAULT 0,
            credit REAL NOT NULL DEFAULT 0,
            CHECK ((debit = 0 AND credit > 0) OR (credit = 0 AND debit > 0))
        );

        CREATE INDEX IF NOT EXISTS idx_journal_lines_entry ON journal_lines(entry_id);
        CREATE INDEX IF NOT EXISTS idx_journal_lines_account ON journal_lines(account_id);

        CREATE TABLE IF NOT EXISTS accounting_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            start_date TEXT,
            end_date TEXT,
            is_closed INTEGER NOT NULL DEFAULT 0,
            is_current INTEGER NOT NULL DEFAULT 0,
            current_step INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS cycle_step_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL REFERENCES accounting_periods(id) ON DELETE CASCADE,
            step INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            note TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period_id, step)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT
        );

        CREATE TABLE IF NOT EXISTS adjustment_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL REFERENCES accounting_periods(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            requested_on TEXT NOT NULL,
            requested_by TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            approved_by TEXT,
            approved_on TEXT,
            entry_id INTEGER REFERENCES journal_entries(id),
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS trial_balance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL REFERENCES accounting_periods(id) ON DELETE CASCADE,
            stage TEXT NOT NULL,
            as_of TEXT NOT NULL,
            captured_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            payload TEXT NOT NULL,
            UNIQUE(period_id, stage, as_of)
        );

        CREATE TABLE IF NOT EXISTS source_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            label TEXT,
            file_path TEXT NOT NULL,
            uploaded_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reversing_entry_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            reverse_on TEXT NOT NULL,
            created_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending'
        );
        """
    )


def _apply_schema_updates(conn: sqlite3.Connection) -> None:
    _ensure_column(conn, "journal_entries", "document_ref TEXT")
    _ensure_column(conn, "journal_entries", "external_ref TEXT")
    _ensure_column(conn, "journal_entries", "memo TEXT")
    _ensure_column(conn, "journal_entries", "period_id INTEGER REFERENCES accounting_periods(id)")
    _ensure_column(conn, "journal_entries", "source_type TEXT")
    _ensure_column(conn, "journal_entries", "status TEXT NOT NULL DEFAULT 'posted'")
    _ensure_column(conn, "journal_entries", "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    _ensure_column(conn, "journal_entries", "posted_at TEXT")
    _ensure_column(conn, "journal_entries", "created_by TEXT DEFAULT 'system'")
    _ensure_column(conn, "journal_entries", "posted_by TEXT")

    _ensure_table(
        conn,
        "accounting_periods",
        """
        CREATE TABLE accounting_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            start_date TEXT,
            end_date TEXT,
            is_closed INTEGER NOT NULL DEFAULT 0,
            is_current INTEGER NOT NULL DEFAULT 0,
            current_step INTEGER NOT NULL DEFAULT 1
        )
        """,
    )
    _ensure_column(conn, "accounting_periods", "is_current INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "accounting_periods", "current_step INTEGER NOT NULL DEFAULT 1")

    _ensure_table(
        conn,
        "cycle_step_status",
        """
        CREATE TABLE cycle_step_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL REFERENCES accounting_periods(id) ON DELETE CASCADE,
            step INTEGER NOT NULL,
            step_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            note TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(period_id, step)
        )
        """,
    )

    _ensure_table(
        conn,
        "audit_log",
        """
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT
        )
        """,
    )

    _ensure_table(
        conn,
        "adjustment_requests",
        """
        CREATE TABLE adjustment_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL REFERENCES accounting_periods(id) ON DELETE CASCADE,
            description TEXT NOT NULL,
            requested_on TEXT NOT NULL,
            requested_by TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            approved_by TEXT,
            approved_on TEXT,
            entry_id INTEGER REFERENCES journal_entries(id),
            notes TEXT
        )
        """,
    )

    _ensure_table(
        conn,
        "trial_balance_snapshots",
        """
        CREATE TABLE trial_balance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER NOT NULL REFERENCES accounting_periods(id) ON DELETE CASCADE,
            stage TEXT NOT NULL,
            as_of TEXT NOT NULL,
            captured_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            payload TEXT NOT NULL,
            UNIQUE(period_id, stage, as_of)
        )
        """,
    )

    _ensure_table(
        conn,
        "source_documents",
        """
        CREATE TABLE source_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            label TEXT,
            file_path TEXT NOT NULL,
            uploaded_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )

    _ensure_table(
        conn,
        "reversing_entry_queue",
        """
        CREATE TABLE reversing_entry_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            reverse_on TEXT NOT NULL,
            created_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending'
        )
        """,
    )


def _ensure_column(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    try:
        col_name = column_def.split()[0]
        cur = conn.execute(f"PRAGMA table_info({table})")
        if any(row["name"] == col_name for row in cur.fetchall()):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
    except sqlite3.OperationalError:
        # Table may not exist; ignore so caller can create table separately.
        pass


def _ensure_table(conn: sqlite3.Connection, table: str, create_sql: str) -> None:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    if cur.fetchone() is None:
        conn.execute(create_sql)


def seed_chart_of_accounts(conn: Optional[sqlite3.Connection] = None) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        accounts = [
            ("101", "Cash", "Asset", "Debit", 1),
            ("106", "Accounts Receivable", "Asset", "Debit", 1),
            ("124", "Supplies", "Asset", "Debit", 1),
            ("128", "Prepaid Rent", "Asset", "Debit", 1),
            ("167", "Equipment", "Asset", "Debit", 1),
            ("168", "Accumulated Depreciation - Equipment", "Contra Asset", "Credit", 1),
            ("201", "Accounts Payable", "Liability", "Credit", 1),
            ("212", "Salaries Payable", "Liability", "Credit", 1),
            ("230", "Unearned Revenue", "Liability", "Credit", 1),
            ("301", "Owner's Capital", "Equity", "Credit", 1),
            ("302", "Owner's Drawings", "Equity", "Debit", 1),
            ("401", "Service Revenue", "Revenue", "Credit", 0),
            ("402", "Sales Revenue", "Revenue", "Credit", 0),
            ("501", "Rent Expense", "Expense", "Debit", 0),
            ("502", "Salaries Expense", "Expense", "Debit", 0),
            ("503", "Supplies Expense", "Expense", "Debit", 0),
            ("504", "Depreciation Expense", "Expense", "Debit", 0),
            ("505", "Utilities Expense", "Expense", "Debit", 0),
            ("506", "Cost of Goods Sold", "Expense", "Debit", 0),
        ]
        # is_permanent: 1 for balance sheet accounts
        rows = [
            (name, code, type_, normal, 1 if is_perm else 0, 1)
            for (code, name, type_, normal, is_perm) in accounts
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO accounts(name, code, type, normal_side, is_permanent, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()


def insert_journal_entry(
    date: str,
    description: str,
    lines: Iterable[Tuple[int, float, float]],
    *,
    is_adjusting: int = 0,
    is_closing: int = 0,
    is_reversing: int = 0,
    document_ref: Optional[str] = None,
    external_ref: Optional[str] = None,
    memo: Optional[str] = None,
    period_id: Optional[int] = None,
    source_type: Optional[str] = None,
    status: str = "posted",
    created_by: str = "system",
    posted_by: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """
    Insert a balanced journal entry.
    lines: iterable of (account_id, debit, credit)
    Returns entry_id
    """
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        total_debits = sum(d for _, d, _ in lines)
        total_credits = sum(c for _, _, c in lines)
        if round(total_debits - total_credits, 2) != 0:
            raise ValueError("Entry is not balanced: debits must equal credits.")

        if period_id is None:
            period = get_current_period(conn=conn)
            period_id = period["id"] if period else None

        posted_at = datetime.utcnow().isoformat(timespec="seconds") if status == "posted" else None
        if status != "posted" and posted_by:
            posted_by = None

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO journal_entries(
                date,
                description,
                is_adjusting,
                is_closing,
                is_reversing,
                document_ref,
                external_ref,
                memo,
                period_id,
                source_type,
                status,
                created_by,
                posted_at,
                posted_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                description,
                is_adjusting,
                is_closing,
                is_reversing,
                document_ref,
                external_ref,
                memo,
                period_id,
                source_type,
                status,
                created_by,
                posted_at,
                posted_by,
            ),
        )
        entry_id = cur.lastrowid
        for account_id, debit, credit in lines:
            cur.execute(
                """
                INSERT INTO journal_lines(entry_id, account_id, debit, credit)
                VALUES (?, ?, ?, ?)
                """,
                (entry_id, account_id, float(debit), float(credit)),
            )
        conn.commit()

        log_audit(
            action="journal_entry_created",
            details=json.dumps(
                {
                    "entry_id": entry_id,
                    "date": date,
                    "description": description,
                    "is_adjusting": bool(is_adjusting),
                    "is_closing": bool(is_closing),
                    "is_reversing": bool(is_reversing),
                    "period_id": period_id,
                    "status": status,
                }
            ),
            user=created_by,
            conn=conn,
        )
        return int(entry_id)
    finally:
        if not owned:
            conn.close()


def get_accounts(conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, code, name, type, normal_side, is_permanent, is_active FROM accounts ORDER BY code"
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def list_accounting_periods(conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, name, start_date, end_date, is_closed, is_current, current_step
            FROM accounting_periods
            ORDER BY COALESCE(start_date, name)
            """
        )
        periods = cur.fetchall()
        if not periods:
            ensure_default_period(conn=conn)
            cur = conn.execute(
                """
                SELECT id, name, start_date, end_date, is_closed, is_current, current_step
                FROM accounting_periods
                ORDER BY COALESCE(start_date, name)
                """
            )
            return cur.fetchall()
        return periods
    finally:
        if not owned:
            conn.close()


def ensure_default_period(*, conn: Optional[sqlite3.Connection] = None) -> sqlite3.Row:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        today = date.today()
        period_name = today.strftime("%Y-%m")
        cur = conn.execute("SELECT * FROM accounting_periods WHERE name=?", (period_name,))
        row = cur.fetchone()
        if row is None:
            start_date = f"{period_name}-01"
            conn.execute(
                """
                INSERT INTO accounting_periods(name, start_date, is_current)
                VALUES (?, ?, 1)
                """,
                (period_name, start_date),
            )
            conn.execute(
                "UPDATE accounting_periods SET is_current=0 WHERE name<>?",
                (period_name,),
            )
            conn.commit()
            cur = conn.execute("SELECT * FROM accounting_periods WHERE name=?", (period_name,))
            row = cur.fetchone()
        ensure_cycle_steps(int(row["id"]), conn=conn)
        return row
    finally:
        if not owned:
            conn.close()


def create_period(
    name: str,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO accounting_periods(name, start_date, end_date, is_current)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(name) DO UPDATE SET start_date=excluded.start_date, end_date=excluded.end_date
            """,
            (name, start_date, end_date),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM accounting_periods WHERE name=?",
            (name,),
        ).fetchone()
        period_id = int(row["id"])
        ensure_cycle_steps(period_id, conn=conn)
        return period_id
    finally:
        if not owned:
            conn.close()


def get_current_period(*, conn: Optional[sqlite3.Connection] = None) -> Optional[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM accounting_periods WHERE is_current=1 LIMIT 1")
        row = cur.fetchone()
        if row is None:
            row = ensure_default_period(conn=conn)
        else:
            ensure_cycle_steps(int(row["id"]), conn=conn)
        return row
    finally:
        if not owned:
            conn.close()


def set_current_period(period_id: int, *, conn: Optional[sqlite3.Connection] = None) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        conn.execute("UPDATE accounting_periods SET is_current=0")
        conn.execute("UPDATE accounting_periods SET is_current=1 WHERE id=?", (period_id,))
        conn.commit()
        ensure_cycle_steps(period_id, conn=conn)
    finally:
        if not owned:
            conn.close()


def ensure_cycle_steps(period_id: int, *, conn: Optional[sqlite3.Connection] = None) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        conn.executemany(
            """
            INSERT OR IGNORE INTO cycle_step_status(period_id, step, step_name, status)
            VALUES (?, ?, ?, 'pending')
            """,
            [(period_id, idx + 1, name) for idx, name in enumerate(ACCOUNTING_CYCLE_STEPS)],
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()


def get_cycle_status(period_id: int, *, conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        ensure_cycle_steps(period_id, conn=conn)
        cur = conn.execute(
            """
            SELECT step, step_name, status, note, updated_at
            FROM cycle_step_status
            WHERE period_id=?
            ORDER BY step
            """,
            (period_id,),
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def set_cycle_step_status(
    period_id: int,
    step: int,
    status: str,
    note: Optional[str] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        ensure_cycle_steps(period_id, conn=conn)
        conn.execute(
            """
            UPDATE cycle_step_status
            SET status=?, note=?, updated_at=CURRENT_TIMESTAMP
            WHERE period_id=? AND step=?
            """,
            (status, note, period_id, step),
        )
        conn.execute(
            "UPDATE accounting_periods SET current_step=? WHERE id=?",
            (step, period_id),
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()


def log_audit(
    *,
    action: str,
    details: Optional[str] = None,
    user: str = "system",
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO audit_log(user, action, details, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (user, action, details, datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()


def list_audit_log(limit: int = 100, *, conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, timestamp, user, action, details
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def create_adjustment_request(
    period_id: int,
    description: str,
    *,
    requested_on: Optional[str] = None,
    requested_by: Optional[str] = None,
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        ensure_cycle_steps(period_id, conn=conn)
        requested_on = requested_on or datetime.utcnow().date().isoformat()
        cur = conn.execute(
            """
            INSERT INTO adjustment_requests(period_id, description, requested_on, requested_by, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (period_id, description, requested_on, requested_by, notes),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def list_adjustment_requests(
    period_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, description, requested_on, requested_by, status, approved_by, approved_on, entry_id, notes
            FROM adjustment_requests
            WHERE period_id=?
            ORDER BY requested_on, id
            """,
            (period_id,),
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def link_adjustment_to_entry(
    adjustment_id: int,
    entry_id: int,
    *,
    approved_by: Optional[str] = None,
    approved_on: Optional[str] = None,
    status: str = "posted",
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE adjustment_requests
            SET entry_id=?, approved_by=?, approved_on=?, status=?
            WHERE id=?
            """,
            (
                entry_id,
                approved_by,
                approved_on or datetime.utcnow().date().isoformat(),
                status,
                adjustment_id,
            ),
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()


def update_adjustment_status(
    adjustment_id: int,
    status: str,
    *,
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE adjustment_requests
            SET status=?,
                notes=COALESCE(?, notes),
                approved_on=CASE WHEN ?='approved' THEN COALESCE(approved_on, CURRENT_DATE) ELSE approved_on END
            WHERE id=?
            """,
            (status, notes, status, adjustment_id),
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()


def capture_trial_balance_snapshot(
    period_id: int,
    stage: str,
    as_of: str,
    data: Iterable[Dict[str, Any]],
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        payload = json.dumps(list(data))
        cur = conn.execute(
            """
            INSERT OR REPLACE INTO trial_balance_snapshots(period_id, stage, as_of, payload)
            VALUES (?, ?, ?, ?)
            """,
            (period_id, stage, as_of, payload),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def get_trial_balance_snapshots(
    period_id: int,
    stage: Optional[str] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        if stage:
            cur = conn.execute(
                """
                SELECT id, stage, as_of, captured_on, payload
                FROM trial_balance_snapshots
                WHERE period_id=? AND stage=?
                ORDER BY captured_on DESC
                """,
                (period_id, stage),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, stage, as_of, captured_on, payload
                FROM trial_balance_snapshots
                WHERE period_id=?
                ORDER BY captured_on DESC
                """,
                (period_id,),
            )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def add_source_document(
    entry_id: int,
    file_path: str,
    *,
    label: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO source_documents(entry_id, label, file_path)
            VALUES (?, ?, ?)
            """,
            (entry_id, label, file_path),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def list_source_documents(
    entry_id: int,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, label, file_path, uploaded_on
            FROM source_documents
            WHERE entry_id=?
            ORDER BY id
            """,
            (entry_id,),
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def schedule_reversing_entry(
    entry_id: int,
    reverse_on: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO reversing_entry_queue(original_entry_id, reverse_on)
            VALUES (?, ?)
            """,
            (entry_id, reverse_on),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def list_reversing_queue(*, conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, original_entry_id, reverse_on, created_on, status
            FROM reversing_entry_queue
            ORDER BY reverse_on, id
            """
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def get_account_by_name(name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM accounts WHERE name = ?", (name,))
        return cur.fetchone()
    finally:
        if not owned:
            conn.close()


def compute_trial_balance(
    *, up_to_date: Optional[str] = None, include_temporary: bool = True, period_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None
) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        params: list = []
        date_filter = ""
        if up_to_date:
            date_filter = "AND je.date <= ?"
            params.append(up_to_date)

        temp_filter = ""
        if not include_temporary:
            temp_filter = "AND a.is_permanent = 1"

        period_filter = ""
        if period_id is not None:
            period_filter = "AND je.period_id = ?"
            params.append(period_id)

        # Compute a signed balance then split into non-negative net_debit / net_credit
        balance_expr = "(COALESCE(SUM(jl.debit),0) - COALESCE(SUM(jl.credit),0))"
        sql = f"""
            SELECT a.id as account_id, a.code, a.name, a.type, a.normal_side,
                   -- net_debit: positive balance when debits exceed credits
                   ROUND(CASE WHEN {balance_expr} > 0 THEN {balance_expr} ELSE 0 END, 2) AS net_debit,
                   -- net_credit: positive balance when credits exceed debits
                   ROUND(CASE WHEN {balance_expr} < 0 THEN -({balance_expr}) ELSE 0 END, 2) AS net_credit
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jl.entry_id {date_filter} {period_filter}
            WHERE a.is_active = 1 {temp_filter}
            GROUP BY a.id, a.code, a.name, a.type, a.normal_side
            ORDER BY a.code
        """
        cur = conn.execute(sql, params)
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def fetch_journal(conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT je.id as entry_id, je.date, je.description, je.is_adjusting, je.is_closing, je.is_reversing,
                   jl.id as line_id, a.code, a.name, jl.debit, jl.credit
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            JOIN accounts a ON a.id = jl.account_id
            ORDER BY je.date, je.id, jl.id
            """
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def fetch_ledger(conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT a.id as account_id, a.code, a.name, a.type, a.normal_side,
                   je.date, je.description, jl.debit, jl.credit
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jl.entry_id
            WHERE a.is_active = 1
            ORDER BY a.code, je.date, je.id, jl.id
            """
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def export_rows_to_csv(rows: Iterable[sqlite3.Row], headers: Iterable[str], output_path: Path) -> None:
    import csv

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(list(headers))
        for r in rows:
            if isinstance(r, sqlite3.Row):
                writer.writerow([r[h] for h in headers])
            else:
                writer.writerow(list(r))


def export_rows_to_excel(rows: Iterable[sqlite3.Row], headers: Iterable[str], output_path: Path, *, sheet_name: str = "Sheet1") -> None:
    try:
        from openpyxl import Workbook
    except ImportError as e:
        raise RuntimeError("openpyxl is required for Excel export. Install with: pip install openpyxl") from e

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    hdrs = list(headers)
    ws.append(hdrs)
    for r in rows:
        if isinstance(r, sqlite3.Row):
            ws.append([r[h] for h in hdrs])
        else:
            ws.append(list(r))
    wb.save(str(output_path))


def export_text_to_excel(lines: Iterable[str], output_path: Path, *, sheet_name: str = "Report") -> None:
    try:
        from openpyxl import Workbook
    except ImportError as e:
        raise RuntimeError("openpyxl is required for Excel export. Install with: pip install openpyxl") from e

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    for ln in lines:
        ws.append([ln])
    wb.save(str(output_path))


