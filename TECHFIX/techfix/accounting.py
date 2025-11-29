from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
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
    def __init__(self, conn: Optional[sqlite3.Connection] = None) -> None:
        self._owned = conn is not None
        self.conn = conn or db.get_connection()
        self.current_period = db.get_current_period(conn=self.conn)
        if not self.current_period:
            self.current_period = db.ensure_default_period(conn=self.conn)
        self._initialize_cycle_status()

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
        line_tuples = [ln.as_tuple() for ln in lines]
        period = period_id or self.current_period_id
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
            created_by=created_by,
            posted_by=posted_by,
            period_id=period,
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

    # Adjusting Entries helpers
    def adjust_supplies_used(self, date: str, remaining_supplies_amount: float) -> Optional[int]:
        acc_supplies = db.get_account_by_name("Supplies", self.conn)
        acc_supplies_exp = db.get_account_by_name("Supplies Expense", self.conn)
        if not acc_supplies or not acc_supplies_exp:
            return None
        # Compute current balance in Supplies (debit minus credit)
        cur = self.conn.execute(
            """
            SELECT COALESCE(SUM(debit) - SUM(credit), 0) AS balance
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            WHERE jl.account_id = ?
            """,
            (acc_supplies["id"],),
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
        cur = self.conn.execute(
            """
            SELECT a.id, a.name, ROUND(COALESCE(SUM(jl.credit) - SUM(jl.debit),0),2) AS balance
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jl.entry_id
            WHERE a.type = 'Revenue' AND a.is_active=1 AND je.period_id = ?
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
        cur = self.conn.execute(
            """
            SELECT a.id, a.name, ROUND(COALESCE(SUM(jl.debit) - SUM(jl.credit),0),2) AS balance
            FROM accounts a
            LEFT JOIN journal_lines jl ON jl.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jl.entry_id
            WHERE a.type = 'Expense' AND a.is_active=1 AND je.period_id = ?
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
        drawings = db.get_account_by_name("Owner's Drawings", self.conn)
        if drawings:
            cur = self.conn.execute(
                """
                SELECT ROUND(COALESCE(SUM(debit) - SUM(credit),0),2) AS balance
                FROM journal_lines jl
                JOIN journal_entries je ON je.id = jl.entry_id
                WHERE jl.account_id = ? AND je.period_id = ?
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
                    if status != 'pending' or not when:
                        continue
                    if str(when) > str(cutoff):
                        continue
                    eid = int(r['original_entry_id'])
                    rid = self.reverse_entry(eid, when)
                    if rid:
                        created.append(int(rid))
                        db.update_reversing_status(int(r['id']), 'completed', reversed_entry_id=int(rid), conn=self.conn)
                except Exception:
                    pass
            if created:
                db.set_cycle_step_status(self.current_period_id, 10, 'completed', note='Reversing entries posted', conn=self.conn)
            return created
        except Exception:
            return created

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
                klass = "Operating"
                if non_cash_lines:
                    other_id = int(non_cash_lines[0]["account_id"])
                    acct = self.conn.execute("SELECT type FROM accounts WHERE id=?", (other_id,)).fetchone()
                    acct_type = acct["type"] if acct else None
                    if acct_type in ("Asset", "Contra Asset"):
                        klass = "Investing"
                    elif acct_type in ("Liability", "Equity"):
                        klass = "Financing"
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


