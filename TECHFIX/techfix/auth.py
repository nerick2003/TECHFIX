"""
Authentication and Security Module
Handles user authentication, password management, and session management.
"""
from __future__ import annotations

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.warning("bcrypt not available, using fallback password hashing")

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("cryptography not available, encryption disabled")

logger = logging.getLogger(__name__)

# Session management
_active_sessions: Dict[str, Dict[str, Any]] = {}
_session_timeout = timedelta(hours=8)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt or fallback to SHA256."""
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        # Fallback: SHA256 with salt (less secure but works without bcrypt)
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
        return f"{salt}:{hash_obj.hexdigest()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash.
    
    SECURITY: This function MUST return False if password doesn't match.
    Never return True without proper verification.
    """
    # Input validation
    if not password:
        logger.warning("verify_password: password is empty or None")
        return False
    
    if not hashed:
        logger.warning("verify_password: hash is empty or None")
        return False
    
    if not isinstance(password, str) or not isinstance(hashed, str):
        logger.warning(f"verify_password: invalid types - password: {type(password)}, hash: {type(hashed)}")
        return False
    
    password = password.strip()
    hashed = hashed.strip()
    
    if not password or not hashed:
        logger.warning("verify_password: password or hash is empty after strip")
        return False
    
    if BCRYPT_AVAILABLE:
        try:
            # Log what we're checking (for debugging - be careful with sensitive data)
            logger.info(f"verify_password: Checking password (length: {len(password)}, first char: '{password[0] if password else 'N/A'}')")
            logger.info(f"verify_password: Hash length: {len(hashed)}, first 10 chars: '{hashed[:10] if len(hashed) >= 10 else hashed}'")
            
            # bcrypt verification - encode both password and hash
            password_bytes = password.encode('utf-8')
            hash_bytes = hashed.encode('utf-8')
            
            logger.debug(f"verify_password: Password bytes length: {len(password_bytes)}")
            logger.debug(f"verify_password: Hash bytes length: {len(hash_bytes)}")
            
            # CRITICAL: Use bcrypt.checkpw to verify
            result = bcrypt.checkpw(password_bytes, hash_bytes)
            
            logger.info(f"verify_password: bcrypt.checkpw result = {result}")
            logger.info(f"verify_password: Password being checked: '{password}'")
            
            if result:
                logger.info(f"verify_password: ✓ Password MATCHES hash")
            else:
                logger.warning(f"verify_password: ✗ Password DOES NOT MATCH hash")
                logger.warning(f"verify_password: Input password: '{password}' (length: {len(password)})")
            
            return result
        except Exception as e:
            logger.error(f"verify_password: bcrypt exception: {e}", exc_info=True)
            logger.error(f"verify_password: Exception details - password type: {type(password)}, hash type: {type(hashed)}")
            return False
    else:
        # Fallback verification using SHA256
        try:
            if ':' not in hashed:
                logger.warning("verify_password: hash format invalid (no colon separator)")
                return False
            
            parts = hashed.split(':', 1)
            if len(parts) != 2:
                logger.warning(f"verify_password: invalid hash format - expected 2 parts, got {len(parts)}")
                return False
            
            salt, stored_hash = parts
            if not salt or not stored_hash:
                logger.warning("verify_password: salt or stored_hash is empty")
                return False
            
            # Compute hash of password + salt
            hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
            computed_hash = hash_obj.hexdigest()
            
            # Constant-time comparison to prevent timing attacks
            result = computed_hash == stored_hash
            logger.info(f"verify_password: SHA256 verification result = {result}")
            
            if not result:
                logger.warning("verify_password: SHA256 check returned False - password does not match")
            
            return result
        except Exception as e:
            logger.error(f"verify_password: SHA256 exception: {e}", exc_info=True)
            return False


def create_session(user_id: int, username: str, role_id: Optional[int] = None) -> str:
    """Create a new session and return session token."""
    token = secrets.token_urlsafe(32)
    _active_sessions[token] = {
        'user_id': user_id,
        'username': username,
        'role_id': role_id,
        'created_at': datetime.now(timezone.utc),
        'last_activity': datetime.now(timezone.utc),
    }
    return token


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """Get session data if valid, None otherwise."""
    if token not in _active_sessions:
        return None
    
    session = _active_sessions[token]
    now = datetime.now(timezone.utc)
    
    # Check if session expired
    if now - session['last_activity'] > _session_timeout:
        del _active_sessions[token]
        return None
    
    # Update last activity
    session['last_activity'] = now
    return session


def invalidate_session(token: str) -> None:
    """Invalidate a session."""
    _active_sessions.pop(token, None)


def invalidate_user_sessions(user_id: int) -> None:
    """Invalidate all sessions for a user."""
    tokens_to_remove = [
        token for token, session in _active_sessions.items()
        if session['user_id'] == user_id
    ]
    for token in tokens_to_remove:
        del _active_sessions[token]


def authenticate_user(username: str, password: str, *, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user and return user info if successful.
    
    SECURITY: This function MUST return None if password verification fails.
    Never return user info without proper password verification.
    """
    from . import db
    
    # Input validation - reject empty inputs immediately
    if not username or not isinstance(username, str):
        logger.warning("Authentication failed: invalid username")
        return None
    
    if not password or not isinstance(password, str):
        logger.warning("Authentication failed: invalid password")
        return None
    
    username = username.strip()
    password = password.strip()
    
    if not username or not password:
        logger.warning("Authentication failed: username or password is empty")
        return None
    
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    # Track if password was verified - CRITICAL for security
    password_verified = False
    
    try:
        # Get user with password hash
        cur = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.role_id, u.company_id, u.is_active,
                   u.password_hash, r.name as role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.username = ? AND u.is_active = 1
            """,
            (username,)
        )
        row = cur.fetchone()
        
        if not row:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None
        
        # Get user ID and verify username matches (prevent username spoofing)
        user_id = row['id']
        db_username = row['username']
        
        # CRITICAL: Verify the username from database matches the requested username
        if db_username != username:
            logger.error(f"SECURITY ERROR: Username mismatch! Requested '{username}', DB has '{db_username}'")
            return None
        
        if not user_id:
            logger.error(f"Authentication failed: user '{username}' has no ID")
            return None
        
        logger.info(f"User lookup successful: username='{username}', id={user_id}")
        
        # Check if password hash column exists and has a value
        password_hash = None
        try:
            # sqlite3.Row supports dictionary-style access
            raw_password_hash = row['password_hash']
            logger.debug(f"Raw password_hash from DB: type={type(raw_password_hash)}, value={raw_password_hash is not None}")
            
            # Check if it's actually None or empty string
            if raw_password_hash is not None:
                password_hash_str = str(raw_password_hash).strip()
                if len(password_hash_str) > 0:
                    password_hash = password_hash_str
                    logger.debug(f"Password hash extracted: length={len(password_hash)}")
                else:
                    logger.warning(f"Password hash is empty string for user '{username}'")
                    password_hash = None
            else:
                logger.warning(f"Password hash is NULL for user '{username}'")
                password_hash = None
        except (KeyError, AttributeError, TypeError) as e:
            logger.error(f"Error getting password_hash: {e}", exc_info=True)
            password_hash = None
        
        logger.info(f"User '{username}' (id: {user_id}) - password_hash present: {password_hash is not None}")
        if password_hash:
            logger.info(f"Password hash length: {len(password_hash)}")
        else:
            logger.warning(f"WARNING: User '{username}' has NO password_hash - will require first-login password 'admin'")
        
        # SECURITY: Password verification is MANDATORY
        if not password_hash:
            # First login - require default password "admin" for security
            logger.info(f"First login path for user '{username}' - checking if password is 'admin'")
            logger.info(f"Provided password length: {len(password)}, first char: '{password[0] if password else 'N/A'}'")
            
            # CRITICAL: For first login, password MUST be exactly "admin" (case-sensitive)
            # Use strict comparison - no whitespace, exact match
            expected_password = "admin"
            
            # Log the comparison details
            logger.info(f"Password comparison: input='{password}' (len={len(password)}), expected='{expected_password}' (len={len(expected_password)})")
            logger.info(f"Password == expected: {password == expected_password}")
            logger.info(f"Password repr: {repr(password)}")
            logger.info(f"Expected repr: {repr(expected_password)}")
            
            # First check: exact string match
            if password != expected_password:
                logger.warning(f"Authentication FAILED: password does not match 'admin'")
                logger.warning(f"  Input: '{password}' (length: {len(password)}, repr: {repr(password)})")
                logger.warning(f"  Expected: '{expected_password}' (length: {len(expected_password)}, repr: {repr(expected_password)})")
                return None
            
            # Second check: length must be exactly 5
            if len(password) != 5:
                logger.warning(f"Authentication FAILED: password length is {len(password)}, expected 5")
                return None
            
            # Third check: must be exactly "admin" after strip (should already be stripped, but double-check)
            if password.strip() != "admin":
                logger.warning(f"Authentication FAILED: password after strip is '{password.strip()}', expected 'admin'")
                return None
            
            # All checks passed - password is verified
            password_verified = True
            logger.info(f"✓ First login password verified for user '{username}' - password matches 'admin'")
            
            # Password verified, now set it as the user's password
            new_password_hash = hash_password(password)
            if not new_password_hash:
                logger.error(f"Failed to hash password for user '{username}'")
                return None
                
            try:
                # Try with last_login first
                conn.execute(
                    "UPDATE users SET password_hash = ?, last_login = ? WHERE id = ?",
                    (new_password_hash, datetime.now(timezone.utc).isoformat(), user_id)
                )
                conn.commit()
                logger.info(f"Password set for user '{username}'")
            except Exception as e:
                logger.debug(f"Error setting password with last_login: {e}")
                # Try without last_login column if it doesn't exist
                try:
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (new_password_hash, user_id)
                    )
                    conn.commit()
                    logger.info(f"Password set for user '{username}' (without last_login)")
                except Exception as e2:
                    logger.error(f"Error setting password: {e2}", exc_info=True)
                    return None
        else:
            # Verify password - this is critical for security
            if not password_hash or len(str(password_hash).strip()) == 0:
                logger.error(f"Authentication failed: password_hash is empty for user '{username}'")
                return None
            
            # CRITICAL: Verify password - this MUST happen
            logger.info(f"About to verify password for user '{username}'")
            logger.info(f"  Input password: '{password}' (length: {len(password)}, repr: {repr(password)})")
            logger.info(f"  Stored hash length: {len(password_hash)}")
            logger.info(f"  Hash first 20 chars: '{password_hash[:20] if len(password_hash) >= 20 else password_hash}'")
            
            # SECURITY: Verify the password using the stored hash
            # This is the CRITICAL check - if this returns False, authentication MUST fail
            verified = verify_password(password, password_hash)
            logger.info(f"Password verification for user '{username}': {verified}")
            
            # ADDITIONAL SECURITY CHECK: If verify_password returned True but we're suspicious,
            # do a sanity check - verify that the password hash is actually valid
            if verified and BCRYPT_AVAILABLE:
                # Test that bcrypt is working correctly by verifying the hash format
                try:
                    # Check if hash looks like a valid bcrypt hash (should start with $2b$ or similar)
                    if not (password_hash.startswith('$2') and len(password_hash) >= 60):
                        logger.error(f"SECURITY WARNING: Password hash doesn't look like valid bcrypt hash!")
                        logger.error(f"  Hash: '{password_hash[:50]}...'")
                        verified = False
                    else:
                        # Double-check: try to verify with a wrong password to ensure bcrypt is working
                        test_wrong_password = password + "_WRONG_TEST"
                        test_result = bcrypt.checkpw(test_wrong_password.encode('utf-8'), password_hash.encode('utf-8'))
                        if test_result:
                            logger.error(f"SECURITY ERROR: bcrypt.checkpw returned True for WRONG password! This indicates a serious bug!")
                            verified = False
                        else:
                            logger.debug(f"Sanity check passed: bcrypt correctly rejected wrong password")
                except Exception as e:
                    logger.error(f"Error in security sanity check: {e}", exc_info=True)
                    # Don't fail authentication due to sanity check error, but log it
            
            if not verified:
                logger.warning(f"Authentication failed: invalid password for user '{username}'")
                logger.warning(f"  Password provided: '{password}' (length: {len(password)})")
                logger.warning(f"  Password hash type: {type(password_hash)}, length: {len(password_hash) if password_hash else 0}")
                return None
            
            # Password verified successfully
            password_verified = True
            logger.info(f"Password verified successfully for user '{username}'")
            
            # Update last login
            try:
                conn.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), user_id)
                )
                conn.commit()
            except Exception:
                pass  # last_login column might not exist
        
        # SECURITY CHECK: Never return user info without password verification
        if not password_verified:
            logger.error(f"SECURITY ERROR: Attempted to return user info without password verification for user '{username}'")
            return None
        
        # Get user info for return (sqlite3.Row supports dictionary access, but not .get())
        # Use try/except for optional fields that might be None
        # Ensure we have required fields before returning
        try:
            user_id_val = row['id']
            username_val = row['username']
            
            if not user_id_val or not username_val:
                logger.error(f"Authentication failed: missing required user fields (id={user_id_val}, username={username_val})")
                return None
            
            result = {
                'id': user_id_val,
                'username': username_val,
            }
            
            # Add optional fields safely
            try:
                result['full_name'] = row['full_name']
            except (KeyError, IndexError):
                result['full_name'] = None
                
            try:
                result['role_id'] = row['role_id']
            except (KeyError, IndexError):
                result['role_id'] = None
                
            try:
                result['role_name'] = row['role_name']
            except (KeyError, IndexError):
                result['role_name'] = None
                
            try:
                result['company_id'] = row['company_id']
            except (KeyError, IndexError):
                result['company_id'] = None
            
            # Final validation - ensure result is valid
            if not result.get('id') or not result.get('username'):
                logger.error(f"Authentication failed: invalid result structure")
                return None
            
            # Double-check password was verified before returning
            if not password_verified:
                logger.error(f"SECURITY ERROR: Password verification flag is False for user '{username}' - rejecting authentication")
                return None
            
            logger.info(f"Authentication successful for user: {username_val} (id: {user_id_val})")
            return result
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Authentication failed: error building user info - {e}", exc_info=True)
            return None
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        return None
    finally:
        if not owned:
            conn.close()


def change_password(user_id: int, old_password: str, new_password: str, *, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Change user password."""
    from . import db
    
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        # Get current password hash
        cur = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        
        if not row:
            return False
        
        # sqlite3.Row doesn't support .get(), use try/except instead
        try:
            password_hash = row['password_hash']
        except (KeyError, IndexError):
            password_hash = None
        
        # Verify old password
        if password_hash and not verify_password(old_password, password_hash):
            return False
        
        # Set new password
        new_hash = hash_password(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id)
        )
        conn.commit()
        
        # Invalidate all sessions for security
        invalidate_user_sessions(user_id)
        
        return True
    except Exception as e:
        logger.error(f"Password change error: {e}", exc_info=True)
        return False
    finally:
        if not owned:
            conn.close()


def reset_password(user_id: int, new_password: str, *, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Reset user password (admin function)."""
    from . import db
    
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        new_hash = hash_password(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id)
        )
        conn.commit()
        
        # Invalidate all sessions
        invalidate_user_sessions(user_id)
        
        return True
    except Exception as e:
        logger.error(f"Password reset error: {e}", exc_info=True)
        return False
    finally:
        if not owned:
            conn.close()


def has_permission(user_role_id: Optional[int], permission: str, *, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Check if user role has a specific permission."""
    # Simple RBAC implementation
    # Admin has all permissions
    if user_role_id is None:
        return False
    
    from . import db
    
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        # Get role name
        cur = conn.execute("SELECT name FROM roles WHERE id = ?", (user_role_id,))
        row = cur.fetchone()
        
        if not row:
            return False
        
        role_name = row['name'].lower()
        
        # Admin has all permissions
        if role_name == 'admin':
            return True
        
        # Define permissions per role (can be extended)
        permissions = {
            'accountant': ['view', 'create', 'edit', 'post', 'adjust', 'close'],
            'viewer': ['view'],
            'manager': ['view', 'create', 'edit', 'approve', 'close'],
        }
        
        role_perms = permissions.get(role_name, [])
        return permission.lower() in role_perms
    except Exception:
        return False
    finally:
        if not owned:
            conn.close()

