# Reversing Entry Schedule

## Timeline and Deadlines
1. Identify accruals, prepayments, estimates at period close.
2. Set `reverse_on` for first business day of next period.
3. Set `deadline_on` equal to `reverse_on` for strict compliance.
4. Configure `reminder_on` one day before `reverse_on`.

## Categorization
- Accruals
- Prepayments
- Estimates
- Other

## Templates
- Define in `reversing_entry_templates` with `entry_type`, `required_fields`, `default_memo`, `authorization_level`, `approval_required`.
- Apply via `AccountingEngine.apply_reversing_template`.

## Approvals
- Workflow stored in `reversing_entry_approvals` with `reviewer`, `role`, `level`, `status`.
- `authorization_level` indicates minimum approval tier required.

## Reminders
- Automatic audit log entries on/after `reminder_on`.

## Audit Trail and Versioning
- All status and deadline changes recorded in `reversing_entry_history`.
- System actions recorded in `audit_log`.

## Integration
- Reversals posted as journal entries via `AccountingEngine.reverse_entry`.

## Reporting
- Use `AccountingEngine.generate_reversing_report(as_of)` for compliance metrics and exceptions.
- Export rows using `export_rows_to_csv` or `export_rows_to_excel`.

## Training Notes
- Use specific payable/receivable accounts for accrual reversals.
- Ensure approvals for entries flagged `approval_required` before processing.
- Schedule monthly and quarterly entries with templates to standardize.
