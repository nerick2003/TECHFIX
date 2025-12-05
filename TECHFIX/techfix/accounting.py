from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date as _date
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from pathlib import Path
import sqlite3

from . import db


@dataclass
class JournalLine:
    account_id: int
    debit: float = 0.0
    credit: float = 0.0

    def as_tuple(self) -> Tuple[int, float, float]:
        return (self.account_id, float(self.debit), float(self.credit))


class AccountingEngine:
    def __init__(self, conn: Optional[sqlite3.Connection] = None, *, current_user: Optional[str] = None) -> None:
        self._owned = conn is not None
        self.conn = conn or db.get_connection()
        # Simple current user / company context (Phase 1 security model)
        self.current_user_name = current_user or "system"
        # Ensure we have a concrete user row for preference lookups when needed.
        try:
            self.current_user_row = db.get_or_create_default_user(self.conn)
        except Exception:
            self.current_user_row = None
        try:
            db.ensure_default_role_and_user(conn=self.conn)
        except Exception:
            pass
        # Default company and currency context (Phase 5 scaffolding)
        try:
            self.current_company = db.get_company_by_code("DEFAULT", conn=self.conn)
            self.base_currency = (self.current_company["base_currency"] if self.current_company else None) or "PHP"
        except Exception:
            self.current_company = None
            self.base_currency = "PHP"
        self.current_period = db.get_current_period(conn=self.conn)
        if not self.current_period:
            self.current_period = db.ensure_default_period(conn=self.conn)
        self._initialize_cycle_status()

    def set_company_context(self, company_code: str) -> None:
        """
        Switch the active company context for subsequent operations.
        This is scaffolding for future multi-entity support.
        """
        row = db.get_company_by_code(company_code, conn=self.conn)
        if not row:
            raise ValueError(f"Company with code '{company_code}' not found.")
        self.current_company = row
        self.base_currency = (row["base_currency"] or self.base_currency or "PHP")

    def close(self) -> None:
        if not self._owned:
            self.conn.close()

    # Transaction Entry & Journalization
    def record_entry(
        self,
        date: str,
        description: str,
        lines: Iterable[JournalLine],
        *,
        is_adjusting: bool = False,
        is_closing: bool = False,
        is_reversing: bool = False,
        document_ref: Optional[str] = None,
        external_ref: Optional[str] = None,
        memo: Optional[str] = None,
        source_type: Optional[str] = None,
        status: str = "posted",
        created_by: str = "system",
        posted_by: Optional[str] = None,
        period_id: Optional[int] = None,
        attachments: Optional[Sequence[Tuple[str, str]]] = None,
        schedule_reverse_on: Optional[str] = None,
    ) -> int:
        # Validate that entry has at least one line
        line_list = list(lines)
        if not line_list:
            raise ValueError("Journal entry must have at least one line (debit or credit).")
        
        line_tuples = [ln.as_tuple() for ln in line_list]
        period = period_id or self.current_period_id
        # Core validation: ensure an active, open period and a date within bounds (if defined)
        if not period:
            raise RuntimeError("No active accounting period selected.")
        try:
            entry_date = datetime.strptime(date, "%Y-%m-%d").date()
        except Exception:
            raise ValueError("Entry date must be in ISO format YYYY-MM-DD.")

        period_row = db.get_accounting_period_by_id(int(period), conn=self.conn)
        if period_row:
            if int(period_row["is_closed"] or 0) == 1:
                raise RuntimeError("Cannot post entries to a closed accounting period.")
            start = period_row["start_date"]
            end = period_row["end_date"]
            if start:
                try:
                    start_d = _date.fromisoformat(start)
                    if entry_date < start_d:
                        raise RuntimeError("Entry date is before the period start date.")
                except Exception:
                    # If stored date is malformed, skip strict validation
                    pass
            if end:
                try:
                    end_d = _date.fromisoformat(end)
                    if entry_date > end_d:
                        raise RuntimeError("Entry date is after the period end date.")
                except Exception:
                    pass
        # Resolve user / company context, but remain backward compatible
        created_username = created_by or self.current_user_name or "system"
        created_user = None
        company = getattr(self, "current_company", None)
        try:
            created_user = db.get_user_by_username(created_username, conn=self.conn)
        except Exception:
            created_user = None

        entry_id = db.insert_journal_entry(
            date,
            description,
            line_tuples,
            is_adjusting=1 if is_adjusting else 0,
            is_closing=1 if is_closing else 0,
            is_reversing=1 if is_reversing else 0,
            document_ref=document_ref,
            external_ref=external_ref,
            memo=memo,
            source_type=source_type,
            status=status,
            created_by=created_username,
            posted_by=posted_by,
            period_id=period,
            company_id=int(company["id"]) if company else None,
            created_by_user_id=int(created_user["id"]) if created_user else None,
            posted_by_user_id=None,
            conn=self.conn,
        )
        if attachments:
            for label, path in attachments:
                if path:
                    db.add_source_document(entry_id, path, label=label, conn=self.conn)
        if schedule_reverse_on:
            db.schedule_reversing_entry(entry_id, schedule_reverse_on, conn=self.conn)
        self._update_cycle_status_after_entry(
            is_adjusting=is_adjusting,
            is_closing=is_closing,
            status=status,
        )
        return entry_id

    # --- High-level AR/AP helpers ---------------------------------------------------

    def create_customer(
        self,
        name: str,
        code: str,
        *,
        contact: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> int:
        """Create a customer in the subledger."""
        return db.create_customer(
            name,
            code,
            contact=contact,
            email=email,
            phone=phone,
            conn=self.conn,
        )

    def create_vendor(
        self,
        name: str,
        code: str,
        *,
        contact: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> int:
        """Create a vendor in the subledger."""
        return db.create_vendor(
            name,
            code,
            contact=contact,
            email=email,
            phone=phone,
            conn=self.conn,
        )

    def record_sale_on_account(
        self,
        date: str,
        customer_id: int,
        amount: float,
        *,
        description: str = "Sale on account",
        ar_account_name: str = "Accounts Receivable",
        revenue_account_name: str = "Service Income",
        invoice_no: Optional[str] = None,
        due_date: Optional[str] = None,
        memo: Optional[str] = None,
    ) -> int:
        """
        Convenience helper: create a simple sale on account and link a sales invoice.
        Debit Accounts Receivable, credit Service Income.
        """
        ar_acc = db.get_account_by_name(ar_account_name, self.conn)
        rev_acc = db.get_account_by_name(revenue_account_name, self.conn)
        if not ar_acc or not rev_acc:
            raise RuntimeError("Required accounts not found for sale on account.")
        entry_id = self.record_entry(
            date,
            description,
            [
                JournalLine(account_id=ar_acc["id"], debit=amount),
                JournalLine(account_id=rev_acc["id"], credit=amount),
            ],
            memo=memo,
            status="posted",
        )
        db.create_sales_invoice(
            customer_id,
            entry_id,
            date,
            amount,
            invoice_no=invoice_no,
            due_date=due_date,
            conn=self.conn,
        )
        return entry_id

    def record_bill_on_account(
        self,
        date: str,
        vendor_id: int,
        amount: float,
        *,
        description: str = "Bill on account",
        ap_account_name: str = "Accounts Payable",
        expense_account_name: str = "Rent Expense",
        bill_no: Optional[str] = None,
        due_date: Optional[str] = None,
        memo: Optional[str] = None,
    ) -> int:
        """
        Convenience helper: create a simple bill on account and link a purchase bill.
        Debit an expense, credit Accounts Payable.
        """
        ap_acc = db.get_account_by_name(ap_account_name, self.conn)
        exp_acc = db.get_account_by_name(expense_account_name, self.conn)
        if not ap_acc or not exp_acc:
            raise RuntimeError("Required accounts not found for bill on account.")
        entry_id = self.record_entry(
            date,
            description,
            [
                JournalLine(account_id=exp_acc["id"], debit=amount),
                JournalLine(account_id=ap_acc["id"], credit=amount),
            ],
            memo=memo,
            status="posted",
        )
        db.create_purchase_bill(
            vendor_id,
            entry_id,
            date,
            amount,
            bill_no=bill_no,
            due_date=due_date,
            conn=self.conn,
        )
        return entry_id

    # Adjusting Entries helpers
    def adjust_supplies_used(self, date: str, remaining_supplies_amount: float) -> Optional[int]:
        acc_supplies = db.get_account_by_name("Supplies", self.conn)
        acc_supplies_exp = db.get_account_by_name("Supplies Expense", self.conn)
        if not acc_supplies or not acc_supplies_exp:
            return None
        # Compute current balance in Supplies (debit minus credit)
        # Only include posted entries from current period for accurate calculation
        params = [acc_supplies["id"]]
        period_filter = ""
        if self.current_period_id:
            period_filter = " AND (je.period_id = ? OR je.period_id IS NULL)"
            params.append(self.current_period_id)
        
        cur = self.conn.execute(
            f"""
            SELECT COALESCE(SUM(debit) - SUM(credit), 0) AS balance
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.account_id = ?
              AND (je.status = 'posted' OR je.status IS NULL)
              {period_filter}
            """,
            tuple(params),
        )
        current_balance = float(cur.fetchone()["balance"])
        used = round(current_balance - remaining_supplies_amount, 2)
        if used <= 0:
            return None
        return self.record_entry(
            date,
            "Adjust supplies used",
            [
                JournalLine(account_id=acc_supplies_exp["id"], debit=used),
                JournalLine(account_id=acc_supplies["id"], credit=used),
            ],
            is_adjusting=True,
            memo="System-generated supplies adjustment",
        )

    def adjust_prepaid_to_expense(self, date: str, prepaid_name: str, expense_name: str, amount: float) -> Optional[int]:
        acc_prepaid = db.get_account_by_name(prepaid_name, self.conn)
        acc_expense = db.get_account_by_name(expense_name, self.conn)
        if not acc_prepaid or not acc_expense:
            return None
        return self.record_entry(
            date,
            f"Amortize {prepaid_name}",
            [
                JournalLine(account_id=acc_expense["id"], debit=amount),
                JournalLine(account_id=acc_prepaid["id"], credit=amount),
            ],
            is_adjusting=True,
            memo=f"Amortization of {prepaid_name}",
        )

    def adjust_depreciation(self, date: str, asset_name: str, contra_name: str, amount: float) -> Optional[int]:
        acc_exp = db.get_account_by_name("Depreciation Expense", self.conn)
        acc_contra = db.get_account_by_name(contra_name, self.conn)
        if not acc_exp or not acc_contra:
            return None
        return self.record_entry(
            date,
            f"Record depreciation for {asset_name}",
            [
                JournalLine(account_id=acc_exp["id"], debit=amount),
                JournalLine(account_id=acc_contra["id"], credit=amount),
            ],
            is_adjusting=True,
            memo=f"Monthly depreciation for {asset_name}",
        )

    # Closing Entries
    def make_closing_entries(self, date: str) -> List[int]:
        entry_ids: List[int] = []
        cur = self.conn.execute(
            "SELECT id, name, type FROM accounts WHERE type IN ('Revenue','Expense') AND is_active=1"
        )
        accounts = cur.fetchall()
        if not accounts:
            return entry_ids

        capital = db.get_account_by_name("Owner's Capital", self.conn)
        if not capital:
            return entry_ids
        capital_id = capital["id"]

        # Close Revenues (handle both normal and unexpected balances)
        # Exclude closing entries and reversing entries to prevent double-counting
        # Only include posted entries for accurate calculation
        cur = self.conn.execute(
            """
            SELECT a.id, a.name, ROUND(COALESCE(SUM(jl.credit) - SUM(jl.debit),0),2) AS balance
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jl.entry_id
            WHERE a.type = 'Revenue' 
              AND a.is_active=1 
              AND je.period_id = ?
              AND (je.status = 'posted' OR je.status IS NULL)
              AND (je.is_closing = 0 OR je.is_closing IS NULL)
              AND (je.is_reversing = 0 OR je.is_reversing IS NULL)
            GROUP BY a.id, a.code, a.name
            HAVING ABS(balance) > 0.005
            """,
            (self.current_period_id,),
        )
        revenue_balances = cur.fetchall()
        for r in revenue_balances:
            balance = float(r["balance"])
            if balance >= 0:
                # Normal revenue (credit balance): debit revenue, credit capital
                entry_ids.append(
                    self.record_entry(
                        date,
                        "Close revenue to capital",
                        [
                            JournalLine(account_id=r["id"], debit=balance),
                            JournalLine(account_id=capital_id, credit=balance),
                        ],
                        is_closing=True,
                        memo="System closing of revenue accounts",
                    )
                )
            else:
                # Unexpected debit balance on revenue: credit revenue, debit capital
                amt = abs(balance)
                entry_ids.append(
                    self.record_entry(
                        date,
                        "Close (reverse-sign) revenue to capital",
                        [
                            JournalLine(account_id=capital_id, debit=amt),
                            JournalLine(account_id=r["id"], credit=amt),
                        ],
                        is_closing=True,
                        memo="System closing of revenue accounts (reverse-sign)",
                    )
                )

        # Close Expenses (handle both debit and unexpected credit balances)
        # Exclude closing entries and reversing entries to prevent double-counting
        # Only include posted entries for accurate calculation
        cur = self.conn.execute(
            """
            SELECT a.id, a.name, ROUND(COALESCE(SUM(jl.debit) - SUM(jl.credit),0),2) AS balance
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jl.entry_id
            WHERE a.type = 'Expense' 
              AND a.is_active=1 
              AND je.period_id = ?
              AND (je.status = 'posted' OR je.status IS NULL)
              AND (je.is_closing = 0 OR je.is_closing IS NULL)
              AND (je.is_reversing = 0 OR je.is_reversing IS NULL)
            GROUP BY a.id, a.code, a.name
            HAVING ABS(balance) > 0.005
            """,
            (self.current_period_id,),
        )
        expense_balances = cur.fetchall()
        for e in expense_balances:
            balance = float(e["balance"])
            if balance > 0:
                # Normal expense debit balance: debit capital, credit expense
                entry_ids.append(
                    self.record_entry(
                        date,
                        "Close expenses to capital",
                        [
                            JournalLine(account_id=capital_id, debit=balance),
                            JournalLine(account_id=e["id"], credit=balance),
                        ],
                        is_closing=True,
                        memo="System closing of expense accounts",
                    )
                )
            else:
                # Unexpected credit balance on expense: debit expense, credit capital
                amt = abs(balance)
                entry_ids.append(
                    self.record_entry(
                        date,
                        "Close (reverse-sign) expense to capital",
                        [
                            JournalLine(account_id=e["id"], debit=amt),
                            JournalLine(account_id=capital_id, credit=amt),
                        ],
                        is_closing=True,
                        memo="System closing of expense accounts (reverse-sign)",
                    )
                )

        # Close Drawings (if present) to Capital
        # Exclude closing entries to prevent double-counting
        # Only include posted entries for accurate calculation
        drawings = db.get_account_by_name("Owner's Drawings", self.conn)
        if drawings:
            cur = self.conn.execute(
                """
                SELECT ROUND(COALESCE(SUM(debit) - SUM(credit),0),2) AS balance
                FROM journal_lines jl
                JOIN journal_entries je ON je.id = jl.entry_id
                WHERE jl.account_id = ? 
                  AND je.period_id = ?
                  AND (je.status = 'posted' OR je.status IS NULL)
                  AND (je.is_closing = 0 OR je.is_closing IS NULL)
                """,
                (drawings["id"], self.current_period_id),
            )
            bal = float(cur.fetchone()["balance"])
            if bal > 0.005:
                entry_ids.append(
                    self.record_entry(
                        date,
                        "Close drawings to capital",
                        [
                            JournalLine(account_id=capital_id, debit=bal),
                            JournalLine(account_id=drawings["id"], credit=bal),
                        ],
                        is_closing=True,
                        memo="System closing of drawings",
                    )
                )

        if self.current_period_id:
            db.set_cycle_step_status(
                self.current_period_id,
                8,
                "completed" if entry_ids else "pending",
                note="Closing entries posted" if entry_ids else "No closing entries required",
                conn=self.conn,
            )
            db.set_cycle_step_status(
                self.current_period_id,
                9,
                "in_progress",
                note="Ready to prepare post-closing trial balance",
                conn=self.conn,
            )
        return entry_ids

    # Reversing Entries (simple generic)
    def reverse_entry(self, entry_id: int, date: str) -> Optional[int]:
        cur = self.conn.execute(
            """
            SELECT account_id, debit, credit
            FROM journal_lines WHERE entry_id = ?
            """,
            (entry_id,),
        )
        lines = cur.fetchall()
        if not lines:
            return None
        reversed_lines = [
            JournalLine(account_id=ln["account_id"], debit=ln["credit"], credit=ln["debit"]) for ln in lines
        ]
        return self.record_entry(
            date,
            f"Reversing entry for #{entry_id}",
            reversed_lines,
            is_reversing=True,
            memo=f"Auto-reversal of entry #{entry_id}",
        )

    def process_reversing_schedule(self, as_of: Optional[str] = None) -> List[int]:
        created: List[int] = []
        if not self.current_period_id:
            return created
        try:
            rows = db.list_reversing_queue(self.current_period_id, conn=self.conn)
            cutoff = as_of or datetime.utcnow().date().isoformat()
            for r in rows:
                try:
                    status = r['status'] if 'status' in r.keys() else 'pending'
                    when = r['reverse_on'] if 'reverse_on' in r.keys() else None
                    deadline = r['deadline_on'] if 'deadline_on' in r.keys() else None
                    reminder = r['reminder_on'] if 'reminder_on' in r.keys() else None
                    qid = int(r['id']) if 'id' in r.keys() else None
                    if status != 'pending' or not when:
                        continue
                    if str(when) > str(cutoff):
                        continue
                    if reminder and str(reminder) <= str(cutoff) and qid:
                        db.log_audit(action='reversing_reminder', details=f"queue:{qid} reverse_on:{when}", user='system', conn=self.conn)
                    ready = True
                    if qid:
                        ready = db.is_reversing_ready(qid, conn=self.conn)
                    if not ready:
                        continue
                    eid = int(r['original_entry_id'])
                    rid = self.reverse_entry(eid, when)
                    if rid:
                        created.append(int(rid))
                        db.update_reversing_status(int(r['id']), 'completed', reversed_entry_id=int(rid), conn=self.conn)
                        if deadline and str(deadline) < str(cutoff):
                            db.log_audit(action='reversing_past_deadline', details=f"queue:{qid} reversed:{rid}", user='system', conn=self.conn)
                except Exception:
                    pass
            if created:
                db.set_cycle_step_status(self.current_period_id, 10, 'completed', note='Reversing entries posted', conn=self.conn)
            return created
        except Exception:
            return created

    def apply_reversing_template(self, entry_id: int, template_id: int, reverse_on: str, *, memo: Optional[str] = None, notes: Optional[str] = None) -> int:
        tpl_rows = db.list_reversing_templates(conn=self.conn)
        tpl = next((t for t in tpl_rows if int(t['id']) == int(template_id)), None)
        if not tpl:
            return db.schedule_reversing_entry(entry_id, reverse_on, conn=self.conn)
        return db.schedule_reversing_entry(
            entry_id,
            reverse_on,
            deadline_on=reverse_on,
            entry_type=tpl['entry_type'],
            template_id=int(tpl['id']),
            priority='normal',
            reminder_on=reverse_on,
            notes=notes or memo or tpl['default_memo'],
            approval_required=int(tpl['approval_required'] or 0),
            authorization_level=int(tpl['authorization_level'] or 0),
            conn=self.conn,
        )

    def generate_reversing_report(self, as_of: Optional[str] = None) -> Dict[str, object]:
        if not self.current_period_id:
            return {"error": "No active period"}
        rows = db.list_reversing_queue(self.current_period_id, conn=self.conn)
        today = as_of or datetime.utcnow().date().isoformat()
        pending = [r for r in rows if r['status'] == 'pending']
        overdue = [r for r in pending if r['deadline_on'] and str(r['deadline_on']) < str(today)]
        awaiting_approval = []
        for r in pending:
            qid = int(r['id'])
            if int(r['approval_required'] or 0) == 1 and not db.is_reversing_ready(qid, conn=self.conn):
                awaiting_approval.append(r)
        completed = [r for r in rows if r['status'] == 'completed']
        summary = {
            'pending': len(pending),
            'completed': len(completed),
            'overdue': len(overdue),
            'awaiting_approval': len(awaiting_approval),
        }
        return {'summary': summary, 'pending': pending, 'overdue': overdue, 'awaiting_approval': awaiting_approval, 'completed': completed}

    def export_reversing_report_csv(self, output_path: str, as_of: Optional[str] = None) -> None:
        report = self.generate_reversing_report(as_of)
        rows = []
        for section in ('pending', 'overdue', 'awaiting_approval', 'completed'):
            for r in report.get(section, []):
                rows.append((section, r['id'], r['original_entry_id'], r['reverse_on'], r['deadline_on'], r['status'], r['entry_type'], r['priority']))
        db.export_rows_to_csv(rows, headers=['section','id','original_entry_id','reverse_on','deadline_on','status','entry_type','priority'], output_path=Path(output_path))

    def export_reversing_report_excel(self, output_path: str, as_of: Optional[str] = None) -> None:
        report = self.generate_reversing_report(as_of)
        rows = []
        for section in ('pending', 'overdue', 'awaiting_approval', 'completed'):
            for r in report.get(section, []):
                rows.append((section, r['id'], r['original_entry_id'], r['reverse_on'], r['deadline_on'], r['status'], r['entry_type'], r['priority']))
        db.export_rows_to_excel(rows, headers=['section','id','original_entry_id','reverse_on','deadline_on','status','entry_type','priority'], output_path=Path(output_path), sheet_name='Reversing Report')

    @property
    def current_period_id(self) -> Optional[int]:
        if self.current_period:
            return int(self.current_period["id"])
        return None

    def refresh_current_period(self) -> None:
        self.current_period = db.get_current_period(conn=self.conn)
        if not self.current_period:
            self.current_period = db.ensure_default_period(conn=self.conn)

    def set_active_period(self, period_id: int) -> None:
        db.set_current_period(period_id, conn=self.conn)
        self.refresh_current_period()
        self._initialize_cycle_status()

    def create_period(
        self,
        name: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        make_current: bool = True,
    ) -> int:
        period_id = db.create_period(
            name,
            start_date=start_date,
            end_date=end_date,
            conn=self.conn,
        )
        if make_current:
            self.set_active_period(period_id)
        return period_id

    def list_periods(self) -> List[sqlite3.Row]:
        periods = db.list_accounting_periods(conn=self.conn)
        return list(periods)

    def get_cycle_status(self) -> List[sqlite3.Row]:
        if not self.current_period_id:
            return []
        return list(db.get_cycle_status(self.current_period_id, conn=self.conn))

    def set_cycle_step_status(self, step: int, status: str, note: Optional[str] = None) -> None:
        if not self.current_period_id:
            return
        # When marking a step completed, ensure previous steps are at least completed
        try:
            if status == 'completed':
                rows = list(db.get_cycle_status(self.current_period_id, conn=self.conn))
                for r in rows:
                    if r['step'] < step and r['status'] != 'completed':
                        db.set_cycle_step_status(self.current_period_id, r['step'], 'completed', note='Auto-completed (prerequisite)', conn=self.conn)
        except Exception:
            # Don't let auxiliary step-fixing block the main update
            pass
        db.set_cycle_step_status(self.current_period_id, step, status, note, conn=self.conn)

    def capture_trial_balance_snapshot(self, stage: str, as_of: str, rows) -> int:
        if not self.current_period_id:
            raise RuntimeError("No active accounting period selected.")
        data = [({k: r[k] for k in r.keys()} if isinstance(r, sqlite3.Row) else r) for r in rows]
        return db.capture_trial_balance_snapshot(
            self.current_period_id,
            stage,
            as_of,
            data,
            conn=self.conn,
        )

    def get_trial_balance_snapshots(self, stage: Optional[str] = None) -> List[sqlite3.Row]:
        if not self.current_period_id:
            return []
        return list(db.get_trial_balance_snapshots(self.current_period_id, stage, conn=self.conn))

    # --- Financial reporting helpers -------------------------------------------------

    def generate_trial_balance_report(
        self,
        as_of: str,
        *,
        include_temporary: bool = True,
    ) -> Dict[str, object]:
        """
        Build a structured trial balance report as of a date.
        Returns rows plus total debits / credits and the difference.
        """
        rows = db.compute_trial_balance(
            up_to_date=as_of,
            include_temporary=include_temporary,
            period_id=self.current_period_id,
            conn=self.conn,
        )
        total_debits = sum(float(r["net_debit"] or 0.0) for r in rows)
        total_credits = sum(float(r["net_credit"] or 0.0) for r in rows)
        diff = round(total_debits - total_credits, 2)
        return {
            "as_of": as_of,
            "include_temporary": include_temporary,
            "rows": rows,
            "total_debits": round(total_debits, 2),
            "total_credits": round(total_credits, 2),
            "difference": diff,
        }

    def generate_income_statement(self, start_date: str, end_date: str, *, period_id: Optional[int] = None) -> Dict[str, object]:
        """
        Simple income statement for a date range based on trial balance activity.
        Uses revenue and expense accounts only.
        
        Args:
            start_date: Start date for the income statement
            end_date: End date for the income statement
            period_id: Optional period ID to filter by. If None, uses current_period_id.
                       If you want to include entries from all periods, pass period_id=None
                       explicitly after ensuring date ranges are set.
        """
        # If period_id is explicitly None, don't filter by period (allows cross-period reporting)
        # Otherwise, use current_period_id as default
        filter_period_id = period_id if period_id is not None else self.current_period_id
        
        rows = db.compute_trial_balance(
            from_date=start_date,
            up_to_date=end_date,
            include_temporary=True,
            period_id=filter_period_id,
            exclude_closing=True,  # Exclude closing entries to show revenue/expenses before closing
            conn=self.conn,
        )
        revenue_items: List[Dict[str, object]] = []
        expense_items: List[Dict[str, object]] = []
        total_revenue = 0.0
        total_expense = 0.0
        for r in rows:
            acc_type = (r["type"] or "").lower()
            net_debit = float(r["net_debit"] or 0.0)
            net_credit = float(r["net_credit"] or 0.0)
            if acc_type == "revenue":
                # Revenue accounts: credit balance increases revenue
                amount = round(net_credit - net_debit, 2)
                if abs(amount) > 0.005:
                    revenue_items.append(
                        {
                            "code": r["code"],
                            "name": r["name"],
                            "amount": amount,  # Positive for revenue, negative for contra-revenue
                        }
                    )
                    total_revenue += amount
            elif acc_type == "contra revenue":
                # Contra-revenue accounts (e.g., Sales Returns, Sales Discounts)
                # have debit balances and reduce revenue
                amount = round(net_debit - net_credit, 2)
                if abs(amount) > 0.005:
                    revenue_items.append(
                        {
                            "code": r["code"],
                            "name": r["name"],
                            "amount": -abs(amount),  # Always show as negative
                        }
                    )
                    total_revenue -= abs(amount)  # Subtract from total revenue
            elif acc_type == "expense":
                amount = round(net_debit - net_credit, 2)
                if abs(amount) > 0.005:
                    expense_items.append(
                        {
                            "code": r["code"],
                            "name": r["name"],
                            "amount": amount,
                        }
                    )
                    total_expense += amount
        total_revenue = round(total_revenue, 2)
        total_expense = round(total_expense, 2)
        net_income = round(total_revenue - total_expense, 2)
        return {
            "start_date": start_date,
            "end_date": end_date,
            "revenues": revenue_items,
            "expenses": expense_items,
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "net_income": net_income,
        }

    def generate_balance_sheet(self, as_of: str) -> Dict[str, object]:
        """
        Simple balance sheet as of a date using permanent accounts only.
        """
        rows = db.compute_trial_balance(
            up_to_date=as_of,
            include_temporary=False,
            period_id=self.current_period_id,
            conn=self.conn,
        )
        assets: List[Dict[str, object]] = []
        liabilities: List[Dict[str, object]] = []
        equity: List[Dict[str, object]] = []
        total_assets = 0.0
        total_liabilities = 0.0
        total_equity = 0.0

        for r in rows:
            acc_type = (r["type"] or "").lower()
            net_debit = float(r["net_debit"] or 0.0)
            net_credit = float(r["net_credit"] or 0.0)
            
            if acc_type == "asset":
                # Assets have debit balances (positive)
                balance = net_debit - net_credit
                amount = round(balance, 2)
                if abs(amount) <= 0.005:
                    continue
                # Handle negative asset balances (shouldn't happen normally, but can occur)
                # Negative balances reduce total assets
                line = {
                    "code": r["code"],
                    "name": r["name"],
                    "amount": amount,  # Can be negative
                }
                assets.append(line)
                total_assets += amount  # Add the amount (negative if balance is negative)
            elif acc_type == "contra asset":
                # Contra assets have credit balances and reduce asset value
                # Use credit balance directly: net_credit - net_debit
                # This gives us the amount to subtract from total assets
                credit_balance = net_credit - net_debit
                amount = round(credit_balance, 2)
                if abs(amount) <= 0.005:
                    continue
                contra_line = {
                    "code": r["code"],
                    "name": r["name"],
                    "amount": -amount,  # Show as negative (reduces assets)
                }
                assets.append(contra_line)
                total_assets -= amount  # Subtract credit balance from total assets
            elif acc_type == "liability":
                # Liabilities have credit balances (positive on balance sheet)
                balance = net_credit - net_debit
                amount = round(balance, 2)
                
                # If liability has a debit balance (overpayment), treat as prepaid asset
                if amount < 0:
                    # This is an overpayment - treat as prepaid asset
                    prepaid_amount = abs(amount)
                    prepaid_line = {
                        "code": r["code"],
                        "name": f"Prepaid ({r['name']})",
                        "amount": prepaid_amount,
                    }
                    assets.append(prepaid_line)
                    total_assets += prepaid_amount
                    # Don't include in liabilities
                    continue
                
                if abs(amount) <= 0.005:
                    continue
                line = {
                    "code": r["code"],
                    "name": r["name"],
                    "amount": amount,
                }
                liabilities.append(line)
                total_liabilities += amount
            elif acc_type == "equity":
                account_name = r["name"]
                
                # Special handling for Owner's Drawings - it should REDUCE equity, not increase it
                # Drawings have debit balances (positive), so they reduce the credit balance of equity
                # Check for drawings FIRST before calculating normal balance
                if "drawing" in account_name.lower() or "withdrawal" in account_name.lower():
                    # Drawings have debit balances, so net_debit - net_credit gives us the drawings amount
                    drawings_amount = round(net_debit - net_credit, 2)
                    if abs(drawings_amount) > 0.005:
                        line = {
                            "code": r["code"],
                            "name": account_name,
                            "amount": -abs(drawings_amount),  # Show as NEGATIVE to indicate it reduces equity
                        }
                        equity.append(line)
                        total_equity -= drawings_amount  # Subtract drawings from total equity
                    # Skip normal processing for drawings
                    continue
                
                # For Owner's Capital and other equity accounts (NOT drawings)
                # Equity has credit balances (positive on balance sheet)
                balance = net_credit - net_debit
                amount = round(balance, 2)
                if abs(amount) <= 0.005:
                    continue
                
                line = {
                    "code": r["code"],
                    "name": account_name,
                    "amount": amount,
                }
                equity.append(line)
                total_equity += amount

        total_assets = round(total_assets, 2)
        total_liabilities = round(total_liabilities, 2)
        total_equity = round(total_equity, 2)

        # Balance check: Assets = Liabilities + Equity
        # Expanded form: Assets = Liabilities + Owner's Capital + Revenues - Expenses - Withdrawals
        # After closing entries, Revenues, Expenses, and Withdrawals are zero (closed to Capital)
        # So: Assets - (Liabilities + Equity) = 0
        balance_check = round(total_assets - (total_liabilities + total_equity), 2)

        return {
            "as_of": as_of,
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "balance_check": balance_check,
        }

    def generate_cash_flow(self, start_date: str, end_date: str) -> Dict[str, object]:
        """
        Generate a simple cash flow classification between start_date and end_date (inclusive).

        Approach (simple/direct classification):
        - For each journal entry in the date range, find lines that affect the Cash account.
        - For each cash line, classify the cash movement by the type of the other accounts in the same entry:
          - Asset / Contra Asset -> Investing
          - Liability / Equity -> Financing
          - Revenue / Expense -> Operating
          - Fallback -> Operating

        Returns a dict containing items and totals per section.
        """
        # Find cash account id
        cash_acc = db.get_account_by_name("Cash", conn=self.conn)
        if not cash_acc:
            return {"error": "Cash account not found"}
        cash_id = int(cash_acc["id"])

        clause = " AND je.period_id = ?" if self.current_period_id else ""
        params = [start_date, end_date] + ([int(self.current_period_id)] if self.current_period_id else [])
        sql = (
            """
            SELECT je.id AS entry_id, je.date AS date
            FROM journal_entries je
            WHERE date(je.date) BETWEEN date(?) AND date(?)
              AND (je.status = 'posted' OR je.status IS NULL)
            """
            + clause
            + """
            ORDER BY je.date, je.id
            """
        )
        cur = self.conn.execute(sql, params)
        entries = [r["entry_id"] for r in cur.fetchall()]

        sections = {"Operating": [], "Investing": [], "Financing": []}
        totals = {"Operating": 0.0, "Investing": 0.0, "Financing": 0.0}

        for eid in entries:
            lines = list(self.conn.execute(
                "SELECT account_id, debit, credit FROM journal_lines WHERE entry_id=?",
                (eid,)
            ).fetchall())
            cash_lines = [l for l in lines if int(l["account_id"]) == cash_id and (l["debit"] or l["credit"])]
            if not cash_lines:
                continue
            non_cash_lines = [l for l in lines if int(l["account_id"]) != cash_id and (l["debit"] or l["credit"])]
            for cl in cash_lines:
                amt = float(cl["debit"] or 0) - float(cl["credit"] or 0)
                klass = "Operating"  # Default classification
                
                if non_cash_lines:
                    # Analyze all non-cash accounts to determine classification
                    # Use weighted classification based on transaction amounts
                    account_type_amounts = {}
                    for line in non_cash_lines:
                        other_id = int(line["account_id"])
                        acct = self.conn.execute("SELECT type FROM accounts WHERE id=?", (other_id,)).fetchone()
                        if acct:
                            acct_type = acct["type"]
                            line_amt = abs(float(line["debit"] or 0) - float(line["credit"] or 0))
                            if acct_type not in account_type_amounts:
                                account_type_amounts[acct_type] = 0.0
                            account_type_amounts[acct_type] += line_amt
                    
                    # Classify based on dominant account type by amount
                    if account_type_amounts:
                        # Priority: Investing > Financing > Operating
                        investing_total = account_type_amounts.get("Asset", 0) + account_type_amounts.get("Contra Asset", 0)
                        financing_total = account_type_amounts.get("Liability", 0) + account_type_amounts.get("Equity", 0)
                        operating_total = account_type_amounts.get("Revenue", 0) + account_type_amounts.get("Expense", 0)
                        
                        if investing_total > financing_total and investing_total > operating_total:
                            klass = "Investing"
                        elif financing_total > operating_total:
                            klass = "Financing"
                        # else: Operating (default)
                
                sections[klass].append({
                    "entry_id": eid,
                    "date": self.conn.execute("SELECT date FROM journal_entries WHERE id=?", (eid,)).fetchone()["date"],
                    "amount": round(amt, 2),
                })
                totals[klass] = round(totals[klass] + amt, 2)

        net = round(sum(totals.values()), 2)
        return {"sections": sections, "totals": totals, "net_change_in_cash": net, "start": start_date, "end": end_date}

    def list_adjustment_requests(self) -> List[sqlite3.Row]:
        if not self.current_period_id:
            return []
        return list(db.list_adjustment_requests(self.current_period_id, conn=self.conn))

    def create_adjustment_request(
        self,
        description: str,
        *,
        requested_on: Optional[str] = None,
        requested_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        if not self.current_period_id:
            raise RuntimeError("No active accounting period selected.")
        return db.create_adjustment_request(
            self.current_period_id,
            description,
            requested_on=requested_on,
            requested_by=requested_by,
            notes=notes,
            conn=self.conn,
        )

    def link_adjustment_to_entry(
        self,
        adjustment_id: int,
        entry_id: int,
        *,
        approved_by: Optional[str] = None,
        approved_on: Optional[str] = None,
        status: str = "posted",
    ) -> None:
        db.link_adjustment_to_entry(
            adjustment_id,
            entry_id,
            approved_by=approved_by,
            approved_on=approved_on,
            status=status,
            conn=self.conn,
        )
        if self.current_period_id:
            db.set_cycle_step_status(
                self.current_period_id,
                5,
                "completed",
                note="Adjusting entries approved",
                conn=self.conn,
            )
            db.set_cycle_step_status(
                self.current_period_id,
                6,
                "in_progress",
                note="Adjusted trial balance ready",
                conn=self.conn,
            )

    def list_reversing_queue(self) -> List[sqlite3.Row]:
        return list(db.list_reversing_queue(self.current_period_id, conn=self.conn))

    def update_adjustment_status(self, adjustment_id: int, status: str, notes: Optional[str] = None) -> None:
        db.update_adjustment_status(adjustment_id, status, notes=notes, conn=self.conn)

    def diagnose_supplies_account_issue(self) -> Dict[str, object]:
        """
        Diagnose the Supplies account credit balance issue.
        Returns a dictionary with details about the issue and recommendations.
        
        Common issue: An adjusting entry credited Supplies, but Supplies had no
        debit balance because purchases were recorded to Supplies Expense instead.
        OR adjusting entries were incorrectly entered with Supplies as credit account.
        """
        if not self.current_period_id:
            return {"error": "No active accounting period selected"}
        
        supplies = db.get_account_by_name("Supplies", self.conn)
        if not supplies:
            return {"error": "Supplies account not found"}
        
        supplies_id = supplies['id']
        
        # Get current balance
        cur = self.conn.execute("""
            SELECT 
                COALESCE(SUM(jl.debit), 0) as total_debit,
                COALESCE(SUM(jl.credit), 0) as total_credit,
                COALESCE(SUM(jl.debit), 0) - COALESCE(SUM(jl.credit), 0) as balance
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.account_id = ?
              AND je.period_id = ?
              AND (je.status = 'posted' OR je.status IS NULL)
        """, (supplies_id, self.current_period_id))
        
        result = cur.fetchone()
        total_debit = float(result['total_debit'] or 0)
        total_credit = float(result['total_credit'] or 0)
        balance = float(result['balance'] or 0)
        
        # Find all entries affecting Supplies
        cur = self.conn.execute("""
            SELECT je.id, je.date, je.description, je.is_adjusting, je.document_ref,
                   jl.debit, jl.credit
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.account_id = ?
              AND je.period_id = ?
              AND (je.status = 'posted' OR je.status IS NULL)
            ORDER BY je.date, je.id
        """, (supplies_id, self.current_period_id))
        
        entries = cur.fetchall()
        
        # Find problematic adjusting entries and determine what account should have been used
        problematic_entries = []
        account_corrections = {
            "Depreciation expense": "Accumulated Depreciation",
            "Accrued utilities expense": "Utilities Payable",
            "Accrued salaries expense": "SSS, PhilHealth, and Pag-Ibig Payable",
            "Accrued percentage tax": "Accrued Percentage Tax Payable",
        }
        
        for entry in entries:
            if entry['is_adjusting'] and float(entry['credit'] or 0) > 0:
                # Determine what account should have been credited based on description
                correct_account = None
                desc_lower = (entry['description'] or '').lower()
                for key, correct_acc in account_corrections.items():
                    if key.lower() in desc_lower:
                        correct_account = correct_acc
                        break
                
                problematic_entries.append({
                    "entry_id": entry['id'],
                    "date": entry['date'],
                    "description": entry['description'],
                    "document_ref": entry['document_ref'],
                    "credit_amount": float(entry['credit'] or 0),
                    "should_credit": correct_account or "Unknown (check original entry)",
                })
        
        has_issue = balance < 0
        
        return {
            "account_id": supplies_id,
            "account_name": "Supplies",
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance": balance,
            "has_issue": has_issue,
            "total_entries": len(entries),
            "problematic_entries": problematic_entries,
            "recommendation": (
                "These adjusting entries incorrectly credited Supplies. "
                "They should credit different accounts. Delete and re-enter with correct accounts."
                if has_issue and problematic_entries
                else "No issue found" if not has_issue
                else "Check entries affecting Supplies account"
            ),
        }

    def fix_supplies_account_entries(self, dry_run: bool = True) -> Dict[str, object]:
        """
        Fix adjusting entries that incorrectly credit Supplies account.
        
        This method:
        1. Identifies adjusting entries that incorrectly credit Supplies
        2. Gets all lines from those entries
        3. Replaces the Supplies credit with the correct account
        4. Deletes the incorrect entry and recreates it with the fix
        
        Args:
            dry_run: If True, only return what would be fixed without making changes
            
        Returns:
            Dictionary with:
            - fixed_count: Number of entries fixed
            - total_entries: Total problematic entries found
            - errors: List of errors encountered
            - fixed_entries: List of entry IDs that were fixed (entry_id -> new_entry_id)
        """
        if not self.current_period_id:
            return {"error": "No active accounting period selected"}
        
        # Get diagnosis
        diagnosis = self.diagnose_supplies_account_issue()
        
        if diagnosis.get('error'):
            return diagnosis
        
        if not diagnosis.get('has_issue') or not diagnosis.get('problematic_entries'):
            return {
                "fixed_count": 0,
                "total_entries": 0,
                "errors": [],
                "fixed_entries": {},
                "message": "No problematic entries found. Supplies account is fine."
            }
        
        problematic_entries = diagnosis['problematic_entries']
        supplies_account = db.get_account_by_name("Supplies", self.conn)
        if not supplies_account:
            return {"error": "Supplies account not found"}
        
        supplies_id = supplies_account['id']
        
        # Process each problematic entry
        fixed_count = 0
        errors = []
        fixed_entries = {}
        
        for entry_info in problematic_entries:
            entry_id = entry_info['entry_id']
            should_credit_account_name = entry_info['should_credit']
            
            # Get the correct account
            correct_account = db.get_account_by_name(should_credit_account_name, self.conn)
            if not correct_account:
                errors.append({
                    "entry_id": entry_id,
                    "error": f"Account '{should_credit_account_name}' not found"
                })
                continue
            
            # Get all lines for this entry
            cur = self.conn.execute("""
                SELECT account_id, debit, credit 
                FROM journal_lines 
                WHERE entry_id = ?
                ORDER BY id
            """, (entry_id,))
            
            lines = cur.fetchall()
            
            if not lines:
                errors.append({
                    "entry_id": entry_id,
                    "error": "No journal lines found for entry"
                })
                continue
            
            # Get entry metadata
            cur = self.conn.execute("""
                SELECT date, description, is_adjusting, is_closing, is_reversing,
                       document_ref, external_ref, memo, source_type, status
                FROM journal_entries
                WHERE id = ?
            """, (entry_id,))
            
            entry_meta = cur.fetchone()
            if not entry_meta:
                errors.append({
                    "entry_id": entry_id,
                    "error": "Entry not found"
                })
                continue
            
            # Rebuild journal lines, replacing Supplies credit with correct account
            new_lines = []
            supplies_credit_found = False
            
            for line in lines:
                account_id = line['account_id']
                debit = float(line['debit'] or 0)
                credit = float(line['credit'] or 0)
                
                if account_id == supplies_id and credit > 0:
                    # Replace Supplies credit with correct account
                    new_lines.append(JournalLine(
                        account_id=correct_account['id'],
                        debit=0.0,
                        credit=credit
                    ))
                    supplies_credit_found = True
                else:
                    # Keep other lines as-is
                    new_lines.append(JournalLine(
                        account_id=account_id,
                        debit=debit,
                        credit=credit
                    ))
            
            if not supplies_credit_found:
                errors.append({
                    "entry_id": entry_id,
                    "error": "Supplies credit line not found in entry"
                })
                continue
            
            if dry_run:
                # In dry run, just track that we would fix it
                fixed_entries[entry_id] = None
            else:
                # Delete old entry (this will cascade delete journal_lines due to foreign key)
                try:
                    self.conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
                    
                    # Recreate entry with corrected lines
                    new_entry_id = self.record_entry(
                        date=entry_meta['date'],
                        description=entry_meta['description'],
                        lines=new_lines,
                        is_adjusting=bool(entry_meta['is_adjusting']),
                        is_closing=bool(entry_meta['is_closing']),
                        is_reversing=bool(entry_meta['is_reversing']),
                        document_ref=entry_meta['document_ref'],
                        external_ref=entry_meta['external_ref'],
                        memo=entry_meta['memo'],
                        source_type=entry_meta['source_type'],
                        status=entry_meta['status'] or 'posted',
                    )
                    
                    self.conn.commit()
                    fixed_entries[entry_id] = new_entry_id
                    fixed_count += 1
                except Exception as e:
                    errors.append({
                        "entry_id": entry_id,
                        "error": str(e)
                    })
                    self.conn.rollback()
        
        return {
            "fixed_count": fixed_count,
            "total_entries": len(problematic_entries),
            "errors": errors,
            "fixed_entries": fixed_entries,
            "dry_run": dry_run,
            "message": (
                f"Would fix {len(problematic_entries)} entries" if dry_run
                else f"Fixed {fixed_count} out of {len(problematic_entries)} entries"
            )
        }

    def check_account_name_issues(self) -> Dict[str, object]:
        """
        Check for account name mismatches in journal entries.
        Returns a dictionary with issues found and recommendations.
        
        Common issues:
        - Entries using "Service Income" instead of "Service Revenue"
        - Other account name variations that don't match chart of accounts
        """
        if not self.current_period_id:
            return {"error": "No active accounting period selected"}
        
        issues_found = []
        
        # Account name mappings (wrong name -> correct name)
        account_name_mappings = {
            "Service Income": "Service Revenue",
            "Owners Capital": "Owner's Capital",
            "Owner Capital": "Owner's Capital",
            "Owners Drawings": "Owner's Drawings",
            "Owner Drawings": "Owner's Drawings",
            "Salaries and Wages": "Salaries & Wages",
        }
        
        # Find all journal lines in current period
        cur = self.conn.execute("""
            SELECT jl.id, jl.entry_id, jl.account_id, a.name as account_name,
                   je.document_ref, je.description, je.date, jl.debit, jl.credit
            FROM journal_lines jl
            JOIN accounts a ON a.id = jl.account_id
            JOIN journal_entries je ON je.id = jl.entry_id
            WHERE je.period_id = ?
            ORDER BY je.date, je.id, jl.id
        """, (self.current_period_id,))
        
        lines = cur.fetchall()
        
        # Check for mismatched account names
        for line in lines:
            account_name = line['account_name']
            if account_name in account_name_mappings:
                correct_name = account_name_mappings[account_name]
                # Check if correct account exists
                correct_account = db.get_account_by_name(correct_name, self.conn)
                if correct_account:
                    issues_found.append({
                        "line_id": line['id'],
                        "entry_id": line['entry_id'],
                        "document_ref": line['document_ref'],
                        "date": line['date'],
                        "description": line['description'],
                        "wrong_account": account_name,
                        "wrong_account_id": line['account_id'],
                        "correct_account": correct_name,
                        "correct_account_id": correct_account['id'],
                        "debit": float(line['debit'] or 0),
                        "credit": float(line['credit'] or 0),
                    })
        
        return {
            "period_id": self.current_period_id,
            "total_lines_checked": len(lines),
            "issues_found": len(issues_found),
            "issues": issues_found,
            "recommendation": "Delete and re-enter affected transactions, or manually update account assignments" if issues_found else "No issues found"
        }

    def _initialize_cycle_status(self) -> None:
        if not self.current_period_id:
            return
        statuses = db.get_cycle_status(self.current_period_id, conn=self.conn)
        if not statuses:
            return
        # Mark the first step as in-progress by default
        first_step = min((row["step"] for row in statuses), default=1)
        db.set_cycle_step_status(
            self.current_period_id,
            first_step,
            "in_progress",
            note="Collecting and analyzing source documents",
            conn=self.conn,
        )

    def _update_cycle_status_after_entry(
        self,
        *,
        is_adjusting: bool,
        is_closing: bool,
        status: str,
    ) -> None:
        if not self.current_period_id or status != "posted":
            return
        db.set_cycle_step_status(
            self.current_period_id,
            1,
            "completed",
            note="Source documents analyzed",
            conn=self.conn,
        )
        db.set_cycle_step_status(
            self.current_period_id,
            2,
            "completed",
            note="Transactions journalized",
            conn=self.conn,
        )
        if is_adjusting:
            db.set_cycle_step_status(
                self.current_period_id,
                5,
                "completed",
                note="Adjusting entries posted",
                conn=self.conn,
            )
            db.set_cycle_step_status(
                self.current_period_id,
                6,
                "in_progress",
                note="Generate adjusted trial balance",
                conn=self.conn,
            )
        if is_closing:
            db.set_cycle_step_status(
                self.current_period_id,
                8,
                "completed",
                note="Closing entries recorded",
                conn=self.conn,
            )
            db.set_cycle_step_status(
                self.current_period_id,
                9,
                "in_progress",
                note="Post-closing trial balance pending",
                conn=self.conn,
            )


