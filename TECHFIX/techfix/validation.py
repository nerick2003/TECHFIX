"""
Input Validation and Sanitization Module
Handles validation and sanitization of user inputs.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Tuple, List, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Allowed file extensions for uploads
ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.pdf'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """Sanitize a string input."""
    if not isinstance(value, str):
        value = str(value)
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Trim whitespace
    value = value.strip()
    
    # Limit length
    if max_length and len(value) > max_length:
        value = value[:max_length]
        logger.warning(f"String truncated to {max_length} characters")
    
    return value


def validate_date(date_str: str) -> Tuple[bool, Optional[datetime]]:
    """Validate date string in YYYY-MM-DD format."""
    try:
        date_obj = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        return True, datetime.combine(date_obj, datetime.min.time())
    except (ValueError, AttributeError):
        return False, None


def validate_amount(amount_str: str) -> Tuple[bool, Optional[float]]:
    """Validate and parse amount string."""
    try:
        # Remove commas and currency symbols
        cleaned = re.sub(r'[,\s₱$€£¥]', '', str(amount_str).strip())
        
        # Parse as float
        amount = float(cleaned)
        
        # Check for reasonable range
        if amount < 0:
            return False, None
        if amount > 1e15:  # Very large number
            logger.warning(f"Amount seems unusually large: {amount}")
        
        # Round to 2 decimal places
        amount = round(amount, 2)
        
        return True, amount
    except (ValueError, TypeError, AttributeError):
        return False, None


def validate_account_code(code: str) -> bool:
    """Validate account code format."""
    if not code or not isinstance(code, str):
        return False
    
    # Account codes should be alphanumeric with optional dashes/underscores
    # Length between 2 and 20 characters
    pattern = r'^[A-Za-z0-9_-]{2,20}$'
    return bool(re.match(pattern, code.strip()))


def validate_account_name(name: str) -> bool:
    """Validate account name."""
    if not name or not isinstance(name, str):
        return False
    
    name = name.strip()
    
    # Length check
    if len(name) < 2 or len(name) > 100:
        return False
    
    # Should not contain only special characters
    if not re.search(r'[A-Za-z0-9]', name):
        return False
    
    return True


def validate_email(email: str) -> bool:
    """Validate email address format."""
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone.strip())
    
    # Should be digits, length 7-15
    return bool(re.match(r'^\d{7,15}$', cleaned))


def validate_file_upload(file_path: Path, allowed_extensions: Optional[set] = None) -> Tuple[bool, Optional[str]]:
    """Validate file upload."""
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS
    
    try:
        if not file_path.exists():
            return False, "File does not exist"
        
        # Check extension
        ext = file_path.suffix.lower()
        if ext not in allowed_extensions:
            return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        
        # Check file size
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        
        if size == 0:
            return False, "File is empty"
        
        return True, None
    except Exception as e:
        logger.error(f"File validation error: {e}", exc_info=True)
        return False, f"Validation error: {str(e)}"


def sanitize_sql_input(value: Any) -> str:
    """Sanitize input for SQL (though parameterized queries should be used)."""
    if value is None:
        return 'NULL'
    
    if isinstance(value, (int, float)):
        return str(value)
    
    # Escape single quotes
    value_str = str(value).replace("'", "''")
    return f"'{value_str}'"


def validate_period_dates(start_date: str, end_date: str) -> Tuple[bool, Optional[str]]:
    """Validate accounting period dates."""
    valid_start, start_dt = validate_date(start_date)
    if not valid_start:
        return False, "Invalid start date format (use YYYY-MM-DD)"
    
    valid_end, end_dt = validate_date(end_date)
    if not valid_end:
        return False, "Invalid end date format (use YYYY-MM-DD)"
    
    if start_dt and end_dt and start_dt > end_dt:
        return False, "Start date must be before end date"
    
    return True, None


def validate_journal_entry_lines(lines: List[Any]) -> Tuple[bool, Optional[str]]:
    """Validate journal entry lines."""
    if not lines or len(lines) < 2:
        return False, "Journal entry must have at least 2 lines (debit and credit)"
    
    total_debit = 0.0
    total_credit = 0.0
    
    for line in lines:
        if not hasattr(line, 'debit') or not hasattr(line, 'credit'):
            return False, "Invalid journal line format"
        
        debit = float(line.debit) if line.debit else 0.0
        credit = float(line.credit) if line.credit else 0.0
        
        if debit < 0 or credit < 0:
            return False, "Debit and credit amounts cannot be negative"
        
        if debit > 0 and credit > 0:
            return False, "A line cannot have both debit and credit"
        
        if debit == 0 and credit == 0:
            return False, "A line must have either debit or credit"
        
        total_debit += debit
        total_credit += credit
    
    # Check balance
    if abs(total_debit - total_credit) > 0.01:  # Allow small rounding differences
        return False, f"Debits ({total_debit:.2f}) must equal credits ({total_credit:.2f})"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove path components
    filename = Path(filename).name
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]
    
    return filename

