import os
import sqlite3
from datetime import datetime, date, timezone
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

SCHEMA_VERSION: int = 1


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


def get_or_create_default_user(conn: sqlite3.Connection) -> sqlite3.Row:
    """
    Ensure there is at least one application user and return it.

    For now we use a simple single-user model with username 'default'.
    """
    cur = conn.execute("SELECT * FROM users WHERE username = ?", ("default",))
    row = cur.fetchone()
    if row:
        return row
    conn.execute(
        "INSERT INTO users (username, full_name, is_active) VALUES (?,?,1)",
        ("default", "Default User"),
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE username = ?", ("default",)).fetchone()


def get_user_preferences(user_id: int, conn: sqlite3.Connection) -> Dict[str, Any]:
    cur = conn.execute(
        "SELECT key, value FROM user_preferences WHERE user_id = ?",
        (user_id,),
    )
    prefs: Dict[str, Any] = {}
    for row in cur.fetchall():
        key = row["key"]
        val_raw = row["value"]
        try:
            val = json.loads(val_raw)
        except Exception:
            val = val_raw
        prefs[key] = val
    return prefs


def set_user_preference(user_id: int, key: str, value: Any, conn: sqlite3.Connection) -> None:
    payload = json.dumps(value)
    conn.execute(
        """
        INSERT INTO user_preferences (user_id, key, value)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value
        """,
        (user_id, key, payload),
    )
    conn.commit()


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

        -- Basic subledgers: customers, vendors, AR/AP documents
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            contact TEXT,
            email TEXT,
            phone TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            contact TEXT,
            email TEXT,
            phone TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS sales_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            invoice_no TEXT,
            date TEXT NOT NULL,
            due_date TEXT,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
        );

        CREATE TABLE IF NOT EXISTS purchase_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL REFERENCES vendors(id),
            entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            bill_no TEXT,
            date TEXT NOT NULL,
            due_date TEXT,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
        );

        -- Simple inventory and fixed asset scaffolding
        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            unit TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS inventory_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
            entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
            date TEXT NOT NULL,
            quantity REAL NOT NULL,
            memo TEXT
        );

        CREATE TABLE IF NOT EXISTS fixed_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            asset_code TEXT NOT NULL UNIQUE,
            acquisition_date TEXT,
            cost REAL NOT NULL DEFAULT 0,
            useful_life_months INTEGER,
            salvage_value REAL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        -- Multi-entity and security model (companies, users, roles)
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            base_currency TEXT
        );

        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            full_name TEXT,
            role_id INTEGER REFERENCES roles(id),
            company_id INTEGER REFERENCES companies(id),
            is_active INTEGER NOT NULL DEFAULT 1,
            password_hash TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        );

        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            value TEXT,
            UNIQUE(user_id, key)
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
            posted_by TEXT,
            company_id INTEGER REFERENCES companies(id),
            created_by_user_id INTEGER REFERENCES users(id),
            posted_by_user_id INTEGER REFERENCES users(id),
            currency_code TEXT,
            fx_rate REAL
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
            status TEXT NOT NULL DEFAULT 'pending',
            deadline_on TEXT,
            entry_type TEXT,
            template_id INTEGER,
            priority TEXT,
            reminder_on TEXT,
            notes TEXT,
            approval_required INTEGER NOT NULL DEFAULT 0,
            authorization_level INTEGER NOT NULL DEFAULT 0,
            reversed_entry_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'info',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER NOT NULL DEFAULT 0,
            read_at TEXT
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query TEXT NOT NULL,
            search_type TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def _apply_schema_updates(conn: sqlite3.Connection) -> None:
    # User authentication columns
    _ensure_column(conn, "users", "password_hash TEXT")
    _ensure_column(conn, "users", "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    _ensure_column(conn, "users", "last_login TEXT")
    
    # Core journal / periods / cycle tables and columns
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

    # Multi-entity and security model
    _ensure_table(
        conn,
        "companies",
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE
        )
        """,
    )
    _ensure_table(
        conn,
        "roles",
        """
        CREATE TABLE roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
        """,
    )
    _ensure_table(
        conn,
        "users",
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            full_name TEXT,
            role_id INTEGER REFERENCES roles(id),
            company_id INTEGER REFERENCES companies(id),
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
    )
    _ensure_table(
        conn,
        "user_preferences",
        """
        CREATE TABLE user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key TEXT NOT NULL,
            value TEXT,
            UNIQUE(user_id, key)
        )
        """,
    )

    # Currencies and tax codes (multi-currency & tax scaffolding)
    _ensure_table(
        conn,
        "currencies",
        """
        CREATE TABLE currencies (
            code TEXT PRIMARY KEY,
            name TEXT,
            symbol TEXT
        )
        """,
    )
    _ensure_table(
        conn,
        "tax_codes",
        """
        CREATE TABLE tax_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            rate REAL NOT NULL,              -- e.g. 0.12 for 12%
            account_id INTEGER,              -- optional link to a tax account
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
    )
    _ensure_column(conn, "companies", "base_currency TEXT")
    _ensure_column(conn, "journal_entries", "currency_code TEXT")
    _ensure_column(conn, "journal_entries", "fx_rate REAL")

    # Subledger tables (customers, vendors, AR/AP, inventory, fixed assets)
    _ensure_table(
        conn,
        "customers",
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            contact TEXT,
            email TEXT,
            phone TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
    )
    _ensure_table(
        conn,
        "vendors",
        """
        CREATE TABLE vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            contact TEXT,
            email TEXT,
            phone TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
    )
    _ensure_table(
        conn,
        "sales_invoices",
        """
        CREATE TABLE sales_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            invoice_no TEXT,
            date TEXT NOT NULL,
            due_date TEXT,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
        )
        """,
    )
    _ensure_table(
        conn,
        "purchase_bills",
        """
        CREATE TABLE purchase_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL REFERENCES vendors(id),
            entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            bill_no TEXT,
            date TEXT NOT NULL,
            due_date TEXT,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
        )
        """,
    )
    _ensure_table(
        conn,
        "inventory_items",
        """
        CREATE TABLE inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            unit TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
    )
    _ensure_table(
        conn,
        "inventory_movements",
        """
        CREATE TABLE inventory_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
            entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL,
            date TEXT NOT NULL,
            quantity REAL NOT NULL,
            memo TEXT
        )
        """,
    )
    _ensure_table(
        conn,
        "fixed_assets",
        """
        CREATE TABLE fixed_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            asset_code TEXT NOT NULL UNIQUE,
            acquisition_date TEXT,
            cost REAL NOT NULL DEFAULT 0,
            useful_life_months INTEGER,
            salvage_value REAL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )

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
    _ensure_column(conn, "reversing_entry_queue", "deadline_on TEXT")
    _ensure_column(conn, "reversing_entry_queue", "entry_type TEXT")
    _ensure_column(conn, "reversing_entry_queue", "template_id INTEGER")
    _ensure_column(conn, "reversing_entry_queue", "priority TEXT")
    _ensure_column(conn, "reversing_entry_queue", "reminder_on TEXT")
    _ensure_column(conn, "reversing_entry_queue", "notes TEXT")
    _ensure_column(conn, "reversing_entry_queue", "approval_required INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "reversing_entry_queue", "authorization_level INTEGER NOT NULL DEFAULT 0")
    
    # Notifications table
    _ensure_table(
        conn,
        "notifications",
        """
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'info',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER NOT NULL DEFAULT 0,
            read_at TEXT
        )
        """,
    )
    
    # Search history table
    _ensure_table(
        conn,
        "search_history",
        """
        CREATE TABLE search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            query TEXT NOT NULL,
            search_type TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    _ensure_column(conn, "reversing_entry_queue", "reversed_entry_id INTEGER")

    _ensure_table(
        conn,
        "reversing_entry_templates",
        """
        CREATE TABLE reversing_entry_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            entry_type TEXT,
            required_fields TEXT,
            default_memo TEXT,
            authorization_level INTEGER NOT NULL DEFAULT 0,
            approval_required INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """,
    )

    _ensure_table(
        conn,
        "reversing_entry_approvals",
        """
        CREATE TABLE reversing_entry_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER NOT NULL REFERENCES reversing_entry_queue(id) ON DELETE CASCADE,
            reviewer TEXT,
            role TEXT,
            level INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            approved_on TEXT,
            notes TEXT
        )
        """,
    )

    _ensure_table(
        conn,
        "reversing_entry_history",
        """
        CREATE TABLE reversing_entry_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER NOT NULL REFERENCES reversing_entry_queue(id) ON DELETE CASCADE,
            change_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            field TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT DEFAULT 'system'
        )
        """,
    )

    _ensure_table(
        conn,
        "schema_versions",
        """
        CREATE TABLE schema_versions (
            version INTEGER PRIMARY KEY,
            applied_on TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    cur = conn.execute("SELECT 1 FROM schema_versions WHERE version=?", (SCHEMA_VERSION,))
    if cur.fetchone() is None:
        conn.execute("INSERT INTO schema_versions(version) VALUES (?)", (SCHEMA_VERSION,))


# --- Simple helpers for users / roles / companies --------------------------

def ensure_default_role_and_user(*, conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Ensure there is at least one basic role and user.
    This keeps the security model minimal but ready for future GUI use.
    """
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        # Default roles
        default_roles = [
            ('Admin', 'Full access to all features'),
            ('Manager', 'Management access with approval capabilities'),
            ('Accountant', 'Full accounting operations access'),
            ('User', 'Standard user with read and limited write access'),
            ('Viewer', 'Read-only access to view reports and data')
        ]
        for role_name, role_description in default_roles:
            conn.execute(
                """
                INSERT OR IGNORE INTO roles(name, description)
                VALUES (?, ?)
                """,
                (role_name, role_description)
            )
        # Default company (already seeded in seed_chart_of_accounts, but safe here too)
        conn.execute(
            """
            INSERT OR IGNORE INTO companies(name, code, base_currency)
            VALUES ('Default Company', 'DEFAULT', 'PHP')
            """
        )
        # Default admin user
        cur = conn.execute("SELECT id FROM companies WHERE code='DEFAULT'")
        row = cur.fetchone()
        company_id = int(row["id"]) if row else None
        cur = conn.execute("SELECT id FROM roles WHERE name='Admin'")
        role_row = cur.fetchone()
        role_id = int(role_row["id"]) if role_row else None
        if company_id and role_id:
            # Import auth module here to avoid circular imports
            from . import auth
            # Default password hash for admin user
            default_password_hash = auth.hash_password("admin")
            
            # Check if admin user exists
            cur = conn.execute("SELECT id, password_hash FROM users WHERE username='admin'")
            existing = cur.fetchone()
            
            if existing:
                # Admin exists - set password_hash to default if it's empty/invalid
                admin_id = existing['id']
                existing_hash = existing.get('password_hash') if hasattr(existing, 'get') else existing['password_hash']
                
                # If password hash is empty or None, set it to default "admin" password
                if not existing_hash or (isinstance(existing_hash, str) and len(existing_hash.strip()) == 0):
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (default_password_hash, admin_id)
                    )
            else:
                # Create admin user with default "admin" password
                conn.execute(
                    """
                    INSERT INTO users(username, full_name, role_id, company_id, is_active, password_hash)
                    VALUES ('admin', 'Administrator', ?, ?, 1, ?)
                    """,
                    (role_id, company_id, default_password_hash),
                )
        conn.commit()
    finally:
        if not owned:
            conn.close()


def get_user_by_username(username: str, *, conn: Optional[sqlite3.Connection] = None) -> Optional[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
        return cur.fetchone()
    finally:
        if not owned:
            conn.close()


def get_company_by_code(code: str, *, conn: Optional[sqlite3.Connection] = None) -> Optional[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM companies WHERE code=?", (code,))
        return cur.fetchone()
    finally:
        if not owned:
            conn.close()


def create_currency(
    code: str,
    name: Optional[str] = None,
    symbol: Optional[str] = None,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Insert or update a currency definition."""
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO currencies(code, name, symbol)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET name=excluded.name, symbol=excluded.symbol
            """,
            (code, name, symbol),
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()


def list_currencies(*, conn: Optional[sqlite3.Connection] = None) -> List[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute("SELECT code, name, symbol FROM currencies ORDER BY code")
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def create_tax_code(
    code: str,
    name: str,
    rate: float,
    *,
    account_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    """Create or update a tax code (e.g. VAT 12%)."""
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tax_codes(code, name, rate, account_id, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(code) DO UPDATE SET name=excluded.name, rate=excluded.rate, account_id=excluded.account_id
            """,
            (code, name, float(rate), account_id),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def list_tax_codes(*, conn: Optional[sqlite3.Connection] = None) -> List[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, code, name, rate, account_id, is_active FROM tax_codes ORDER BY code"
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def get_tax_code_by_code(
    code: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, code, name, rate, account_id, is_active FROM tax_codes WHERE code=?",
            (code,),
        )
        return cur.fetchone()
    finally:
        if not owned:
            conn.close()


def get_accounting_period_by_id(period_id: int, *, conn: Optional[sqlite3.Connection] = None) -> Optional[sqlite3.Row]:
    """Fetch a single accounting period row by id."""
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM accounting_periods WHERE id=?",
            (period_id,),
        )
        return cur.fetchone()
    finally:
        if not owned:
            conn.close()


def set_period_closed(
    period_id: int,
    is_closed: bool = True,
    *,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Mark an accounting period as closed or open.
    Does not change current_step; meant to be an explicit admin action.
    """
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        conn.execute(
            "UPDATE accounting_periods SET is_closed=? WHERE id=?",
            (1 if is_closed else 0, period_id),
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()


# --- Simple AR/AP, inventory, and fixed asset helpers ----------------------

def create_customer(
    name: str,
    code: str,
    *,
    contact: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO customers(name, code, contact, email, phone, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (name, code, contact, email, phone),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def list_customers(*, conn: Optional[sqlite3.Connection] = None) -> List[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, name, code, contact, email, phone, is_active FROM customers ORDER BY name"
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def create_vendor(
    name: str,
    code: str,
    *,
    contact: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO vendors(name, code, contact, email, phone, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (name, code, contact, email, phone),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def list_vendors(*, conn: Optional[sqlite3.Connection] = None) -> List[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, name, code, contact, email, phone, is_active FROM vendors ORDER BY name"
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def create_sales_invoice(
    customer_id: int,
    entry_id: int,
    date: str,
    total_amount: float,
    *,
    invoice_no: Optional[str] = None,
    due_date: Optional[str] = None,
    status: str = "open",
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO sales_invoices(customer_id, entry_id, invoice_no, date, due_date, total_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (customer_id, entry_id, invoice_no, date, due_date, float(total_amount), status),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def create_purchase_bill(
    vendor_id: int,
    entry_id: int,
    date: str,
    total_amount: float,
    *,
    bill_no: Optional[str] = None,
    due_date: Optional[str] = None,
    status: str = "open",
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO purchase_bills(vendor_id, entry_id, bill_no, date, due_date, total_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (vendor_id, entry_id, bill_no, date, due_date, float(total_amount), status),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()



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
        # Ensure a default company exists (single-entity by default)
        conn.execute(
            """
            INSERT OR IGNORE INTO companies(name, code, base_currency)
            VALUES ('Default Company', 'DEFAULT', 'PHP')
            """
        )

        # Seed using the reference Chart of Accounts (codes, titles, groups)
        # This drives the debit/credit account dropdowns throughout the app.
        accounts = [
            # Account No., Account Title, Account Group, Normal side, Is permanent (1 = balance sheet)
            ("101", "Cash", "Asset", "Debit", 1),
            ("102", "Accounts Receivable", "Asset", "Debit", 1),
            ("103", "Input Tax", "Asset", "Debit", 1),
            ("104", "Office Equipment", "Asset", "Debit", 1),
            ("105", "Accumulated Depreciation", "Contra Asset", "Credit", 1),
            ("106", "Accumulated Depreciation - Equipment", "Contra Asset", "Credit", 1),
            ("124", "Supplies", "Asset", "Debit", 1),

            ("201", "Accounts Payable", "Liability", "Credit", 1),
            ("202", "Utilities Payable", "Liability", "Credit", 1),
            ("203", "Withholding Taxes Payable", "Liability", "Credit", 1),
            ("204", "SSS, PhilHealth, and Pag-Ibig Payable", "Liability", "Credit", 1),
            ("205", "Expanded Withholding Tax Payable", "Liability", "Credit", 1),
            ("206", "Accrued Percentage Tax Payable", "Liability", "Credit", 1),

            ("301", "Owner's Capital", "Equity", "Credit", 1),
            ("302", "Owner's Drawings", "Equity", "Debit", 1),

            ("401", "Service Revenue", "Revenue", "Credit", 0),

            ("402", "Salaries & Wages", "Expense", "Debit", 0),
            ("403", "Rent Expense", "Expense", "Debit", 0),
            ("404", "Utilities Expense", "Expense", "Debit", 0),
            ("405", "Supplies Expense", "Expense", "Debit", 0),
            ("406", "PhilHealth, Pag-Ibig and SSS Contributions", "Expense", "Debit", 0),
            ("407", "Depreciation Expense", "Expense", "Debit", 0),
            ("408", "Transportation Expense", "Expense", "Debit", 0),
            ("409", "Percentage Tax Expense", "Expense", "Debit", 0),
            ("410", "Income Summary", "Expense", "Debit", 0),
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
    company_id: Optional[int] = None,
    created_by_user_id: Optional[int] = None,
    posted_by_user_id: Optional[int] = None,
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
        # Convert to list to check if empty and allow multiple iterations
        lines_list = list(lines)
        if not lines_list:
            raise ValueError("Journal entry must have at least one line (debit or credit).")
        
        total_debits = sum(d for _, d, _ in lines_list)
        total_credits = sum(c for _, _, c in lines_list)
        if round(total_debits - total_credits, 2) != 0:
            raise ValueError("Entry is not balanced: debits must equal credits.")

        if period_id is None:
            period = get_current_period(conn=conn)
            period_id = period["id"] if period else None

        posted_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if status == "posted" else None
        if status != "posted":
            # Only posted entries can have a posted_by / posted_by_user_id
            posted_by = None
            posted_by_user_id = None

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
                posted_by,
                company_id,
                created_by_user_id,
                posted_by_user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                company_id,
                created_by_user_id,
                posted_by_user_id,
            ),
        )
        entry_id = cur.lastrowid
        for account_id, debit, credit in lines_list:
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


def realign_period(
    period_id: int,
    *,
    name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    set_as_current: bool = True,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    Update an accounting period's dates/name and optionally mark it current.
    Useful when entries were posted outside the original period range.
    """
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        fields = []
        params: list[Any] = []
        if name is not None:
            fields.append("name = ?")
            params.append(name)
        if start_date is not None:
            fields.append("start_date = ?")
            params.append(start_date)
        if end_date is not None:
            fields.append("end_date = ?")
            params.append(end_date)
        # Always keep the period open when realigning manually.
        fields.append("is_closed = 0")
        params.append(period_id)
        conn.execute(f"UPDATE accounting_periods SET {', '.join(fields)} WHERE id = ?", params)
        if set_as_current:
            conn.execute("UPDATE accounting_periods SET is_current = 0 WHERE id <> ?", (period_id,))
            conn.execute("UPDATE accounting_periods SET is_current = 1 WHERE id = ?", (period_id,))
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
            (user, action, details, datetime.now(timezone.utc).isoformat(timespec="seconds")),
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
        requested_on = requested_on or datetime.now(timezone.utc).date().isoformat()
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
                approved_on or datetime.now(timezone.utc).date().isoformat(),
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
    deadline_on: Optional[str] = None,
    entry_type: Optional[str] = None,
    template_id: Optional[int] = None,
    priority: Optional[str] = None,
    reminder_on: Optional[str] = None,
    notes: Optional[str] = None,
    approval_required: int = 0,
    authorization_level: int = 0,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO reversing_entry_queue(
                original_entry_id, reverse_on, deadline_on, entry_type, template_id,
                priority, reminder_on, notes, approval_required, authorization_level
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                reverse_on,
                deadline_on,
                entry_type,
                template_id,
                priority,
                reminder_on,
                notes,
                int(approval_required),
                int(authorization_level),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()


def list_reversing_queue(period_id: Optional[int] = None, *, conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        sql = (
            """
            SELECT rq.id, rq.original_entry_id, rq.reverse_on, rq.created_on, rq.status, rq.reversed_entry_id,
                   rq.deadline_on, rq.entry_type, rq.template_id, rq.priority, rq.reminder_on, rq.notes,
                   rq.approval_required, rq.authorization_level
            FROM reversing_entry_queue rq
            JOIN journal_entries je ON je.id = rq.original_entry_id
            {period_clause}
            ORDER BY rq.reverse_on, rq.id
            """
        )
        params: list = []
        period_clause = ""
        if period_id is not None:
            period_clause = "WHERE je.period_id = ?"
            params.append(period_id)
        sql = sql.format(period_clause=period_clause)
        cur = conn.execute(sql, params)
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def update_reversing_status(item_id: int, status: str, *, reversed_entry_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        prev = conn.execute(
            "SELECT status FROM reversing_entry_queue WHERE id=?",
            (item_id,),
        ).fetchone()
        old_status = prev["status"] if prev else None
        conn.execute(
            """
            UPDATE reversing_entry_queue
            SET status=?, reversed_entry_id=COALESCE(?, reversed_entry_id)
            WHERE id=?
            """
            ,
            (status, reversed_entry_id, item_id),
        )
        conn.commit()
        conn.execute(
            """
            INSERT INTO reversing_entry_history(queue_id, field, old_value, new_value)
            VALUES (?, 'status', ?, ?)
            """,
            (item_id, old_status, status),
        )
        conn.commit()
        
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
    *, from_date: Optional[str] = None, up_to_date: Optional[str] = None, include_temporary: bool = True, period_id: Optional[int] = None, exclude_closing: bool = False, exclude_adjusting: bool = False, conn: Optional[sqlite3.Connection] = None
) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        params: list = []
        where_extra = ""
        if up_to_date:
            where_extra += " AND date(je.date) <= date(?)"
            params.append(up_to_date)
        if from_date:
            where_extra += " AND date(je.date) >= date(?)"
            params.append(from_date)

        temp_filter = ""
        if not include_temporary:
            temp_filter = "AND a.is_permanent = 1"

        if period_id is not None:
            where_extra += " AND je.period_id = ?"
            params.append(period_id)

        # Exclude closing entries if requested (for income statement calculations)
        closing_filter = ""
        if exclude_closing:
            closing_filter = "AND (je.is_closing = 0 OR je.is_closing IS NULL)"

        # Exclude adjusting entries if requested (for unadjusted trial balance)
        adjusting_filter = ""
        if exclude_adjusting:
            adjusting_filter = "AND (je.is_adjusting = 0 OR je.is_adjusting IS NULL)"

        # Compute a signed balance then split into non-negative net_debit / net_credit
        # Only include posted entries for accurate balances
        balance_expr = "(COALESCE(SUM(jl.debit),0) - COALESCE(SUM(jl.credit),0))"
        sql = f"""
            SELECT a.id as account_id, a.code, a.name, a.type, a.normal_side,
                   ROUND(CASE WHEN {balance_expr} > 0 THEN {balance_expr} ELSE 0 END, 2) AS net_debit,
                   ROUND(CASE WHEN {balance_expr} < 0 THEN -({balance_expr}) ELSE 0 END, 2) AS net_credit
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jl.entry_id
            WHERE a.is_active = 1 
              AND (je.status = 'posted' OR je.status IS NULL OR je.id IS NULL)
              {temp_filter} {where_extra} {closing_filter} {adjusting_filter}
            GROUP BY a.id, a.code, a.name, a.type, a.normal_side
            ORDER BY a.code
        """
        cur = conn.execute(sql, params)
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def compute_unadjusted_trial_balance(
    *, from_date: Optional[str] = None, up_to_date: Optional[str] = None, include_temporary: bool = True, period_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None
) -> list[sqlite3.Row]:
    """
    Compute unadjusted trial balance by excluding adjusting entries.
    This is a convenience wrapper around compute_trial_balance with exclude_adjusting=True.
    """
    return compute_trial_balance(
        from_date=from_date,
        up_to_date=up_to_date,
        include_temporary=include_temporary,
        period_id=period_id,
        exclude_adjusting=True,
        conn=conn
    )


def fetch_journal(period_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        sql = (
            """
            SELECT je.id as entry_id, je.date, je.description, je.is_adjusting, je.is_closing, je.is_reversing,
                   je.document_ref, je.external_ref,
                   jl.id as line_id, a.code, a.name, jl.debit, jl.credit
            FROM journal_entries je
            JOIN journal_lines jl ON jl.entry_id = je.id
            JOIN accounts a ON a.id = jl.account_id
            {period_clause}
            ORDER BY je.date, je.id, jl.id
            """
        )
        params: list = []
        period_clause = ""
        if period_id is not None:
            period_clause = "WHERE je.period_id = ?"
            params.append(period_id)
        sql = sql.format(period_clause=period_clause)
        cur = conn.execute(sql, params)
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()


def fetch_ledger(period_id: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        sql = (
            """
            SELECT a.id as account_id, a.code, a.name, a.type, a.normal_side,
                   je.date, je.description, jl.debit, jl.credit
            FROM accounts a
            INNER JOIN journal_lines jl ON jl.account_id = a.id
            INNER JOIN journal_entries je ON je.id = jl.entry_id
            WHERE a.is_active = 1 
              AND (je.status = 'posted' OR je.status IS NULL)
              {period_clause}
            ORDER BY a.code, je.date, je.id, jl.id
            """
        )
        params: list = []
        period_clause = ""
        if period_id is not None:
            period_clause = "AND je.period_id = ?"
            params.append(period_id)
        sql = sql.format(period_clause=period_clause)
        cur = conn.execute(sql, params)
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


def create_reversing_template(
    name: str,
    *,
    entry_type: Optional[str] = None,
    required_fields: Optional[Dict[str, Any]] = None,
    default_memo: Optional[str] = None,
    authorization_level: int = 0,
    approval_required: int = 0,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO reversing_entry_templates(name, entry_type, required_fields, default_memo, authorization_level, approval_required)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                entry_type,
                json.dumps(required_fields or {}),
                default_memo,
                int(authorization_level),
                int(approval_required),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()

def list_reversing_templates(*, conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, name, entry_type, required_fields, default_memo, authorization_level, approval_required, is_active FROM reversing_entry_templates ORDER BY name"
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()

def add_reversing_approval(
    queue_id: int,
    reviewer: Optional[str] = None,
    *,
    role: Optional[str] = None,
    level: int = 0,
    status: str = "pending",
    approved_on: Optional[str] = None,
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> int:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO reversing_entry_approvals(queue_id, reviewer, role, level, status, approved_on, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (queue_id, reviewer, role, int(level), status, approved_on, notes),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        if not owned:
            conn.close()

def get_reversing_approvals(queue_id: int, *, conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, reviewer, role, level, status, approved_on, notes FROM reversing_entry_approvals WHERE queue_id=? ORDER BY level, id",
            (queue_id,),
        )
        return cur.fetchall()
    finally:
        if not owned:
            conn.close()

def set_reversing_deadline(item_id: int, deadline_on: str, *, conn: Optional[sqlite3.Connection] = None) -> None:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        prev = conn.execute("SELECT deadline_on FROM reversing_entry_queue WHERE id=?", (item_id,)).fetchone()
        old = prev["deadline_on"] if prev else None
        conn.execute("UPDATE reversing_entry_queue SET deadline_on=? WHERE id=?", (deadline_on, item_id))
        conn.commit()
        conn.execute(
            "INSERT INTO reversing_entry_history(queue_id, field, old_value, new_value) VALUES (?, 'deadline_on', ?, ?)",
            (item_id, old, deadline_on),
        )
        conn.commit()
    finally:
        if not owned:
            conn.close()

def is_reversing_ready(queue_id: int, *, conn: Optional[sqlite3.Connection] = None) -> bool:
    owned = conn is not None
    if not conn:
        conn = get_connection()
    try:
        rq = conn.execute(
            "SELECT approval_required, authorization_level FROM reversing_entry_queue WHERE id=?",
            (queue_id,),
        ).fetchone()
        if not rq:
            return True
        req = int(rq["approval_required"] or 0)
        level_needed = int(rq["authorization_level"] or 0)
        if req == 0:
            return True
        cur = conn.execute(
            "SELECT MIN(level) AS min_level, SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved_count FROM reversing_entry_approvals WHERE queue_id=?",
            (queue_id,),
        )
        row = cur.fetchone()
        if not row:
            return False
        min_level = int(row["min_level"] or 0)
        approved_count = int(row["approved_count"] or 0)
        return approved_count > 0 and min_level <= level_needed
    finally:
        if not owned:
            conn.close()
