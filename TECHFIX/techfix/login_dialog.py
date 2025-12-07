"""Login dialog for TechFix Solutions - standalone window."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Default theme colors (can be customized)
DEFAULT_THEME = {
    "app_bg": "#f5f7fb",
    "surface_bg": "#ffffff",
    "accent_color": "#2563eb",
    "accent_hover": "#1d4ed8",
    "text_primary": "#1f2937",
    "text_secondary": "#4b5563",
    "entry_border": "#d8dee9",
}


def show_login_dialog(auth_module: Any, palette: Optional[Dict[str, str]] = None, parent: Optional[tk.Tk] = None) -> Optional[Dict[str, Any]]:
    """
    Show login dialog as a standalone window.
    
    Args:
        auth_module: Authentication module with authenticate_user and create_session methods
        palette: Optional color palette dictionary
        parent: Optional parent window (if None, creates a new root window)
        
    Returns:
        Dictionary with user info and session_token if login successful, None otherwise
    """
    if not auth_module:
        return {"user": None, "session_token": None}  # No auth required
    
    # Create login window - use standalone root if parent is withdrawn/hidden
    # Check if parent exists and is visible
    use_toplevel = parent and parent.winfo_exists() and parent.winfo_viewable()
    
    if use_toplevel:
        login_window = tk.Toplevel(parent)
        login_window.transient(parent)
        login_window.grab_set()
    else:
        # Create standalone root window if no parent or parent is hidden
        login_window = tk.Tk()
    login_window.title("Login - TechFix Solutions")
    login_window.resizable(False, False)
    
    # Get theme colors
    if palette:
        bg_color = palette.get("app_bg", DEFAULT_THEME["app_bg"])
        surface_bg = palette.get("surface_bg", DEFAULT_THEME["surface_bg"])
        accent_color = palette.get("accent_color", DEFAULT_THEME["accent_color"])
        accent_hover = palette.get("accent_hover", DEFAULT_THEME["accent_hover"])
        text_primary = palette.get("text_primary", DEFAULT_THEME["text_primary"])
        text_secondary = palette.get("text_secondary", DEFAULT_THEME["text_secondary"])
        entry_border = palette.get("entry_border", DEFAULT_THEME["entry_border"])
    else:
        bg_color = DEFAULT_THEME["app_bg"]
        surface_bg = DEFAULT_THEME["surface_bg"]
        accent_color = DEFAULT_THEME["accent_color"]
        accent_hover = DEFAULT_THEME["accent_hover"]
        text_primary = DEFAULT_THEME["text_primary"]
        text_secondary = DEFAULT_THEME["text_secondary"]
        entry_border = DEFAULT_THEME["entry_border"]
    
    login_window.configure(bg=bg_color)
    
    # Center dialog with modern size - fixed size to prevent resizing
    login_window.update_idletasks()
    width, height = 480, 750  # Increased height to ensure buttons are visible
    x = (login_window.winfo_screenwidth() // 2) - (width // 2)
    y = (login_window.winfo_screenheight() // 2) - (height // 2)
    login_window.geometry(f"{width}x{height}+{x}+{y}")
    login_window.minsize(width, height)  # Prevent window from shrinking
    login_window.maxsize(width, height)  # Prevent window from growing
    
    # Main container with padding
    container = tk.Frame(login_window, bg=bg_color)
    container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Card-style login panel
    card_frame = tk.Frame(container, bg=surface_bg, relief=tk.FLAT, bd=0)
    card_frame.pack(fill=tk.BOTH, expand=True)
    
    # Inner padding for card content - use pack for simpler layout
    content_frame = tk.Frame(card_frame, bg=surface_bg)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=40)
    
    # Create a scrollable container if needed, but for now use simple pack
    # Header section
    header_frame = tk.Frame(content_frame, bg=surface_bg)
    header_frame.pack(fill=tk.X, pady=(0, 30))
    
    # Icon
    icon_label = tk.Label(
        header_frame,
        text="🔐",
        font=("{Segoe UI} 48"),
        bg=surface_bg,
        fg=accent_color
    )
    icon_label.pack(pady=(0, 15))
    
    # Title
    title_label = tk.Label(
        header_frame,
        text="Welcome Back",
        font=("{Segoe UI Semibold} 24"),
        bg=surface_bg,
        fg=text_primary
    )
    title_label.pack(pady=(0, 8))
    
    subtitle = tk.Label(
        header_frame,
        text="Sign in to your TechFix Solutions account",
        bg=surface_bg,
        fg=text_secondary,
        font=("{Segoe UI} 11")
    )
    subtitle.pack()
    
    # Form section - use pack instead of grid to avoid layout issues
    form_frame = tk.Frame(content_frame, bg=surface_bg)
    form_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
    # Don't let form_frame expand too much - leave room for buttons
    
    # Username field
    username_frame = tk.Frame(form_frame, bg=surface_bg)
    username_frame.pack(fill=tk.X, pady=(0, 20))
    
    username_label = tk.Label(
        username_frame,
        text="Username",
        bg=surface_bg,
        fg=text_primary,
        font=("{Segoe UI Semibold} 11")
    )
    username_label.pack(anchor=tk.W, pady=(0, 10))
    
    username_var = tk.StringVar(value="admin")
    username_entry_frame = tk.Frame(username_frame, bg=entry_border, bd=1, relief=tk.SOLID)
    username_entry_frame.pack(fill=tk.X)
    
    username_inner = tk.Frame(username_entry_frame, bg=surface_bg)
    username_inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
    
    username_icon = tk.Label(
        username_inner,
        text="👤",
        bg=surface_bg,
        fg=text_secondary,
        font=("{Segoe UI} 14")
    )
    username_icon.pack(side=tk.LEFT, padx=(0, 10))
    
    username_entry = tk.Entry(
        username_inner,
        textvariable=username_var,
        font=("{Segoe UI} 12"),
        relief=tk.FLAT,
        bd=0,
        bg=surface_bg,
        fg=text_primary,
        insertbackground=accent_color,
        highlightthickness=0
    )
    username_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    username_entry.focus()
    username_entry.select_range(0, tk.END)
    
    def on_username_focus_in(e):
        username_entry_frame.configure(bg=accent_color, bd=2)
        username_icon.config(fg=accent_color)
    
    def on_username_focus_out(e):
        username_entry_frame.configure(bg=entry_border, bd=1)
        username_icon.config(fg=text_secondary)
    
    username_entry.bind('<FocusIn>', on_username_focus_in)
    username_entry.bind('<FocusOut>', on_username_focus_out)
    
    # Password field
    password_frame = tk.Frame(form_frame, bg=surface_bg)
    password_frame.pack(fill=tk.X, pady=(0, 20))
    
    password_label = tk.Label(
        password_frame,
        text="Password",
        bg=surface_bg,
        fg=text_primary,
        font=("{Segoe UI Semibold} 11")
    )
    password_label.pack(anchor=tk.W, pady=(0, 10))
    
    password_var = tk.StringVar(value="")  # SECURITY: No default password
    password_show_var = tk.BooleanVar(value=False)
    
    password_entry_frame = tk.Frame(password_frame, bg=entry_border, bd=1, relief=tk.SOLID)
    password_entry_frame.pack(fill=tk.X)
    
    password_inner_frame = tk.Frame(password_entry_frame, bg=surface_bg)
    password_inner_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
    # Use grid for better control
    password_inner_frame.grid_columnconfigure(1, weight=1)
    
    password_icon = tk.Label(
        password_inner_frame,
        text="🔒",
        bg=surface_bg,
        fg=text_secondary,
        font=("{Segoe UI} 14")
    )
    password_icon.grid(row=0, column=0, padx=(0, 10), sticky="w")
    
    # Entry container that will expand
    entry_container = tk.Frame(password_inner_frame, bg=surface_bg)
    entry_container.grid(row=0, column=1, sticky="ew", padx=(0, 8))
    
    password_entry = tk.Entry(
        entry_container,
        textvariable=password_var,
        font=("{Segoe UI} 12"),
        relief=tk.FLAT,
        bd=0,
        bg=surface_bg,
        fg=text_primary,
        show="*",
        insertbackground=accent_color,
        highlightthickness=0
    )
    password_entry.pack(fill=tk.BOTH, expand=True)
    
    def toggle_password():
        if password_show_var.get():
            password_entry.config(show="*")
            toggle_btn.config(text="👁️")
            password_show_var.set(False)
        else:
            password_entry.config(show="")
            toggle_btn.config(text="👁️‍🗨️")
            password_show_var.set(True)
    
    toggle_btn = tk.Button(
        password_inner_frame,
        text="👁️",
        command=toggle_password,
        bg=surface_bg,
        fg=text_secondary,
        relief=tk.FLAT,
        bd=0,
        cursor="hand2",
        font=("{Segoe UI} 13"),
        activebackground=surface_bg,
        activeforeground=accent_color,
        padx=4,
        pady=0
    )
    toggle_btn.grid(row=0, column=2, sticky="e")
    
    def on_password_focus_in(e):
        password_entry_frame.configure(bg=accent_color, bd=2)
        password_icon.config(fg=accent_color)
    
    def on_password_focus_out(e):
        password_entry_frame.configure(bg=entry_border, bd=1)
        password_icon.config(fg=text_secondary)
    
    password_entry.bind('<FocusIn>', on_password_focus_in)
    password_entry.bind('<FocusOut>', on_password_focus_out)
    
    # Error message label - place it in form_frame to avoid layout issues
    # Create a dedicated error frame that's always present but empty
    error_frame = tk.Frame(form_frame, bg=surface_bg, height=60)  # Fixed height
    error_frame.pack(fill=tk.X, pady=(0, 10), after=password_frame)
    error_frame.pack_propagate(False)  # Prevent frame from shrinking
    
    error_label = tk.Label(
        error_frame,
        text="",
        bg=surface_bg,
        fg="#ef4444",
        font=("{Segoe UI} 10"),
        wraplength=350,
        justify=tk.LEFT,
        anchor="nw"
    )
    error_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    error_label_packed = [False]
    
    # Login result
    login_result: Optional[Dict[str, Any]] = None
    is_loading = [False]
    
    def show_error(message: str):
        error_label.config(text=message)
        error_label_packed[0] = True
        # Ensure window stays visible
        login_window.update_idletasks()
        login_window.lift()
        login_window.focus_force()
    
    def hide_error():
        error_label.config(text="")
        error_label_packed[0] = False
    
    def do_login():
        nonlocal login_result
        if is_loading[0]:
            return
        
        hide_error()
        # Get values directly from entry widgets to ensure we have the actual input
        username = username_entry.get().strip()
        password = password_entry.get()  # Get directly from entry widget, not StringVar
        
        logger.debug(f"Login attempt - Username: '{username}' (length: {len(username)})")
        logger.debug(f"Login attempt - Password: length={len(password)}, first_char='{password[0] if password else 'N/A'}'")
        
        # Validate inputs
        if not username:
            show_error("Please enter your username")
            username_entry.focus()
            return
        
        if not password:
            show_error("Please enter your password")
            password_entry.focus()
            return
        
        # Additional validation - ensure password is not just whitespace
        password = password.strip()
        if not password:
            show_error("Please enter your password")
            password_entry.focus()
            return
        
        is_loading[0] = True
        login_btn.config(text="Signing in...", state=tk.DISABLED, bg=accent_color)
        login_window.update()
        
        try:
            # Call authentication - this should return None on failure, dict on success
            logger.info(f"Attempting login for user: '{username}'")
            logger.info(f"Password provided: length={len(password)}, first_char='{password[0] if password else 'N/A'}'")
            logger.info(f"Password value (for debugging): '{password}'")
            user_info = auth_module.authenticate_user(username, password)
            
            # CRITICAL SECURITY CHECK: Explicitly validate the authentication result
            # authenticate_user MUST return None on failure - never trust a truthy value
            if user_info is None:
                logger.warning(f"Authentication failed for user: '{username}' - authenticate_user returned None")
                user_info = None  # Explicitly set to None for clarity
            elif not isinstance(user_info, dict):
                logger.error(f"SECURITY ERROR: Unexpected return type from authenticate_user: {type(user_info)} - rejecting login")
                user_info = None
            elif not user_info.get('id'):
                logger.error(f"SECURITY ERROR: Invalid user_info returned: missing 'id' field - rejecting login")
                user_info = None
            elif not user_info.get('username'):
                logger.error(f"SECURITY ERROR: Invalid user_info returned: missing 'username' field - rejecting login")
                user_info = None
            elif user_info.get('username') != username:
                logger.error(f"SECURITY ERROR: Username mismatch - requested '{username}', got '{user_info.get('username')}' - rejecting login")
                user_info = None
            else:
                logger.info(f"Authentication result validated for user: '{username}' (id: {user_info.get('id')})")
            
            # Final check - only proceed if user_info is a valid dict with required fields
            if user_info and isinstance(user_info, dict) and user_info.get('id') and user_info.get('username') == username:
                # Authentication successful
                logger.info(f"Authentication successful for user: {username}")
                try:
                    session_token = auth_module.create_session(
                        user_info['id'],
                        user_info['username'],
                        user_info.get('role_id')
                    )
                    login_result = {
                        "user": user_info,
                        "session_token": session_token
                    }
                    # Release grab before destroying
                    try:
                        login_window.grab_release()
                    except:
                        pass
                    # Quit mainloop if it's a root window, then destroy
                    if not use_toplevel:
                        login_window.quit()
                    login_window.destroy()
                except Exception as session_error:
                    logger.error(f"Error creating session: {session_error}", exc_info=True)
                    show_error(f"Login failed: Could not create session. Please try again.")
                    password_entry.delete(0, tk.END)  # Clear directly from entry widget
                    password_var.set("")  # Also clear the StringVar
                    password_entry.focus()
            else:
                # Check if user exists
                try:
                    from . import db
                    conn = db.get_connection()
                    try:
                        cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
                        user_exists = cur.fetchone() is not None
                        if not user_exists:
                            show_error(f"User '{username}' not found.\n\nDefault credentials:\nUsername: admin\nPassword: admin")
                        else:
                            show_error("Invalid password.\n\nIf this is your first login, use:\nUsername: admin\nPassword: admin")
                    finally:
                        conn.close()
                except Exception:
                    show_error("Invalid username or password")
                # Clear password and refocus
                password_entry.delete(0, tk.END)  # Clear directly from entry widget
                password_var.set("")  # Also clear the StringVar
                login_window.update_idletasks()
                login_window.lift()  # Ensure window stays on top
                login_window.focus_force()
                password_entry.focus()
                password_entry.icursor(0)
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            show_error(f"Login failed: {str(e)}")
            # Clear password and refocus
            password_entry.delete(0, tk.END)  # Clear directly from entry widget
            password_var.set("")  # Also clear the StringVar
            login_window.update_idletasks()
            login_window.lift()  # Ensure window stays on top
            login_window.focus_force()
            password_entry.focus()
            password_entry.icursor(0)
        finally:
            is_loading[0] = False
            try:
                if login_window.winfo_exists():
                    login_btn.config(text="Sign In", state=tk.NORMAL, bg=accent_color)
                    # Ensure window is visible and on top
                    login_window.update_idletasks()
                    login_window.lift()
                    login_window.focus_force()
            except (tk.TclError, AttributeError):
                pass
    
    def on_cancel():
        # Release grab before destroying
        try:
            login_window.grab_release()
        except:
            pass
        # Quit mainloop if it's a root window, then destroy
        if not use_toplevel:
            login_window.quit()
        login_window.destroy()
    
    # Bind Enter key
    username_entry.bind('<Return>', lambda e: password_entry.focus())
    password_entry.bind('<Return>', lambda e: do_login())
    
    # Buttons frame - ensure it's at the bottom and always visible
    btn_frame = tk.Frame(content_frame, bg=surface_bg)
    btn_frame.pack(fill=tk.X, pady=(20, 0))
    btn_frame.grid_columnconfigure(1, weight=1)
    
    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        command=on_cancel,
        bg="#6b7280",
        fg="white",
        padx=35,
        pady=14,
        font=("{Segoe UI Semibold} 11"),
        cursor="hand2",
        relief=tk.FLAT,
        bd=0,
        activebackground="#4b5563",
        activeforeground="white",
        width=12
    )
    cancel_btn.grid(row=0, column=0, padx=(0, 12), sticky="w")
    
    login_btn = tk.Button(
        btn_frame,
        text="Sign In",
        command=do_login,
        bg=accent_color,
        fg="white",
        padx=35,
        pady=14,
        font=("{Segoe UI Semibold} 11"),
        cursor="hand2",
        relief=tk.FLAT,
        bd=0,
        activebackground=accent_hover,
        activeforeground="white"
    )
    login_btn.grid(row=0, column=1, sticky="ew", padx=(0, 0))
    
    def on_login_enter(e):
        if not is_loading[0]:
            login_btn.config(bg=accent_hover)
    
    def on_login_leave(e):
        if not is_loading[0]:
            login_btn.config(bg=accent_color)
    
    login_btn.bind('<Enter>', on_login_enter)
    login_btn.bind('<Leave>', on_login_leave)
    
    # Handle window close
    login_window.protocol('WM_DELETE_WINDOW', on_cancel)
    
    # Force update to ensure all widgets are rendered and buttons are visible
    login_window.update_idletasks()
    login_window.update()
    
    # Verify buttons are visible
    try:
        btn_y = btn_frame.winfo_y()
        btn_height = btn_frame.winfo_height()
        window_height = login_window.winfo_height()
        # If buttons are cut off, adjust window height
        if btn_y + btn_height > window_height - 30:
            new_height = btn_y + btn_height + 50
            login_window.geometry(f"{width}x{new_height}+{x}+{y}")
            login_window.update_idletasks()
    except Exception:
        pass
    
    # Ensure window is visible and on top
    if not use_toplevel:
        # For root window, make sure it's shown
        login_window.deiconify()
    login_window.focus_force()
    login_window.lift()
    login_window.attributes('-topmost', True)  # Ensure it's on top
    login_window.update()
    
    if use_toplevel:
        # If it's a Toplevel, use wait_window
        login_window.wait_window()
    else:
        # If it's a root window, we need to run mainloop
        # The mainloop will exit when quit() is called
        login_window.mainloop()
        # After mainloop exits, destroy the window if it still exists
        try:
            if login_window.winfo_exists():
                login_window.destroy()
        except:
            pass
    
    return login_result

