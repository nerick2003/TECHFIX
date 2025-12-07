"""
Undo/Redo Module
Provides undo and redo functionality for transactions.
"""
from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging

from . import db

logger = logging.getLogger(__name__)

# In-memory undo/redo stack (could be persisted for crash recovery)
_undo_stack: List[Dict[str, Any]] = []
_redo_stack: List[Dict[str, Any]] = []
_max_stack_size = 50


def record_action(
    action_type: str,
    entity_type: str,
    entity_id: int,
    old_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    *,
    conn: Optional[sqlite3.Connection] = None
) -> None:
    """Record an action for undo/redo."""
    try:
        action = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action_type': action_type,  # 'create', 'update', 'delete'
            'entity_type': entity_type,  # 'journal_entry', 'account', etc.
            'entity_id': entity_id,
            'old_state': old_state,
            'new_state': new_state,
        }
        
        _undo_stack.append(action)
        
        # Limit stack size
        if len(_undo_stack) > _max_stack_size:
            _undo_stack.pop(0)
        
        # Clear redo stack when new action is recorded
        _redo_stack.clear()
        
        logger.debug(f"Action recorded: {action_type} {entity_type} {entity_id}")
    except Exception as e:
        logger.error(f"Error recording action: {e}", exc_info=True)


def undo(*, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Undo the last action."""
    if not _undo_stack:
        return None
    
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        action = _undo_stack.pop()
        
        # Move to redo stack
        _redo_stack.append(action)
        
        # Perform undo based on action type
        result = _perform_undo(action, conn)
        
        if result:
            logger.info(f"Undone: {action['action_type']} {action['entity_type']} {action['entity_id']}")
        
        return result
    except Exception as e:
        logger.error(f"Undo error: {e}", exc_info=True)
        return None
    finally:
        if not owned:
            conn.close()


def redo(*, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Redo the last undone action."""
    if not _redo_stack:
        return None
    
    owned = conn is not None
    if not conn:
        conn = db.get_connection()
    
    try:
        action = _redo_stack.pop()
        
        # Move back to undo stack
        _undo_stack.append(action)
        
        # Perform redo
        result = _perform_redo(action, conn)
        
        if result:
            logger.info(f"Redone: {action['action_type']} {action['entity_type']} {action['entity_id']}")
        
        return result
    except Exception as e:
        logger.error(f"Redo error: {e}", exc_info=True)
        return None
    finally:
        if not owned:
            conn.close()


def _perform_undo(action: Dict[str, Any], conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """Perform the actual undo operation."""
    try:
        action_type = action['action_type']
        entity_type = action['entity_type']
        entity_id = action['entity_id']
        old_state = action.get('old_state')
        new_state = action.get('new_state')
        
        if action_type == 'create':
            # Delete the created entity
            if entity_type == 'journal_entry':
                conn.execute("DELETE FROM journal_entries WHERE id = ?", (entity_id,))
                conn.commit()
                return {'success': True, 'message': 'Journal entry deleted'}
        
        elif action_type == 'update':
            # Restore old state
            if entity_type == 'journal_entry' and old_state:
                # Restore journal entry
                conn.execute(
                    """
                    UPDATE journal_entries
                    SET description = ?, date = ?, status = ?, memo = ?
                    WHERE id = ?
                    """,
                    (
                        old_state.get('description'),
                        old_state.get('date'),
                        old_state.get('status'),
                        old_state.get('memo'),
                        entity_id
                    )
                )
                conn.commit()
                return {'success': True, 'message': 'Journal entry restored'}
        
        elif action_type == 'delete':
            # Recreate the deleted entity
            if entity_type == 'journal_entry' and old_state:
                # Recreate journal entry (simplified - would need to restore lines too)
                conn.execute(
                    """
                    INSERT INTO journal_entries (id, date, description, status, memo, period_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_id,
                        old_state.get('date'),
                        old_state.get('description'),
                        old_state.get('status'),
                        old_state.get('memo'),
                        old_state.get('period_id')
                    )
                )
                conn.commit()
                return {'success': True, 'message': 'Journal entry restored'}
        
        return None
    except Exception as e:
        logger.error(f"Undo operation error: {e}", exc_info=True)
        conn.rollback()
        return None


def _perform_redo(action: Dict[str, Any], conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """Perform the actual redo operation."""
    try:
        action_type = action['action_type']
        entity_type = action['entity_type']
        entity_id = action['entity_id']
        new_state = action.get('new_state')
        
        if action_type == 'create':
            # Recreate the entity
            if entity_type == 'journal_entry' and new_state:
                conn.execute(
                    """
                    INSERT INTO journal_entries (id, date, description, status, memo, period_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity_id,
                        new_state.get('date'),
                        new_state.get('description'),
                        new_state.get('status'),
                        new_state.get('memo'),
                        new_state.get('period_id')
                    )
                )
                conn.commit()
                return {'success': True, 'message': 'Journal entry recreated'}
        
        elif action_type == 'update':
            # Apply new state
            if entity_type == 'journal_entry' and new_state:
                conn.execute(
                    """
                    UPDATE journal_entries
                    SET description = ?, date = ?, status = ?, memo = ?
                    WHERE id = ?
                    """,
                    (
                        new_state.get('description'),
                        new_state.get('date'),
                        new_state.get('status'),
                        new_state.get('memo'),
                        entity_id
                    )
                )
                conn.commit()
                return {'success': True, 'message': 'Journal entry updated'}
        
        elif action_type == 'delete':
            # Delete again
            if entity_type == 'journal_entry':
                conn.execute("DELETE FROM journal_entries WHERE id = ?", (entity_id,))
                conn.commit()
                return {'success': True, 'message': 'Journal entry deleted'}
        
        return None
    except Exception as e:
        logger.error(f"Redo operation error: {e}", exc_info=True)
        conn.rollback()
        return None


def can_undo() -> bool:
    """Check if undo is available."""
    return len(_undo_stack) > 0


def can_redo() -> bool:
    """Check if redo is available."""
    return len(_redo_stack) > 0


def clear_history() -> None:
    """Clear undo/redo history."""
    _undo_stack.clear()
    _redo_stack.clear()

