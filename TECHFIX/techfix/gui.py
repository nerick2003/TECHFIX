from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import tkinter.font as tkfont
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import calendar
from typing import Optional, Sequence, List, Dict
import json
import sys
import subprocess
import platform
try:
    import winreg
except Exception:
    winreg = None

# Support running as a module (package) or as a script
try:
    if __package__:
        from . import db  # type: ignore
        from .accounting import AccountingEngine, JournalLine  # type: ignore
    else:
        raise ImportError
except Exception:
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from techfix import db  # type: ignore
    from techfix.accounting import AccountingEngine, JournalLine  # type: ignore



THEMES = {
    "Light": {
        "app_bg": "#f5f7fb",
        "surface_bg": "#ffffff",
        "accent_color": "#2563eb",
        "accent_hover": "#1d4ed8",
        "accent_disabled": "#93c5fd",
        "text_primary": "#1f2937",
        "text_secondary": "#4b5563",
        "subtitle_fg": "#dbeafe",
        "entry_border": "#d8dee9",
        "entry_disabled_bg": "#e5e7eb",
        "table_stripe": "#eef2ff",
        "tree_heading_bg": "#e2e8f0",
        "tree_selected_bg": "#dbeafe",
        "tab_selected_bg": "#e0ecff",
        "tab_active_bg": "#e8f0ff",
    },
    "Dark": {
        "app_bg": "#111827",
        "surface_bg": "#1f2937",
        "accent_color": "#2563eb",
        "accent_hover": "#1d4ed8",
        "accent_disabled": "#1e3a8a",
        "text_primary": "#f9fafb",
        "text_secondary": "#9ca3af",
        "subtitle_fg": "#bfdbfe",
        "entry_border": "#374151",
        "entry_disabled_bg": "#4b5563",
        "table_stripe": "#1b2534",
        "tree_heading_bg": "#374151",
        "tree_selected_bg": "#1e3a8a",
        "tab_selected_bg": "#1e293b",
        "tab_active_bg": "#24324a",
    },
}

FONT_BASE = "{Segoe UI} 10"
FONT_BOLD = "{Segoe UI Semibold} 11"
FONT_TAB = "{Segoe UI Semibold} 10"
FONT_MONO = "{Cascadia Mono} 11"


class TechFixApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TechFix Solutions - Accounting System")
        
        # Set minimum window size
        self.minsize(1024, 720)
        
        # Make the root window expandable
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # Start in a large centered window (easier for modern UI)
        self.update_idletasks()
        width, height = 1200, 800
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        try:
            self._load_window_settings()
        except Exception:
            pass

        try:
            self._apply_theme(self._get_system_theme(), initial=True)
        except Exception:
            pass

        # Bind F11 to toggle fullscreen (still available)
        self.bind('<F11>', lambda e: self.attributes('-fullscreen', not self.attributes('-fullscreen')))
        self.bind('<Escape>', lambda e: self.attributes('-fullscreen', False))
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        
        # Handle window resize
        self.bind('<Configure>', self._on_window_resize)

        db.init_db(reset=False)
        conn = db.get_connection()
        db.seed_chart_of_accounts(conn)
        conn.close()

        self.engine = AccountingEngine()
        self.periods: List = []
        self.current_period_id: Optional[int] = self.engine.current_period_id
        self.cycle_status_rows: List = []
        self._scroll_canvases: list[tk.Canvas] = []
        self._nav_buttons: list = []
        self.period_form_cache: Dict[int, Dict[str, str]] = {}
        self._last_period_id: Optional[int] = self.current_period_id

        self.style = ttk.Style(self)
        # Initialize theme and palette before building UI
        self.theme_name = "Light"
        self.palette = THEMES[self.theme_name]
        self._configure_style()
        
        self._build_ui()
        
        # Apply theme to all widgets after UI is built
        
        self._update_theme_widgets()
        self._load_periods()
        self._update_theme_widgets()
        self._load_all_views()

        try:
            self._start_theme_monitor()
        except Exception:
            pass

    def destroy(self) -> None:
        try:
            self.engine.close()
        finally:
            super().destroy()

    def _apply_theme(self, name: str, *, initial: bool = False) -> None:
        if name not in THEMES or name == self.theme_name:
            return

        if initial:
            self.theme_name = name
            self.palette = THEMES[name]
            self._configure_style()
            if hasattr(self, 'light_btn') and hasattr(self, 'dark_btn'):
                self.light_btn.configure(style="Techfix.Theme.Selected.TButton" if name == "Light" else "Techfix.Theme.TButton")
                self.dark_btn.configure(style="Techfix.Theme.Selected.TButton" if name == "Dark" else "Techfix.Theme.TButton")
            self._update_theme_widgets()
            try:
                self.set_status(f"Theme: {name}")
                self._save_window_settings()
            except Exception:
                pass
            return

        try:
            if getattr(self, '_theme_animating', False):
                return
            self._animate_theme_switch(name)
        except Exception:
            # Fallback to immediate apply if animation fails
            self.theme_name = name
            self.palette = THEMES[name]
            self._configure_style()
            if hasattr(self, 'light_btn') and hasattr(self, 'dark_btn'):
                self.light_btn.configure(style="Techfix.Theme.Selected.TButton" if name == "Light" else "Techfix.Theme.TButton")
                self.dark_btn.configure(style="Techfix.Theme.Selected.TButton" if name == "Dark" else "Techfix.Theme.TButton")
            self._update_theme_widgets()
            try:
                self.set_status(f"Theme: {name}")
                self._save_window_settings()
            except Exception:
                pass

    def _configure_style(self) -> None:
        colors = self.palette

        self.configure(bg=colors["app_bg"])
        self.option_add("*Font", FONT_BASE)
        self.option_add("*TCombobox*Listbox.font", FONT_BASE)
        # Ensure dropdown popups (Combobox listbox) and menus are readable in both themes
        try:
            self.option_add("*TCombobox*Listbox.background", colors.get("surface_bg", "#ffffff"))
            self.option_add("*TCombobox*Listbox.foreground", colors.get("text_primary", "#000000"))
            self.option_add("*TCombobox*Listbox.selectBackground", colors.get("accent_color", "#2563eb"))
            self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
            self.option_add("*Menu.background", colors.get("surface_bg", "#ffffff"))
            self.option_add("*Menu.foreground", colors.get("text_primary", "#000000"))
            self.option_add("*Menu.activeBackground", colors.get("accent_color", "#2563eb"))
            self.option_add("*Menu.activeForeground", "#ffffff")
            self.option_add("*Menu.relief", "flat")
        except Exception:
            pass

        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure("TFrame", background=colors["app_bg"])
        self.style.configure("Techfix.App.TFrame", background=colors["app_bg"])
        self.style.configure("Techfix.Surface.TFrame", background=colors["surface_bg"])
        self.style.configure("TLabel", background=colors["surface_bg"], foreground=colors["text_primary"], font=FONT_BASE)

        self.style.configure(
            "Techfix.Headline.TLabel",
            background=colors["accent_color"],
            foreground="#ffffff",
            font="{Segoe UI Semibold} 14",
        )
        self.style.configure(
            "Techfix.Subtitle.TLabel",
            background=colors["accent_color"],
            foreground=colors["subtitle_fg"],
            font=FONT_BASE,
        )
        try:
            tkfont.Font(name="TechfixBrandFont", family="Arial Black", size=17)
        except Exception:
            try:
                tkfont.Font(name="TechfixBrandFont", family="Arial", size=17, weight="bold")
            except Exception:
                try:
                    tkfont.Font(name="TechfixBrandFont", family="Segoe UI", size=17, weight="bold")
                except Exception:
                    pass
        self.style.configure(
            "Techfix.SidebarBrand.TLabel",
            background=colors["surface_bg"],
            foreground=colors["accent_color"],
            font="TechfixBrandFont",
        )
        self.style.configure(
            "Techfix.Brand.TLabel",
            background=colors["app_bg"],
            foreground=colors["accent_color"],
            font="{Segoe UI Semibold} 16",
        )

        self.style.configure(
            "Techfix.TLabelframe",
            background=colors["surface_bg"],
            foreground=colors["text_secondary"],
            borderwidth=0,
            padding=12,
        )
        self.style.configure(
            "Techfix.TLabelframe.Label",
            background=colors["surface_bg"],
            foreground=colors["accent_color"],
            font=FONT_BOLD,
        )

        # Monkeypatch ttk.Label to inherit visible bg/fg from parent when not explicitly provided.
        # This reduces text 'halo' artifacts on colored backgrounds by ensuring labels draw with
        # a matching background color and a contrasting foreground.
        try:
            _orig_ttk_label_init = ttk.Label.__init__

            def _contrast_color(hexcolor: str) -> str:
                try:
                    h = hexcolor.lstrip('#')
                    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                    # relative luminance
                    lum = (0.2126 * (r/255.0) + 0.7152 * (g/255.0) + 0.0722 * (b/255.0))
                    return '#ffffff' if lum < 0.55 else colors.get('text_primary', '#000000')
                except Exception:
                    return colors.get('text_primary', '#000000')

            def _patched_label_init(self, master=None, *args, **kwargs):
                try:
                    # If background not given, attempt to inherit parent's bg
                    if ('background' not in kwargs) and ('bg' not in kwargs):
                        if master is not None:
                            try:
                                parent_bg = master.cget('bg')
                                if parent_bg:
                                    kwargs['background'] = parent_bg
                            except Exception:
                                pass

                    # If foreground not given, pick a contrasting color based on background
                    if 'foreground' not in kwargs and 'fg' not in kwargs:
                        bg = kwargs.get('background') or (master.cget('bg') if master is not None else None)
                        if isinstance(bg, str) and bg.startswith('#'):
                            kwargs['foreground'] = _contrast_color(bg)
                        else:
                            kwargs['foreground'] = colors.get('text_primary', '#000000')
                except Exception:
                    pass
                return _orig_ttk_label_init(self, master, *args, **kwargs)

            ttk.Label.__init__ = _patched_label_init
        except Exception:
            pass

        self.style.configure(
            "Techfix.TNotebook",
            background=colors["app_bg"],
            borderwidth=0,
            padding=6,
        )
        self.style.configure(
            "Techfix.AppBar.TLabel",
            background=colors["app_bg"],
            foreground=colors["text_secondary"],
            font=FONT_BASE,
        )
        self.style.configure(
            "Techfix.TNotebook.Tab",
            background=colors["surface_bg"],
            foreground=colors["text_primary"],
            padding=(18, 10),
            font=FONT_TAB,
        )
        self.style.map(
            "Techfix.TNotebook.Tab",
            background=[("selected", colors["tab_selected_bg"]), ("active", colors["tab_active_bg"])],
            foreground=[("selected", colors["text_primary"])],
        )

        self.style.configure(
            "Techfix.TButton",
            background=colors["accent_color"],
            foreground="#ffffff",
            padding=(16, 8),
            borderwidth=0,
            # remove focus thickness/color to avoid drawing focus outlines that look like shadows
        )
        self.style.map(
            "Techfix.TButton",
            background=[("active", colors["accent_hover"]), ("disabled", colors["accent_disabled"])],
            foreground=[("disabled", "#ffffff")],
        )

        # Navigation / Sidebar button style
        self.style.configure(
            "Techfix.Nav.TButton",
            background=colors["surface_bg"],
            foreground=colors["text_primary"],
            padding=(12, 10),
            anchor="w",
            font=FONT_BASE,
            relief="flat",
        )
        self.style.map(
            "Techfix.Nav.TButton",
            background=[("active", colors.get("tab_active_bg")), ("selected", colors.get("tab_selected_bg"))],
            foreground=[("active", colors.get("text_primary"))],
        )
        # Selected variant: accent background with white foreground
        self.style.configure(
            "Techfix.Nav.Selected.TButton",
            background=colors["accent_color"],
            foreground="#ffffff",
            padding=(12, 10),
            anchor="w",
            font=FONT_BASE,
            relief="flat",
        )
        self.style.map(
            "Techfix.Nav.Selected.TButton",
            background=[("active", colors.get("accent_hover"))],
            foreground=[("active", "#ffffff")],
        )

        # Theme toggle button styles
        self.style.configure(
            "Techfix.Theme.TButton",
            background=colors["surface_bg"],
            foreground=colors["text_primary"],
            padding=(10, 6),
            borderwidth=1,
            relief="solid",
        )
        self.style.map(
            "Techfix.Theme.TButton",
            background=[("active", colors.get("tab_active_bg"))],
            foreground=[("active", colors.get("text_primary"))],
        )
        self.style.configure(
            "Techfix.Theme.Selected.TButton",
            background=colors["accent_color"],
            foreground="#ffffff",
            padding=(10, 6),
            borderwidth=1,
            relief="solid",
        )
        self.style.map(
            "Techfix.Theme.Selected.TButton",
            background=[("active", colors.get("accent_hover"))],
            foreground=[("active", "#ffffff")],
        )

        self.style.configure(
            "Techfix.TCheckbutton",
            background=colors["surface_bg"],
            foreground=colors["text_primary"],
            padding=4,
        )
        self.style.configure(
            "Techfix.TEntry",
            fieldbackground=colors["surface_bg"],
            background=colors["surface_bg"],
            foreground=colors["text_primary"],
            borderwidth=0,
            padding=6,
        )
        self.style.map(
            "Techfix.TEntry",
            fieldbackground=[("disabled", colors["entry_disabled_bg"])],
        )

        self.style.configure(
            "Techfix.TCombobox",
            fieldbackground=colors["surface_bg"],
            background=colors["surface_bg"],
            foreground=colors["text_primary"],
            borderwidth=0,
            padding=6,
        )

        self.style.configure(
            "Techfix.Treeview",
            background=colors["surface_bg"],
            fieldbackground=colors["surface_bg"],
            foreground=colors["text_primary"],
            rowheight=26,
            borderwidth=0,
        )
        self.style.configure(
            "Techfix.Treeview.Heading",
            background=colors["tree_heading_bg"],
            foreground=colors["text_primary"],
            font=FONT_BOLD,
        )
        self.style.map(
            "Techfix.Treeview",
            background=[("selected", colors["tree_selected_bg"])],
            foreground=[("selected", colors["text_primary"])],
        )
        self.style.layout("Techfix.Treeview", self.style.layout("Treeview"))

        self.style.configure(
            "Techfix.StatusBar.TLabel",
            background=colors.get("app_bg", "#ffffff"),
            foreground=colors.get("text_secondary", "#4b5563"),
            font=FONT_BASE,
        )

        self.style.configure(
            "Techfix.Danger.TButton",
            background="#dc2626",
            foreground="#ffffff",
            padding=(16, 8),
            borderwidth=0,
        )
        self.style.map(
            "Techfix.Danger.TButton",
            background=[("active", "#b91c1c"), ("disabled", "#ef4444")],
            foreground=[("disabled", "#ffffff")],
        )

    def _update_theme_widgets(self) -> None:
        """Apply current palette colors to widgets that need manual updates."""
        try:
            colors = self.palette

            # Update root/background colors
            self.configure(bg=colors.get("app_bg", "#ffffff"))

            # Update any stored scroll canvases
            if hasattr(self, '_scroll_canvases'):
                for c in getattr(self, '_scroll_canvases'):
                    try:
                        c.configure(bg=colors.get('surface_bg', '#ffffff'))
                    except Exception:
                        pass

            # Update any Text widgets created for financial statements
            for attr in ('income_text', 'balance_sheet_text', 'cash_flow_text', 'close_log', 'txn_memo'):
                if hasattr(self, attr):
                    w = getattr(self, attr)
                    try:
                        w.configure(
                            bg=colors.get('surface_bg', '#ffffff'),
                            fg=colors.get('text_primary', '#000000'),
                            insertbackground=colors.get('text_primary', '#000000'),
                            selectbackground=colors.get('accent_color', '#2563eb'),
                            selectforeground='#ffffff'
                        )
                        try:
                            w.configure(
                                bd=1,
                                relief=tk.SOLID,
                                highlightthickness=1,
                                highlightbackground=colors.get('entry_border', '#d8dee9'),
                                highlightcolor=colors.get('accent_color', '#2563eb'),
                            )
                        except Exception:
                            pass
                        # Update commonly used tags so previously-inserted tagged text remains visible after theme change
                        try:
                            w.tag_configure('header', foreground=colors.get('accent_color', '#2563eb'))
                            w.tag_configure('subheader', foreground=colors.get('text_secondary', '#4b5563'))
                            w.tag_configure('section', foreground=colors.get('text_primary', '#1f2937'))
                            w.tag_configure('total', foreground=colors.get('text_primary', '#1f2937'))
                            w.tag_configure('net', foreground=colors.get('accent_color', '#2563eb'))
                            w.tag_configure('warning', foreground='red')
                        except Exception:
                            pass
                    except Exception:
                        pass

            # Update treeview heading/background via styles (ensure maps are applied)
            try:
                self.style.configure('Techfix.Treeview', background=colors.get('surface_bg'))
                self.style.configure('Techfix.Treeview.Heading', background=colors.get('tree_heading_bg'))
            except Exception:
                pass

            # Refresh sidebar brand canvas to match theme
            try:
                if hasattr(self, 'sidebar_brand_canvas'):
                    self.sidebar_brand_canvas.configure(bg=colors.get('surface_bg', '#ffffff'))
                    self._draw_sidebar_brand()
            except Exception:
                pass

            # If financial statements already have content, re-generate them
            # so tag colors and formatting are applied for the new theme.
            try:
                if hasattr(self, 'income_text') and self.income_text.get("1.0", tk.END).strip():
                    try:
                        # Re-generate financial statement text without updating cycle status
                        self._regenerate_financial_statements(self.fs_date_to.get().strip() if hasattr(self, 'fs_date_to') else None)
                    except Exception:
                        pass
            except Exception:
                pass

            # Ensure existing Treeview widgets have readable row colors (tag and retag rows)
            try:
                for name in dir(self):
                    try:
                        obj = getattr(self, name)
                    except Exception:
                        continue
                    if isinstance(obj, ttk.Treeview):
                        try:
                            # Configure a generic 'row' tag with proper colors
                            obj.tag_configure('row', background=colors.get('surface_bg', '#ffffff'), foreground=colors.get('text_primary', '#000000'))
                            # Ensure totals rows reflect current theme
                            obj.tag_configure('totals', background=colors.get('tab_selected_bg', '#e0ecff'), foreground=colors.get('text_primary', '#000000'))
                            # Retag existing rows so the tag applies immediately
                            for iid in obj.get_children():
                                tags = tuple(obj.item(iid, 'tags') or ())
                                if 'row' not in tags:
                                    obj.item(iid, tags=(*tags, 'row'))
                        except Exception:
                            pass
            except Exception:
                pass

            # Update sidebar indicators and button styles to match theme
            try:
                if hasattr(self, '_nav_buttons'):
                    cur = getattr(self, '_current_nav_index', None)
                    for idx, (ind, btn) in enumerate(self._nav_buttons):
                        try:
                            ind.configure(bg=(colors.get('accent_color') if cur == idx else colors.get('surface_bg')),
                                          highlightthickness=0, bd=0, relief=tk.FLAT)
                        except Exception:
                            pass
                        try:
                            btn.configure(style=('Techfix.Nav.Selected.TButton' if cur == idx else 'Techfix.Nav.TButton'))
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                self._style_all_combobox_popdowns()
            except Exception:
                pass
            try:
                self._style_menus()
            except Exception:
                pass

        except Exception:
            # Don't let theme update errors break app initialization
            pass

    def _draw_sidebar_brand(self) -> None:
        try:
            if not hasattr(self, 'sidebar_brand_canvas'):
                return
            c = self.sidebar_brand_canvas
            colors = self.palette
            c.delete('all')
            w = c.winfo_width() or c.winfo_reqwidth()
            h = c.winfo_height() or 30
            text = 'Techfix'
            accent = colors.get('accent_color', '#2563eb')
            # Letter spacing rendering: draw per-character with small gaps and multi-offset for thickness
            try:
                fnt = tkfont.nametofont('TechfixBrandFont')
            except Exception:
                fnt = None
            spacing = 3
            try:
                widths = [int(fnt.measure(ch)) for ch in text] if fnt else [12 for _ in text]
            except Exception:
                widths = [12 for _ in text]
            total = sum(widths) + spacing * max(0, len(text) - 1)
            start_x = int((w - total) / 2)
            y = int(h / 2)
            offsets = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]
            x = start_x
            for i, ch in enumerate(text):
                # Draw outlines for thickness
                for dx, dy in offsets:
                    try:
                        c.create_text(x + dx, y + dy, text=ch, fill=accent, font='TechfixBrandFont', anchor='w')
                    except Exception:
                        pass
                # Draw the main glyph
                c.create_text(x, y, text=ch, fill=accent, font='TechfixBrandFont', anchor='w')
                x += widths[i] + spacing
        except Exception:
            pass

    def _animate_theme_switch(self, name: str, *, duration_ms: int = 300) -> None:
        try:
            self._theme_animating = True
            self.update_idletasks()
            w = max(1, self.winfo_width() or 1200)
            h = max(1, self.winfo_height() or 800)

            new_palette = THEMES[name]
            overlay = tk.Canvas(self, highlightthickness=0, bd=0, bg=self.palette.get('app_bg', '#ffffff'))
            overlay.place(x=0, y=0, width=w, height=h)
            try:
                overlay.lift()
            except Exception:
                pass

            steps = max(10, int(duration_ms / 15))
            dy = h / float(steps)
            if name == "Dark":
                rect = overlay.create_rectangle(0, 0, w, 1, fill=new_palette.get('surface_bg', '#ffffff'), outline="")
                def coords_for_step(i):
                    return (0, 0, w, int(min(h, i * dy)))
            else:
                rect = overlay.create_rectangle(0, h-1, w, h, fill=new_palette.get('surface_bg', '#ffffff'), outline="")
                def coords_for_step(i):
                    y1 = int(max(0, h - i * dy))
                    return (0, y1, w, h)
            i = 0

            def sweep():
                nonlocal i
                i += 1
                overlay.coords(rect, *coords_for_step(i))
                if i < steps:
                    self.after(15, sweep)
                else:
                    try:
                        self.theme_name = name
                        self.palette = new_palette
                        self._configure_style()
                        if hasattr(self, 'light_btn') and hasattr(self, 'dark_btn'):
                            self.light_btn.configure(style="Techfix.Theme.Selected.TButton" if name == "Light" else "Techfix.Theme.TButton")
                            self.dark_btn.configure(style="Techfix.Theme.Selected.TButton" if name == "Dark" else "Techfix.Theme.TButton")
                        self._update_theme_widgets()
                        self.set_status(f"Theme: {name}")
                        self._save_window_settings()
                    except Exception:
                        pass
                    try:
                        overlay.place_forget()
                        overlay.destroy()
                    except Exception:
                        pass
                    self._theme_animating = False

            sweep()
        except Exception:
            self._theme_animating = False

    def _get_system_theme(self) -> str:
        try:
            os_name = platform.system()
            if os_name == "Windows" and winreg:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return "Light" if int(val) != 0 else "Dark"
                except Exception:
                    return "Light"
            if os_name == "Darwin":
                try:
                    out = subprocess.check_output(["defaults", "read", "-g", "AppleInterfaceStyle"], stderr=subprocess.STDOUT)
                    s = out.decode().strip()
                    return "Dark" if s.lower().startswith("dark") else "Light"
                except Exception:
                    return "Light"
            return "Light"
        except Exception:
            return "Light"

    def _start_theme_monitor(self) -> None:
        try:
            self._last_system_theme = self._get_system_theme()
            def _poll():
                try:
                    cur = self._get_system_theme()
                    if cur != getattr(self, "_last_system_theme", cur):
                        self._last_system_theme = cur
                        try:
                            self._apply_theme(cur)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    self.after(3000, _poll)
                except Exception:
                    pass
            _poll()
        except Exception:
            pass
    def _animate_view_transition(self, target: tk.Widget, *, duration_ms: int = 250) -> None:
        try:
            target.update_idletasks()
            w = max(1, target.winfo_width() or 800)
            h = max(1, target.winfo_height() or 600)
            overlay = tk.Canvas(target, highlightthickness=0, bd=0, bg=self.palette.get('surface_bg', '#ffffff'))
            overlay.place(x=0, y=0, width=w, height=h)
            try:
                overlay.lift()
            except Exception:
                pass
            steps = max(10, int(duration_ms / 15))
            dx = w / float(steps)
            rect = overlay.create_rectangle(0, 0, 1, h, fill=self.palette.get('surface_bg', '#ffffff'), outline="")
            i = 0
            def sweep():
                nonlocal i
                i += 1
                x2 = int(min(w, i * dx))
                overlay.coords(rect, 0, 0, x2, h)
                if i < steps:
                    self.after(15, sweep)
                else:
                    try:
                        overlay.place_forget()
                        overlay.destroy()
                    except Exception:
                        pass
            sweep()
        except Exception:
            pass

    def _animate_swipe_to(self, target: tk.Widget, *, direction: str = 'right', duration_ms: int = 250) -> None:
        try:
            # Slide the target frame into view using place, then restore pack
            parent = getattr(self, 'content_area', self)
            target.update_idletasks()
            parent.update_idletasks()
            w = max(1, parent.winfo_width() or target.winfo_width() or 800)
            h = max(1, parent.winfo_height() or target.winfo_height() or 600)
            try:
                target.pack_forget()
            except Exception:
                pass
            start_x = w if direction == 'right' else -w
            target.place(in_=parent, x=start_x, y=0, width=w, height=h)
            try:
                target.lift()
            except Exception:
                pass
            steps = max(10, int(duration_ms / 15))
            dx = w / float(steps)
            i = 0
            def step():
                nonlocal i, start_x
                i += 1
                if direction == 'right':
                    x = int(max(0, start_x - i * dx))
                else:
                    x = int(min(0, start_x + i * dx))
                target.place_configure(x=x)
                if i < steps:
                    self.after(15, step)
                else:
                    try:
                        target.place_forget()
                        target.pack(fill=tk.BOTH, expand=True)
                    except Exception:
                        pass
            step()
        except Exception:
            pass

    def _animate_tab_pulse(self, frame: tk.Widget, *, duration_ms: int = 200) -> None:
        try:
            colors = self.palette
            base = colors.get('surface_bg', '#ffffff')
            accent = colors.get('accent_color', '#2563eb')
            def hex_to_rgb(h: str):
                h = h.lstrip('#')
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            def rgb_to_hex(r: int, g: int, b: int):
                return f"#{r:02x}{g:02x}{b:02x}"
            r1, g1, b1 = hex_to_rgb(accent)
            r2, g2, b2 = hex_to_rgb(base)
            steps = max(8, int(duration_ms / 15))
            style_name = f"Techfix.Pulse.{id(frame)}.TFrame"
            self.style.configure(style_name, background=accent)
            frame.configure(style=style_name)
            i = 0
            def step():
                nonlocal i
                i += 1
                t = i / float(steps)
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
                c = rgb_to_hex(r, g, b)
                try:
                    self.style.configure(style_name, background=c)
                except Exception:
                    pass
                if i < steps:
                    self.after(15, step)
                else:
                    try:
                        frame.configure(style="Techfix.Surface.TFrame")
                    except Exception:
                        pass
            step()
        except Exception:
            pass

    def _style_combobox_popdown(self, cb: ttk.Combobox) -> None:
        try:
            colors = self.palette
            pop = cb.tk.call('ttk::combobox::PopdownWindow', cb)
            lb = self.nametowidget(f'{pop}.f.l')
            lb.configure(
                background=colors.get('surface_bg', '#ffffff'),
                foreground=colors.get('text_primary', '#000000'),
                selectbackground=colors.get('accent_color', '#2563eb'),
                selectforeground='#ffffff',
                highlightthickness=0,
                borderwidth=0,
            )
        except Exception:
            pass

    def _style_all_combobox_popdowns(self) -> None:
        try:
            for name in dir(self):
                try:
                    w = getattr(self, name)
                except Exception:
                    continue
                if isinstance(w, ttk.Combobox):
                    try:
                        self._style_combobox_popdown(w)
                    except Exception:
                        pass
        except Exception:
            pass

    def _style_menus(self) -> None:
        try:
            colors = self.palette
            for m in (getattr(self, 'menubar', None), getattr(self, 'file_menu', None), getattr(self, 'view_menu', None), getattr(self, 'help_menu', None)):
                if m is None:
                    continue
                try:
                    m.configure(
                        bg=colors.get('surface_bg', '#ffffff'),
                        fg=colors.get('text_primary', '#000000'),
                        activebackground=colors.get('accent_color', '#2563eb'),
                        activeforeground='#ffffff',
                        tearoff=False,
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def _on_window_resize(self, event=None):
        if hasattr(self, 'main_frame') and hasattr(self.main_frame, 'winfo_children'):
            self.main_frame.update_idletasks()
        try:
            # Auto-scale cycle table columns
            if hasattr(self, 'cycle_tree'):
                total = self.cycle_tree.winfo_width() or 1
                col_defs = {
                    'step': int(total * 0.08),
                    'name': int(total * 0.32),
                    'status': int(total * 0.18),
                    'note': int(total * 0.30),
                    'updated': int(total * 0.12),
                }
                for c, w in col_defs.items():
                    try:
                        self.cycle_tree.column(c, width=max(60, w))
                    except Exception:
                        pass
            # Ensure notebook grows with window
            if hasattr(self, 'notebook'):
                self.notebook.update_idletasks()
            # Auto-scale closing preview columns
            if hasattr(self, 'closing_preview_tree'):
                total = self.closing_preview_tree.winfo_width() or 1
                widths = {
                    'code': int(total * 0.15),
                    'name': int(total * 0.35),
                    'action': int(total * 0.30),
                    'amount': int(total * 0.20),
                }
                for c, w in widths.items():
                    try:
                        self.closing_preview_tree.column(c, width=max(80, w))
                    except Exception:
                        pass
            # Auto-scale recent transactions columns
            if hasattr(self, 'txn_recent_tree'):
                total = self.txn_recent_tree.winfo_width() or 1
                col_defs = {
                    'date': int(total * 0.12),
                    'reference': int(total * 0.10),
                    'description': int(total * 0.42),
                    'debit': int(total * 0.12),
                    'credit': int(total * 0.12),
                    'account': int(total * 0.12),
                }
                for c, w in col_defs.items():
                    try:
                        self.txn_recent_tree.column(c, width=max(80, w), stretch=(c == 'description'))
                    except Exception:
                        pass
            # Auto-scale journal columns
            if hasattr(self, 'journal_tree'):
                total = self.journal_tree.winfo_width() or 1
                col_defs = {
                    'date': int(total * 0.12),
                    'reference': int(total * 0.10),
                    'description': int(total * 0.42),
                    'debit': int(total * 0.12),
                    'credit': int(total * 0.12),
                    'account': int(total * 0.12),
                }
                for c, w in col_defs.items():
                    try:
                        self.journal_tree.column(c, width=max(80, w), stretch=(c == 'description'))
                    except Exception:
                        pass
        except Exception:
            pass

    def _load_window_settings(self):
        try:
            settings_path = db.DB_DIR / "settings.json"
            if settings_path.exists():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                geom = data.get("geometry")
                full = data.get("fullscreen")
                theme = data.get("theme")
                if isinstance(geom, str) and geom:
                    self.geometry(geom)
                if isinstance(full, bool):
                    self.attributes('-fullscreen', full)
                if isinstance(theme, str) and theme in THEMES:
                    self.theme_name = theme
                    self.palette = THEMES[theme]
        except Exception:
            pass

    def _save_window_settings(self):
        try:
            settings_path = db.DB_DIR / "settings.json"
            payload = {
                "geometry": self.winfo_geometry(),
                "fullscreen": bool(self.attributes('-fullscreen')),
                "theme": self.theme_name,
            }
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass

    def _on_close(self):
        try:
            self._save_window_settings()
        except Exception:
            pass
        self.destroy()

    def set_status(self, text: str) -> None:
        try:
            if hasattr(self, 'status_var'):
                self.status_var.set(str(text))
        except Exception:
            pass

    def _on_period_change(self, event=None):
        selected = self.period_var.get()
        if not selected:
            return
        for period_id, name in self.periods:
            if name == selected:
                # snapshot previous period form
                try:
                    if self._last_period_id:
                        snap = self._snapshot_txn_form()
                        if snap:
                            self.period_form_cache[int(self._last_period_id)] = snap
                except Exception:
                    pass
                self.current_period_id = period_id
                try:
                    self.engine.set_active_period(period_id)
                except Exception:
                    pass
                self._refresh_cycle_and_views()
                # apply cached form or prefill from last entry
                try:
                    snap = self.period_form_cache.get(int(period_id))
                    if snap:
                        self._apply_txn_form(snap)
                    else:
                        self._prefill_txn_from_last_entry()
                except Exception:
                    pass
                self._last_period_id = period_id
                break

    def _load_periods(self):
        try:
            rows = self.engine.list_periods()
            items = []
            for r in rows:
                name = r["name"] if isinstance(r, sqlite3.Row) else (r[1] if len(r) > 1 else "")
                pid = r["id"] if isinstance(r, sqlite3.Row) else r[0]
                items.append((pid, name))
            self.periods = items
            if hasattr(self, 'period_combo'):
                current = self.period_combo.get()
                self.period_combo['values'] = [p[1] for p in self.periods]
                if self.periods and not current:
                    self.current_period_id = self.periods[0][0]
                    self.period_var.set(self.periods[0][1])
                    try:
                        self.engine.set_active_period(self.current_period_id)
                    except Exception:
                        pass
        except Exception:
            pass

    def _prompt_new_period(self):
        """Show dialog to create a new accounting period."""
        # Create a simple dialog to get start and end dates
        class PeriodDialog(tk.Toplevel):
            def __init__(self, parent):
                super().__init__(parent)
                self.title("New Accounting Period")
                self.parent = parent
                self.result = None
                try:
                    self.configure(bg=parent.palette.get('surface_bg', '#ffffff'))
                except Exception:
                    pass
                
                # Make dialog modal
                self.transient(parent)
                self.grab_set()
                
                # Set focus
                self.focus_set()
                
                # Add widgets
                ttk.Label(self, text="Start Date (YYYY-MM-DD):", style="Techfix.TLabel").grid(row=0, column=0, padx=5, pady=5)
                self.start_entry = ttk.Entry(self, style="Techfix.TEntry")
                self.start_entry.grid(row=0, column=1, padx=5, pady=5)
                ttk.Button(self, text="📅", command=lambda: self._pick_date(self.start_entry), style="Techfix.Theme.TButton", width=3).grid(row=0, column=2, padx=2)
                
                ttk.Label(self, text="End Date (YYYY-MM-DD):", style="Techfix.TLabel").grid(row=1, column=0, padx=5, pady=5)
                self.end_entry = ttk.Entry(self, style="Techfix.TEntry")
                self.end_entry.grid(row=1, column=1, padx=5, pady=5)
                ttk.Button(self, text="📅", command=lambda: self._pick_date(self.end_entry), style="Techfix.Theme.TButton", width=3).grid(row=1, column=2, padx=2)
                
                btn_frame = ttk.Frame(self, style="Techfix.Surface.TFrame")
                btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
                
                ttk.Button(btn_frame, text="Create", command=self.on_ok, style="Techfix.TButton").pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="Cancel", command=self.on_cancel, style="Techfix.Theme.TButton").pack(side=tk.LEFT, padx=5)
                
                # Center the dialog
                self.update_idletasks()
                width = self.winfo_width()
                height = self.winfo_height()
                x = (self.winfo_screenwidth() // 2) - (width // 2)
                y = (self.winfo_screenheight() // 2) - (height // 2)
                self.geometry(f'{width}x{height}+{x}+{y}')

            def _pick_date(self, entry_widget):
                class DatePicker(tk.Toplevel):
                    def __init__(self, parent, callback=None, initial_date=None):
                        super().__init__(parent)
                        self.transient(parent)
                        self.grab_set()
                        self.callback = callback
                        self.title("Pick Date")
                        self.resizable(False, False)

                        today = datetime.now().date()
                        if initial_date:
                            try:
                                dt = datetime.strptime(initial_date, '%Y-%m-%d').date()
                            except Exception:
                                dt = today
                        else:
                            dt = today

                        self.year = dt.year
                        self.month = dt.month

                        header = ttk.Frame(self)
                        header.pack(fill=tk.X, padx=8, pady=6)
                        ttk.Button(header, text="◀", width=3, command=self._prev_month).pack(side=tk.LEFT)
                        self.title_lbl = ttk.Label(header, text="", anchor=tk.CENTER)
                        self.title_lbl.pack(side=tk.LEFT, expand=True)
                        ttk.Button(header, text="▶", width=3, command=self._next_month).pack(side=tk.RIGHT)

                        self.cal_frame = ttk.Frame(self)
                        self.cal_frame.pack(padx=8, pady=(0,8))
                        self._draw_calendar()

                    def _draw_calendar(self):
                        for child in self.cal_frame.winfo_children():
                            child.destroy()
                        self.title_lbl.config(text=f"{calendar.month_name[self.month]} {self.year}")
                        wdays = ['Mo','Tu','We','Th','Fr','Sa','Su']
                        for c, wd in enumerate(wdays):
                            ttk.Label(self.cal_frame, text=wd, width=3, anchor='center').grid(row=0, column=c)
                        m = calendar.monthcalendar(self.year, self.month)
                        for r, week in enumerate(m, start=1):
                            for c, day in enumerate(week):
                                if day == 0:
                                    ttk.Label(self.cal_frame, text='', width=3).grid(row=r, column=c, padx=1, pady=1)
                                else:
                                    b = ttk.Button(self.cal_frame, text=str(day), width=3, command=lambda d=day: self._select_day(d))
                                    b.grid(row=r, column=c, padx=1, pady=1)

                    def _prev_month(self):
                        self.month -= 1
                        if self.month < 1:
                            self.month = 12
                            self.year -= 1
                        self._draw_calendar()

                    def _next_month(self):
                        self.month += 1
                        if self.month > 12:
                            self.month = 1
                            self.year += 1
                        self._draw_calendar()

                    def _select_day(self, day):
                        try:
                            d = datetime(self.year, self.month, day).strftime('%Y-%m-%d')
                            if callable(self.callback):
                                self.callback(d)
                        except Exception:
                            pass
                        finally:
                            try:
                                self.grab_release()
                            except Exception:
                                pass
                            self.destroy()

                cur = entry_widget.get().strip()
                def _on_date(d):
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, d)
                dp = DatePicker(self, callback=_on_date, initial_date=cur)
                self.wait_window(dp)
                
            def on_ok(self):
                start_date = self.start_entry.get()
                end_date = self.end_entry.get()
                # Auto-compute end date if omitted (last day of start month)
                if start_date and not end_date:
                    try:
                        s = datetime.strptime(start_date, '%Y-%m-%d')
                        # move to first day of next month then step back one day
                        if s.month == 12:
                            nxt = datetime(s.year + 1, 1, 1)
                        else:
                            nxt = datetime(s.year, s.month + 1, 1)
                        end_date = (nxt - timedelta(days=1)).strftime('%Y-%m-%d')
                        self.end_entry.delete(0, tk.END)
                        self.end_entry.insert(0, end_date)
                    except Exception:
                        pass
                # Basic validation
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    if start >= end:
                        messagebox.showerror("Error", "End date must be after start date")
                        return
                        
                    self.result = (start_date, end_date)
                    self.destroy()
                except ValueError:
                    messagebox.showerror("Error", "Please enter dates in YYYY-MM-DD format")
            
            def on_cancel(self):
                self.destroy()
        
        # Show the dialog and process result
        dialog = PeriodDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
            start_date, end_date = dialog.result
            try:
                name = start_date[:7]
                try:
                    pid = self.engine.create_period(name=name, start_date=start_date, end_date=end_date, make_current=True)
                    self.current_period_id = pid
                    messagebox.showinfo("Success", "New accounting period created successfully")
                    # Refresh period list, select the new period, and load views immediately
                    self._load_periods()
                    if hasattr(self, 'period_combo'):
                        self.period_var.set(name)
                        try:
                            self.period_combo.set(name)
                        except Exception:
                            pass
                    self._on_period_change()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to create period: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create period: {str(e)}")

    def _load_cycle_status(self):
        try:
            if not hasattr(self, 'cycle_tree'):
                return
            if not self.engine.current_period_id:
                self.engine.refresh_current_period()
            rows = self.engine.get_cycle_status()
            for item in self.cycle_tree.get_children():
                self.cycle_tree.delete(item)
            for r in rows:
                vals = (r['step'], r['step_name'], r['status'], r['note'] if 'note' in r else '', r['updated_at'])
                tag = r['status']
                self.cycle_tree.insert('', 'end', values=vals, tags=(tag,))
            try:
                self.cycle_tree.tag_configure('completed', background=self.palette.get('tab_selected_bg', '#e0ecff'))
                self.cycle_tree.tag_configure('in_progress', background=self.palette.get('table_stripe', '#eef2ff'))
                self.cycle_tree.tag_configure('pending', background=self.palette.get('surface_bg', '#ffffff'))
            except Exception:
                pass
            pass
        except Exception as e:
            print(f"Error loading cycle status: {e}")

    def _refresh_cycle_and_views(self) -> None:
        try:
            self.engine.refresh_current_period()
        except Exception:
            pass
        try:
            self._load_cycle_status()
        except Exception:
            pass
        try:
            self._load_all_views()
        except Exception:
            pass

    def _snapshot_txn_form(self) -> Dict[str, str]:
        snap: Dict[str, str] = {}
        try:
            if hasattr(self, 'txn_date'):
                snap['date'] = self.txn_date.get().strip()
            if hasattr(self, 'txn_desc'):
                snap['desc'] = self.txn_desc.get().strip()
            if hasattr(self, 'debit_acct'):
                snap['debit_acct'] = self.debit_acct.get().strip()
            if hasattr(self, 'credit_acct'):
                snap['credit_acct'] = self.credit_acct.get().strip()
            if hasattr(self, 'debit_amt'):
                snap['debit_amt'] = self.debit_amt.get().strip()
            if hasattr(self, 'credit_amt'):
                snap['credit_amt'] = self.credit_amt.get().strip()
            if hasattr(self, 'txn_doc_ref'):
                snap['doc_ref'] = self.txn_doc_ref.get().strip()
            if hasattr(self, 'txn_external_ref'):
                snap['ext_ref'] = self.txn_external_ref.get().strip()
            if hasattr(self, 'txn_source_type'):
                snap['source_type'] = self.txn_source_type.get().strip()
            if hasattr(self, 'txn_memo'):
                snap['memo'] = self.txn_memo.get('1.0', tk.END).strip()
            if hasattr(self, 'txn_reverse_date'):
                snap['reverse_on'] = self.txn_reverse_date.get().strip()
        except Exception:
            pass
        return snap

    def _apply_txn_form(self, snap: Dict[str, str]) -> None:
        try:
            if 'date' in snap and hasattr(self, 'txn_date'):
                self.txn_date.delete(0, tk.END); self.txn_date.insert(0, snap.get('date', ''))
            if 'desc' in snap and hasattr(self, 'txn_desc'):
                self.txn_desc.delete(0, tk.END); self.txn_desc.insert(0, snap.get('desc', ''))
            if 'debit_acct' in snap and hasattr(self, 'debit_acct'):
                self.debit_acct.set(snap.get('debit_acct', ''))
            if 'credit_acct' in snap and hasattr(self, 'credit_acct'):
                self.credit_acct.set(snap.get('credit_acct', ''))
            if 'debit_amt' in snap and hasattr(self, 'debit_amt'):
                self.debit_amt.delete(0, tk.END); self.debit_amt.insert(0, snap.get('debit_amt', ''))
            if 'credit_amt' in snap and hasattr(self, 'credit_amt'):
                self.credit_amt.delete(0, tk.END); self.credit_amt.insert(0, snap.get('credit_amt', ''))
            if 'doc_ref' in snap and hasattr(self, 'txn_doc_ref'):
                self.txn_doc_ref.delete(0, tk.END); self.txn_doc_ref.insert(0, snap.get('doc_ref', ''))
            if 'ext_ref' in snap and hasattr(self, 'txn_external_ref'):
                self.txn_external_ref.delete(0, tk.END); self.txn_external_ref.insert(0, snap.get('ext_ref', ''))
            if 'source_type' in snap and hasattr(self, 'txn_source_type'):
                self.txn_source_type.set(snap.get('source_type', ''))
            if 'memo' in snap and hasattr(self, 'txn_memo'):
                self.txn_memo.delete('1.0', tk.END); self.txn_memo.insert('1.0', snap.get('memo', ''))
            if 'reverse_on' in snap and hasattr(self, 'txn_reverse_date'):
                self.txn_reverse_date.delete(0, tk.END); self.txn_reverse_date.insert(0, snap.get('reverse_on', ''))
        except Exception:
            pass

    def _prefill_txn_from_last_entry(self) -> None:
        try:
            pid = int(self.current_period_id or 0)
            if not pid:
                return
            row = self.engine.conn.execute(
                "SELECT id, date, description FROM journal_entries WHERE period_id=? ORDER BY id DESC LIMIT 1",
                (pid,)
            ).fetchone()
            if not row:
                return
            try:
                if hasattr(self, 'txn_date'):
                    self.txn_date.delete(0, tk.END); self.txn_date.insert(0, row['date'])
                if hasattr(self, 'txn_desc'):
                    self.txn_desc.delete(0, tk.END); self.txn_desc.insert(0, row['description'] or '')
            except Exception:
                pass
            lines = self.engine.conn.execute(
                """
                SELECT jl.debit, jl.credit, a.code, a.name
                FROM journal_lines jl
                JOIN accounts a ON a.id = jl.account_id
                WHERE jl.entry_id=?
                ORDER BY jl.id
                """,
                (int(row['id']),)
            ).fetchall()
            debit_line = next((l for l in lines if (l['debit'] or 0) > 0), None)
            credit_line = next((l for l in lines if (l['credit'] or 0) > 0), None)
            if debit_line and hasattr(self, 'debit_acct') and hasattr(self, 'debit_amt'):
                self.debit_acct.set(f"{debit_line['code']} - {debit_line['name']}")
                self.debit_amt.delete(0, tk.END); self.debit_amt.insert(0, f"{float(debit_line['debit']):.2f}")
            if credit_line and hasattr(self, 'credit_acct') and hasattr(self, 'credit_amt'):
                self.credit_acct.set(f"{credit_line['code']} - {credit_line['name']}")
                self.credit_amt.delete(0, tk.END); self.credit_amt.insert(0, f"{float(credit_line['credit']):.2f}")
        except Exception:
            pass

    def _render_cycle_list(self, rows: List[sqlite3.Row]) -> None:
        return

    def _build_ui(self) -> None:
        # Main container with responsive layout
        self.main_frame = ttk.Frame(self, style="Techfix.App.TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        container = ttk.Frame(self.main_frame, style="Techfix.App.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        # Sidebar (left) + content (right) layout for modern look
        sidebar = ttk.Frame(container, style="Techfix.Surface.TFrame", width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 6), pady=12)
        sidebar.pack_propagate(False)

        right_wrap = ttk.Frame(container, style="Techfix.App.TFrame")
        right_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 12), pady=12)

        # Header goes in right content area
        header = tk.Frame(right_wrap, bg=self.palette["accent_color"]) 
        header.pack(fill=tk.X, padx=0, pady=(0, 8))
        self.header_frame = header
        tk.Label(header, text="TechFix Solutions", bg=self.palette["accent_color"], fg="#ffffff", font="{Segoe UI Semibold} 14").pack(side=tk.LEFT, padx=18, pady=12)
        tk.Label(header, text="Integrated accounting workspace", bg=self.palette["accent_color"], fg=self.palette.get("subtitle_fg", "#dbeafe"), font=FONT_BASE).pack(side=tk.LEFT, padx=12, pady=12)

        toolbar = ttk.Frame(right_wrap, style="Techfix.App.TFrame")
        toolbar.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.toolbar_frame = toolbar

        ttk.Label(toolbar, text="Period", style="Techfix.AppBar.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        self.period_var = tk.StringVar()
        self.period_combo = ttk.Combobox(
            toolbar,
            textvariable=self.period_var,
            state="readonly",
            width=14,
            style="Techfix.TCombobox",
        )
        self.period_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.period_combo.bind("<<ComboboxSelected>>", self._on_period_change)

        ttk.Button(
            toolbar,
            text="New Period",
            command=self._prompt_new_period,
            style="Techfix.TButton",
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Button(
            toolbar,
            text="Refresh Cycle",
            command=self._refresh_cycle_and_views,
            style="Techfix.TButton",
        ).pack(side=tk.LEFT, padx=(0, 12))


        # Theme toggle buttons
        theme_frame = ttk.Frame(toolbar, style="Techfix.App.TFrame")
        theme_frame.pack(side=tk.RIGHT, padx=(0, 12))
        
        self.light_btn = ttk.Button(
            theme_frame,
            text="Light",
            command=lambda: self._apply_theme("Light"),
            style="Techfix.Theme.TButton",
            width=8
        )
        self.light_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        self.dark_btn = ttk.Button(
            theme_frame,
            text="Dark",
            command=lambda: self._apply_theme("Dark"),
            style="Techfix.Theme.TButton",
            width=8
        )
        self.dark_btn.pack(side=tk.LEFT)

        cycle_frame = ttk.Labelframe(right_wrap, text="Accounting Cycle Status", style="Techfix.TLabelframe")
        cycle_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.cycle_frame = cycle_frame

        cycle_top = ttk.Frame(cycle_frame, style="Techfix.Surface.TFrame")
        cycle_top.pack(fill=tk.X, padx=4, pady=(4, 0))
        ttk.Label(cycle_top, text="Track progress through the 10-step cycle.", style="Techfix.TLabel").pack(side=tk.LEFT)

        actions = ttk.Frame(cycle_frame, style="Techfix.Surface.TFrame")
        actions.pack(fill=tk.X, padx=4, pady=(4, 4))

        ttk.Button(
            actions,
            text="Mark Selected Completed",
            command=lambda: self._update_cycle_step_status("completed"),
            style="Techfix.TButton",
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            actions,
            text="Mark Selected In Progress",
            command=lambda: self._update_cycle_step_status("in_progress"),
            style="Techfix.TButton",
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            actions,
            text="Reset to Pending",
            command=lambda: self._update_cycle_step_status("pending"),
            style="Techfix.TButton",
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            actions,
            text="Reset All to Pending",
            command=self._reset_all_cycle_to_pending,
            style="Techfix.TButton",
        ).pack(side=tk.LEFT, padx=(0, 8))

        cols = ("step", "name", "status", "note", "updated")
        self.cycle_tree = ttk.Treeview(
            cycle_frame,
            columns=cols,
            show="headings",
            style="Techfix.Treeview",
            selectmode="browse",
            height=6,
        )
        self.cycle_tree_scroll = ttk.Scrollbar(cycle_frame, orient=tk.VERTICAL, command=self.cycle_tree.yview)
        self.cycle_tree.configure(yscrollcommand=self.cycle_tree_scroll.set)
        for c in cols:
            width = 80 if c == "step" else 140
            if c == "updated":
                width = 160
            self.cycle_tree.heading(c, text=c.title(), anchor="w")
            self.cycle_tree.column(c, width=width if c != "note" else 260, stretch=(c == "note"))
        self.cycle_tree.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0), pady=(0, 6))
        self.cycle_tree_scroll.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4), pady=(0, 6))

    

        notebook_wrap = ttk.Frame(right_wrap, style="Techfix.App.TFrame")
        notebook_wrap.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # Create a single content area and individual tab frames (we'll show/hide them)
        self.content_area = ttk.Frame(notebook_wrap, style="Techfix.App.TFrame")
        self.content_area.pack(fill=tk.BOTH, expand=True)

        self.tab_txn = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")
        self.tab_journal = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")
        self.tab_ledger = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")
        self.tab_trial = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")
        self.tab_adjust = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")
        self.tab_fs = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")
        self.tab_closing = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")
        self.tab_postclosing = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")
        self.tab_export = ttk.Frame(self.content_area, style="Techfix.Surface.TFrame")

        self._build_transactions_tab()
        self._build_journal_tab()
        self._build_ledger_tab()
        self._build_trial_tab()
        self._build_adjust_tab()
        self._build_fs_tab()
        self._build_closing_tab()
        self._build_postclosing_tab()
        self._build_export_tab()

        # Build simple sidebar navigation (shows/hides content frames)
        # Add a profile/header area inside the sidebar
        profile = ttk.Frame(sidebar, style="Techfix.Surface.TFrame")
        profile.pack(fill=tk.X, pady=(6, 12), padx=6)
        self.sidebar_brand_canvas = tk.Canvas(profile, height=30, highlightthickness=0, bd=0, bg=self.palette.get('surface_bg'))
        self.sidebar_brand_canvas.pack(fill=tk.X, padx=6, pady=6)
        try:
            self.sidebar_brand_canvas.bind('<Configure>', lambda e: self._draw_sidebar_brand())
        except Exception:
            pass
        try:
            self._draw_sidebar_brand()
        except Exception:
            pass

        # Factory to create sidebar nav rows (indicator + button)
        def make_nav(text: str, index: int, emoji: str = ""):
            if not hasattr(self, '_nav_buttons'):
                self._nav_buttons = []

            row = ttk.Frame(sidebar, style="Techfix.Surface.TFrame")
            row.pack(fill=tk.X, pady=4, padx=6)

            # Left accent indicator (thin bar)
            indicator = tk.Frame(row, width=6, bg=self.palette["surface_bg"], highlightthickness=0, bd=0, relief=tk.FLAT)
            indicator.pack(side=tk.LEFT, fill=tk.Y)

            # Button expands to fill remaining space
            btn = ttk.Button(row, text=f"{emoji}  {text}", style="Techfix.Nav.TButton", command=lambda i=index: self._nav_to(i))
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Hover effects: change indicator on enter/leave when not selected
            def on_enter(e, ind=indicator):
                try:
                    ind.configure(bg=self.palette.get('tab_active_bg'))
                except Exception:
                    pass

            def on_leave(e, ind=indicator, b=btn, idx=index):
                try:
                    # keep selected indicator if currently selected
                    if getattr(self, '_current_nav_index', None) == idx:
                        ind.configure(bg=self.palette.get('accent_color'))
                    else:
                        ind.configure(bg=self.palette.get('surface_bg'))
                except Exception:
                    pass

            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)

            self._nav_buttons.append((indicator, btn))
            return (indicator, btn)

        # Add navigation buttons (icons via emoji for simplicity)
        make_nav("Transactions", 0, "🧾")
        make_nav("Journal", 1, "📓")
        make_nav("Ledger", 2, "📚")
        make_nav("Trial Balance", 3, "🧮")
        make_nav("Adjustments", 4, "⚙️")
        make_nav("Fin. Statements", 5, "📊")
        make_nav("Closing", 6, "🔒")
        make_nav("Post-Closing", 7, "📈")
        make_nav("Export", 8, "⬇️")

        # Keep an ordered list of the content frames to show/hide
        self._tab_frames = [
            self.tab_txn,
            self.tab_journal,
            self.tab_ledger,
            self.tab_trial,
            self.tab_adjust,
            self.tab_fs,
            self.tab_closing,
            self.tab_postclosing,
            self.tab_export,
        ]

        exit_wrap = ttk.Frame(sidebar, style="Techfix.Surface.TFrame")
        exit_wrap.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=(12, 6))
        ttk.Button(exit_wrap, text="Exit", command=self._on_close, style="Techfix.Danger.TButton").pack(fill=tk.X)

    def _build_menubar(self) -> None:
        self.menubar = tk.Menu(self)
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="Exit", command=self._on_close)
        self.menubar.add_cascade(label="File", menu=self.file_menu)

        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.view_menu.add_command(label="Light Theme", command=lambda: self._apply_theme("Light"))
        self.view_menu.add_command(label="Dark Theme", command=lambda: self._apply_theme("Dark"))
        self.view_menu.add_separator()
        self.view_menu.add_command(label="Toggle Fullscreen", command=lambda: self.attributes('-fullscreen', not self.attributes('-fullscreen')))
        self.menubar.add_cascade(label="View", menu=self.view_menu)

        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About TechFix", "TechFix Accounting App"))
        self.menubar.add_cascade(label="Help", menu=self.help_menu)

        self.config(menu=self.menubar)
        self._style_menus()

    def _update_cycle_step_status(self, status: str) -> None:
        try:
            if not hasattr(self, 'cycle_tree'):
                return
            sel = self.cycle_tree.selection()
            if not sel:
                return
            item = sel[0]
            vals = self.cycle_tree.item(item, 'values')
            step = int(vals[0])
            note = None
            try:
                note = simpledialog.askstring("Update Step", "Note", parent=self) or None
            except Exception:
                note = None
            self.engine.set_cycle_step_status(step, status, note)
            self._load_cycle_status()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update cycle step: {e}")

    def _nav_to(self, index: int) -> None:
        """Navigate to notebook tab by index if possible."""
        try:
            # Hide all frames
            if not hasattr(self, '_tab_frames'):
                return
            for f in getattr(self, '_tab_frames'):
                try:
                    f.pack_forget()
                except Exception:
                    pass

            # Bound index
            if index < 0:
                index = 0
            if index >= len(self._tab_frames):
                index = 0

            sel = self._tab_frames[index]
            try:
                cur = getattr(self, '_current_nav_index', None)
                direction = 'right'
                try:
                    if isinstance(cur, int) and index < cur:
                        direction = 'left'
                except Exception:
                    pass
                self._animate_swipe_to(sel, direction=direction)
            except Exception:
                try:
                    sel.pack(fill=tk.BOTH, expand=True)
                except Exception:
                    pass

            # Update nav button visuals (indicator and selected style)
            try:
                self._current_nav_index = index
                for idx, (ind, btn) in enumerate(getattr(self, '_nav_buttons', ())):
                    if idx == index:
                        try:
                            ind.configure(bg=self.palette.get('accent_color'))
                        except Exception:
                            pass
                        try:
                            btn.configure(style='Techfix.Nav.Selected.TButton')
                        except Exception:
                            pass
                    else:
                        try:
                            ind.configure(bg=self.palette.get('surface_bg'))
                        except Exception:
                            pass
                        try:
                            btn.configure(style='Techfix.Nav.TButton')
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    def _post_to_ledger_action(self) -> None:
        try:
            self.engine.set_cycle_step_status(3, "completed", "Ledger posted")
            self._load_cycle_status()
            messagebox.showinfo("Posted", "Ledger posting marked completed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to post to ledger: {e}")

    def _reset_all_cycle_to_pending(self) -> None:
        """Reset all 10 accounting cycle steps to 'pending' for the active period."""
        try:
            if not self.engine.current_period_id:
                messagebox.showwarning("No Period", "No active accounting period selected.")
                return
            if not messagebox.askyesno("Confirm Reset", "Reset all accounting cycle steps to 'pending' for the current period?"):
                return
            pid = self.engine.current_period_id
            conn = self.engine.conn
            # Use constant list length from db module when available
            try:
                total_steps = len(db.ACCOUNTING_CYCLE_STEPS)
            except Exception:
                total_steps = 10
            for s in range(1, total_steps + 1):
                db.set_cycle_step_status(pid, s, 'pending', note='Reset to pending (user)', conn=conn)
            self._load_cycle_status()
            messagebox.showinfo("Reset Complete", "All cycle steps have been reset to pending.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset cycle steps: {e}")

    def _browse_source_document(self):
        """Open a file dialog to select a source document."""
        filetypes = [
            ('All supported files', '*.pdf;*.jpg;*.jpeg;*.png;*.doc;*.docx;*.xls;*.xlsx'),
            ('PDF files', '*.pdf'),
            ('Image files', '*.jpg;*.jpeg;*.png'),
            ('Word documents', '*.doc;*.docx'),
            ('Excel files', '*.xls;*.xlsx'),
            ('All files', '*.*')
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Source Document",
            filetypes=filetypes,
            defaultextension=".pdf"
        )
        
        if filename:
            self.txn_attachment_path.set(filename)
            
    def _clear_transaction_form(self):
        """Reset all fields in the transaction form to their default values."""
        # Clear entry fields
        if hasattr(self, 'txn_date'):
            try:
                self.txn_date.delete(0, tk.END)
                self.txn_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
            except Exception:
                pass
        # Clear document/reference fields (some names changed over time)
        if hasattr(self, 'txn_doc_ref'):
            try:
                self.txn_doc_ref.delete(0, tk.END)
            except Exception:
                pass
        if hasattr(self, 'txn_external_ref'):
            try:
                self.txn_external_ref.delete(0, tk.END)
            except Exception:
                pass
        if hasattr(self, 'txn_desc'):
            try:
                self.txn_desc.delete(0, tk.END)
            except Exception:
                pass
        if hasattr(self, 'txn_memo'):
            try:
                self.txn_memo.delete('1.0', tk.END)
            except Exception:
                pass
        if hasattr(self, 'txn_attachment_path'):
            try:
                self.txn_attachment_path.set('')
            except Exception:
                pass
        if hasattr(self, 'txn_source_type'):
            try:
                self.txn_source_type.set('')
            except Exception:
                pass
        if hasattr(self, 'debit_acct'):
            try:
                self.debit_acct.set('')
            except Exception:
                pass
        if hasattr(self, 'credit_acct'):
            try:
                self.credit_acct.set('')
            except Exception:
                pass
        if hasattr(self, 'debit_amt'):
            try:
                self.debit_amt.delete(0, tk.END)
            except Exception:
                pass
        if hasattr(self, 'credit_amt'):
            try:
                self.credit_amt.delete(0, tk.END)
            except Exception:
                pass
        if hasattr(self, 'txn_reverse_date'):
            try:
                self.txn_reverse_date.delete(0, tk.END)
            except Exception:
                pass
        if hasattr(self, 'txn_is_adjust'):
            try:
                self.txn_is_adjust.set(0)
            except Exception:
                pass
        if hasattr(self, 'txn_schedule_reverse'):
            try:
                self.txn_schedule_reverse.set(0)
            except Exception:
                pass
            
        # Clear any journal entry lines if they exist
        if hasattr(self, 'journal_entries') and hasattr(self.journal_entries, 'delete'):
            self.journal_entries.delete(0, tk.END)
            
        # Reset the transaction ID if it exists
        if hasattr(self, 'current_transaction_id'):
            self.current_transaction_id = None
            
        # Set focus to the first field (txn_date Entry)
        if hasattr(self, 'txn_date'):
            try:
                self.txn_date.focus_set()
            except Exception:
                pass

    def _set_txn_date_today(self) -> None:
        """Set the transaction date field to today's date."""
        try:
            if hasattr(self, 'txn_date'):
                self.txn_date.delete(0, tk.END)
                self.txn_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        except Exception:
            pass

    def _pick_txn_date(self) -> None:
        """Open a small date picker dialog and set the txn_date when picked."""
        try:
            class DatePicker(tk.Toplevel):
                def __init__(self, parent, callback=None, initial_date=None):
                    super().__init__(parent)
                    self.transient(parent)
                    self.grab_set()
                    self.callback = callback
                    self.title("Pick Date")
                    self.resizable(False, False)

                    today = datetime.now().date()
                    if initial_date:
                        try:
                            dt = datetime.strptime(initial_date, '%Y-%m-%d').date()
                        except Exception:
                            dt = today
                    else:
                        dt = today

                    self.year = dt.year
                    self.month = dt.month

                    header = ttk.Frame(self)
                    header.pack(fill=tk.X, padx=8, pady=6)
                    ttk.Button(header, text="◀", width=3, command=self._prev_month).pack(side=tk.LEFT)
                    self.title_lbl = ttk.Label(header, text="", anchor=tk.CENTER)
                    self.title_lbl.pack(side=tk.LEFT, expand=True)
                    ttk.Button(header, text="▶", width=3, command=self._next_month).pack(side=tk.RIGHT)

                    self.cal_frame = ttk.Frame(self)
                    self.cal_frame.pack(padx=8, pady=(0,8))

                    self._draw_calendar()

                def _draw_calendar(self):
                    for child in self.cal_frame.winfo_children():
                        child.destroy()
                    self.title_lbl.config(text=f"{calendar.month_name[self.month]} {self.year}")
                    wdays = ['Mo','Tu','We','Th','Fr','Sa','Su']
                    for c, wd in enumerate(wdays):
                        ttk.Label(self.cal_frame, text=wd, width=3, anchor='center').grid(row=0, column=c)
                    m = calendar.monthcalendar(self.year, self.month)
                    for r, week in enumerate(m, start=1):
                        for c, day in enumerate(week):
                            if day == 0:
                                ttk.Label(self.cal_frame, text='', width=3).grid(row=r, column=c, padx=1, pady=1)
                            else:
                                b = ttk.Button(self.cal_frame, text=str(day), width=3, command=lambda d=day: self._select_day(d))
                                b.grid(row=r, column=c, padx=1, pady=1)

                def _prev_month(self):
                    self.month -= 1
                    if self.month < 1:
                        self.month = 12
                        self.year -= 1
                    self._draw_calendar()

                def _next_month(self):
                    self.month += 1
                    if self.month > 12:
                        self.month = 1
                        self.year += 1
                    self._draw_calendar()

                def _select_day(self, day):
                    try:
                        d = datetime(self.year, self.month, day).strftime('%Y-%m-%d')
                        if callable(self.callback):
                            self.callback(d)
                    except Exception:
                        pass
                    finally:
                        try:
                            self.grab_release()
                        except Exception:
                            pass
                        self.destroy()

            def _on_date_chosen(d):
                try:
                    if hasattr(self, 'txn_date'):
                        self.txn_date.delete(0, tk.END)
                        self.txn_date.insert(0, d)
                except Exception:
                    pass

            # open the picker
            cur = None
            try:
                cur = self.txn_date.get().strip()
            except Exception:
                cur = None
            dp = DatePicker(self, callback=_on_date_chosen, initial_date=cur)
            self.wait_window(dp)
        except Exception:
            pass

    def _build_scrollable_tab(self, parent: ttk.Frame) -> ttk.Frame:
        """Create a scrollable frame within a tab"""
        # Create a container frame that will hold the canvas and scrollbar
        container = ttk.Frame(parent, style="Techfix.Surface.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        # Create canvas with scrollbar
        canvas = tk.Canvas(container, bd=0, highlightthickness=0, bg=self.palette["surface_bg"])
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        # Create a frame inside the canvas that will hold our content
        scrollable_frame = ttk.Frame(canvas, style="Techfix.Surface.TFrame")

        # Configure the canvas
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Create window in canvas for the scrollable frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags=("scrollable_frame",))

        # Configure the scroll region when the frame changes size
        def _on_frame_configure(event):
            # Update the scroll region to encompass the inner frame
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make sure the frame fills the canvas width
            canvas.itemconfig("scrollable_frame", width=event.width)

        def _on_mousewheel(event):
            # Handle mousewheel scrolling
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        # Bind the configure event to handle resizing
        scrollable_frame.bind("<Configure>", _on_frame_configure)

        # Bind mousewheel events to the canvas and all its children
        def bind_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units") if canvas.winfo_containing(e.x_root, e.y_root) else None)
            widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units") if canvas.winfo_containing(e.x_root, e.y_root) else None)

            for child in widget.winfo_children():
                bind_mousewheel(child)

        bind_mousewheel(scrollable_frame)

        # Bind mousewheel for Windows
        canvas.bind("<MouseWheel>", _on_mousewheel)

        # Bind mousewheel for Linux (button 4/5)
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units") if canvas.winfo_containing(e.x_root, e.y_root) in (canvas, scrollbar) else None)
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units") if canvas.winfo_containing(e.x_root, e.y_root) in (canvas, scrollbar) else None)

        # Store canvas for theme updates
        if not hasattr(self, '_scroll_canvases'):
            self._scroll_canvases = []
        self._scroll_canvases.append(canvas)

        # Make sure entry widgets don't capture scroll events
        def _on_entry_mousewheel(event):
            return "break"

        # Apply to all existing entry widgets
        for child in scrollable_frame.winfo_children():
            if isinstance(child, (ttk.Entry, ttk.Combobox, tk.Text, ttk.Spinbox)):
                child.bind("<MouseWheel>", _on_entry_mousewheel)

        return scrollable_frame

    def _build_transactions_tab(self) -> None:
        frame = self.tab_txn
        
        # Create a main container with proper expansion
        main_container = ttk.Frame(frame, style="Techfix.Surface.TFrame")
        main_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)
        
        # Form frame with fixed height
        form = ttk.LabelFrame(main_container, text="New Transaction", style="Techfix.TLabelframe")
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        # Column weight strategy: labels (0,2,4) stay compact, inputs (1,3) expand
        form.columnconfigure(0, weight=0)
        form.columnconfigure(1, weight=3)
        form.columnconfigure(2, weight=0)
        form.columnconfigure(3, weight=4)
        form.columnconfigure(4, weight=0)
        
        # Configure form grid row weights
        for i in range(8):  # 0-7 rows
            form.rowconfigure(i, weight=0)
        form.rowconfigure(5, weight=1)  # Memo row gets extra space
        
        # Date and Description row with reduced padding
        ttk.Label(form, text="Date: (YYYY-MM-DD)").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        # Date entry with picker and Today button
        date_frame = ttk.Frame(form, style="Techfix.Surface.TFrame")
        date_frame.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        self.txn_date = ttk.Entry(date_frame, style="Techfix.TEntry", width=12)
        self.txn_date.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(date_frame, text="📅", width=3, command=lambda: self._pick_txn_date(), style="Techfix.TButton").pack(side=tk.LEFT, padx=(2,0))
        ttk.Button(date_frame, text="Today", width=6, command=lambda: self._set_txn_date_today(), style="Techfix.TButton").pack(side=tk.LEFT, padx=(4,0))

        ttk.Label(form, text="Description:").grid(row=0, column=2, sticky="w", padx=2, pady=2)
        self.txn_desc = ttk.Entry(form, style="Techfix.TEntry")
        self.txn_desc.grid(row=0, column=3, columnspan=2, sticky="we", padx=2, pady=2)

        accounts = db.get_accounts()
        account_names = [f"{a['code']} - {a['name']}" for a in accounts]
        self.account_id_by_display = {f"{a['code']} - {a['name']}": a["id"] for a in accounts}

        # Debit line with optimized spacing
        ttk.Label(form, text="Debit Account:").grid(row=1, column=0, sticky="w", padx=2, pady=1)
        self.debit_acct = ttk.Combobox(form, values=account_names, style="Techfix.TCombobox")
        self.debit_acct.grid(row=1, column=1, sticky="we", padx=2, pady=1)
        
        ttk.Label(form, text="Amount:").grid(row=1, column=2, sticky="e", padx=2, pady=1)
        self.debit_amt = ttk.Entry(form, style="Techfix.TEntry", width=15)
        self.debit_amt.grid(row=1, column=3, sticky="w", padx=2, pady=1)

        # Credit line with optimized spacing
        ttk.Label(form, text="Credit Account:").grid(row=2, column=0, sticky="w", padx=2, pady=1)
        self.credit_acct = ttk.Combobox(form, values=account_names, style="Techfix.TCombobox")
        self.credit_acct.grid(row=2, column=1, sticky="we", padx=2, pady=1)
        
        ttk.Label(form, text="Amount:").grid(row=2, column=2, sticky="e", padx=2, pady=1)
        self.credit_amt = ttk.Entry(form, style="Techfix.TEntry", width=15)
        self.credit_amt.grid(row=2, column=3, sticky="w", padx=2, pady=1)

        # Document references row with optimized spacing
        ttk.Label(form, text="Doc #:").grid(row=3, column=0, sticky="w", padx=2, pady=1)
        self.txn_doc_ref = ttk.Entry(form, style="Techfix.TEntry")
        self.txn_doc_ref.grid(row=3, column=1, sticky="we", padx=2, pady=1)

        ttk.Label(form, text="External Ref:").grid(row=3, column=2, sticky="e", padx=2, pady=1)
        self.txn_external_ref = ttk.Entry(form, style="Techfix.TEntry")
        self.txn_external_ref.grid(row=3, column=3, sticky="we", padx=2, pady=1)

        # Source type and attachment row with optimized layout
        ttk.Label(form, text="Source:").grid(row=4, column=0, sticky="w", padx=2, pady=1)
        self.txn_source_type = ttk.Combobox(
            form,
            values=["", "Invoice", "Receipt", "Bank", "Adjust", "Payroll", "Other"],
            state="readonly",
            style="Techfix.TCombobox",
            width=15
        )
        self.txn_source_type.set("")
        self.txn_source_type.grid(row=4, column=1, sticky="we", padx=2, pady=1)

        # Attachment row with better button visibility
        ttk.Label(form, text="Document:").grid(row=4, column=2, sticky="e", padx=2, pady=1)
        self.txn_attachment_path = tk.StringVar(value="")
        
        # Create a frame for the entry and button
        attach_frame = ttk.Frame(form, style="Techfix.Surface.TFrame")
        attach_frame.grid(row=4, column=3, sticky="we", padx=2, pady=1)
        
        # Configure the frame to handle resizing
        attach_frame.columnconfigure(0, weight=1)
        
        # Entry field for document path
        self.txn_attachment_display = ttk.Entry(
            attach_frame, 
            textvariable=self.txn_attachment_path, 
            state="readonly", 
            style="Techfix.TEntry"
        )
        self.txn_attachment_display.grid(row=0, column=0, sticky="we", padx=(0,4))
        
        # Browse button with better visibility
        browse_btn = ttk.Button(
            attach_frame, 
            text="Browse...", 
            command=self._browse_source_document, 
            style="Techfix.TButton",
            width=8
        )
        browse_btn.grid(row=0, column=1, sticky="e", padx=(4, 0))

        # Compact memo field
        ttk.Label(form, text="Memo:").grid(row=5, column=0, sticky="nw", padx=2, pady=2)
        
        # Create a frame to hold the text widget and scrollbar
        memo_frame = ttk.Frame(form, style="Techfix.TFrame")
        memo_frame.grid(row=5, column=1, columnspan=4, sticky="nsew", padx=2, pady=2)
        
        # Configure grid weights for memo frame
        memo_frame.columnconfigure(0, weight=1)
        memo_frame.rowconfigure(0, weight=1)
        
        # Text widget with reduced height and padding
        self.txn_memo = tk.Text(
            memo_frame,
            height=3,
            bg=self.palette["surface_bg"],
            fg=self.palette["text_primary"],
            bd=1,
            relief=tk.SOLID,
            highlightthickness=1,
            highlightbackground=self.palette.get("entry_border", "#d8dee9"),
            highlightcolor=self.palette.get("accent_color", "#2563eb"),
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            padx=4,
            pady=2
        )
        self.txn_memo.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbar for memo field
        scrollbar = ttk.Scrollbar(
            memo_frame,
            orient=tk.VERTICAL,
            command=self.txn_memo.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.txn_memo.config(yscrollcommand=scrollbar.set)
        
        # Configure row weight for the memo row
        form.rowconfigure(5, weight=0)  # Don't let memo expand too much

        # Compact options frame
        options_frame = ttk.Frame(form, style="Techfix.Surface.TFrame")
        options_frame.grid(row=6, column=0, columnspan=5, sticky="we", padx=2, pady=2)
        
        # Configure options frame columns
        options_frame.columnconfigure(0, weight=1)
        
        # Left side options with minimal spacing
        options_container = ttk.Frame(options_frame, style="Techfix.Surface.TFrame")
        options_container.pack(fill=tk.X, expand=True)
        
        self.txn_is_adjust = tk.IntVar(value=0)
        ttk.Checkbutton(
            options_container, 
            text="Adjusting Entry", 
            variable=self.txn_is_adjust, 
            style="Techfix.TCheckbutton"
        ).pack(side=tk.LEFT, padx=(0, 12), pady=1)
        
        self.txn_schedule_reverse = tk.IntVar(value=0)
        ttk.Checkbutton(
            options_container,
            text="Schedule Reversal",
            variable=self.txn_schedule_reverse,
            style="Techfix.TCheckbutton",
        ).pack(side=tk.LEFT, padx=(0, 4), pady=1)
        
        ttk.Label(options_container, text="Date:").pack(side=tk.LEFT, padx=(0, 2), pady=1)
        self.txn_reverse_date = ttk.Entry(options_container, width=12, style="Techfix.TEntry")
        self.txn_reverse_date.pack(side=tk.LEFT, pady=1)

        # Action buttons - compact and aligned
        action_frame = ttk.Frame(form, style="Techfix.Surface.TFrame")
        action_frame.grid(row=7, column=0, columnspan=5, sticky="e", padx=2, pady=(4, 0))
        
        # Configure action frame columns
        action_frame.columnconfigure(0, weight=1)
        
        # Button container with consistent spacing
        btn_container = ttk.Frame(action_frame, style="Techfix.Surface.TFrame")
        btn_container.pack(anchor="e")
        
        # Common button style with fixed width
        button_style = {
            'style': 'Techfix.TButton',
            'width': 14,  # Slightly wider for better text fit
            'padding': (10, 4)  # More padding for better clickability
        }
        
        ttk.Button(
            btn_container,
            text="Clear Form",
            command=self._clear_transaction_form,
            **button_style
        ).pack(side=tk.RIGHT, padx=(8, 0), pady=2)
        
        ttk.Button(
            btn_container,
            text="Save Draft",
            command=lambda: self._record_transaction("draft"),
            **button_style
        ).pack(side=tk.RIGHT, padx=6, pady=2)
        
        ttk.Button(
            btn_container,
            text="Record & Post",
            command=lambda: self._record_transaction("posted"),
            **button_style
        ).pack(side=tk.RIGHT, pady=2)

        # --- Recent Transactions area (right pane) ---
        recent_wrap = ttk.Labelframe(main_container, text="Recent Transactions", style="Techfix.TLabelframe")
        recent_wrap.grid(row=0, column=1, sticky="nsew")
        recent_wrap.columnconfigure(0, weight=1)
        recent_wrap.rowconfigure(1, weight=1)
        controls = ttk.Frame(recent_wrap, style="Techfix.Surface.TFrame")
        controls.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(controls, text="Refresh", command=lambda: self._load_recent_transactions(), style="Techfix.TButton").pack(side=tk.LEFT)
        ttk.Button(controls, text="Delete Selected", command=self._delete_selected_transaction, style="Techfix.Danger.TButton").pack(side=tk.LEFT, padx=(6,0))
        tree_frame = ttk.Frame(recent_wrap, style="Techfix.Surface.TFrame")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        cols = ("date", "reference", "description", "debit", "credit", "account")
        self.txn_recent_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            style="Techfix.Treeview",
            selectmode="browse",
        )
        # Headings
        self.txn_recent_tree.heading("date", text="Date")
        self.txn_recent_tree.heading("reference", text="Ref")
        self.txn_recent_tree.heading("description", text="Description")
        self.txn_recent_tree.heading("debit", text="Debit")
        self.txn_recent_tree.heading("credit", text="Credit")
        self.txn_recent_tree.heading("account", text="Account")

        # Column sizing - description expands
        self.txn_recent_tree.column("date", width=100, anchor=tk.W, stretch=False)
        self.txn_recent_tree.column("reference", width=80, anchor=tk.W, stretch=False)
        self.txn_recent_tree.column("description", width=520, anchor=tk.W, stretch=True)
        self.txn_recent_tree.column("debit", width=100, anchor=tk.E, stretch=False)
        self.txn_recent_tree.column("credit", width=100, anchor=tk.E, stretch=False)
        self.txn_recent_tree.column("account", width=220, anchor=tk.W, stretch=False)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.txn_recent_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.txn_recent_tree.xview)
        self.txn_recent_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Layout
        self.txn_recent_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, columnspan=2, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Load initial recent transactions
        try:
            self._load_recent_transactions()
        except Exception:
            pass

    def _delete_selected_transaction(self) -> None:
        try:
            if not hasattr(self, 'txn_recent_tree'):
                return
            sel = self.txn_recent_tree.selection()
            if not sel:
                messagebox.showinfo("Delete", "Select a transaction to delete.")
                return
            item = sel[0]
            vals = self.txn_recent_tree.item(item, 'values')
            try:
                entry_id = int(vals[1]) if len(vals) > 1 and vals[1] else None
            except Exception:
                entry_id = None
            if not entry_id:
                messagebox.showerror("Delete", "Could not determine the selected transaction ID.")
                return
            if not messagebox.askyesno("Confirm Delete", f"Delete transaction #{entry_id}? This cannot be undone."):
                return
            conn = self.engine.conn
            try:
                conn.execute("DELETE FROM journal_entries WHERE id=?", (entry_id,))
                conn.commit()
            except Exception as e:
                messagebox.showerror("Delete Failed", f"Error deleting transaction: {e}")
                return
            try:
                self._load_recent_transactions()
            except Exception:
                pass
            try:
                self._load_journal_entries()
            except Exception:
                pass
        except Exception:
            pass


    def _build_adjust_tab(self) -> None:
        frame = self.tab_adjust

        content = ttk.Frame(frame, style="Techfix.Surface.TFrame")
        content.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        # Common Adjustments section
        f = ttk.Labelframe(content, text="Common Adjustments", style="Techfix.TLabelframe")
        f.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(2, 0))

        # Configure columns - make entry fields expand
        f.columnconfigure(0, weight=0)  # Labels
        f.columnconfigure(1, weight=3)  # Entry fields (3x weight)
        f.columnconfigure(2, weight=1)  # Buttons (1x weight)

        # Configure rows to be compact
        for i in range(4):
            f.rowconfigure(i, weight=0, pad=2)

        # Date input row - using grid for better control
        ttk.Label(f, text="Date:").grid(row=0, column=0, sticky="e", padx=2, pady=2)
        self.adjust_date = ttk.Entry(f, style="Techfix.TEntry")
        self.adjust_date.grid(row=0, column=1, sticky="we", padx=2, pady=2)
        btns = ttk.Frame(f, style="Techfix.Surface.TFrame")
        btns.grid(row=0, column=2, sticky="ew", padx=2, pady=2)
        ttk.Button(btns, text="📅", command=self._pick_adjust_date, style="Techfix.TButton", width=3).pack(side=tk.LEFT, padx=(0,4))
        ttk.Button(btns, text="Today", command=lambda: self._set_entry_today(self.adjust_date), style="Techfix.TButton").pack(side=tk.LEFT)

        # Adjustment controls in a grid
        row = 1

        # Row 1: Supplies
        ttk.Label(f, text="Supplies:").grid(row=row, column=0, sticky="e", padx=2, pady=2)
        self.sup_remaining = ttk.Entry(f, style="Techfix.TEntry")
        self.sup_remaining.grid(row=row, column=1, sticky="we", padx=2, pady=2)
        ttk.Button(f, text="Adjust", command=self._do_adjust_supplies,
                  style="Techfix.TButton").grid(row=row, column=2, padx=2, pady=2, sticky="ew")

        # Row 2: Prepaid Rent
        row += 1
        ttk.Label(f, text="Prepaid Rent:").grid(row=row, column=0, sticky="e", padx=2, pady=2)
        self.prepaid_amt = ttk.Entry(f, style="Techfix.TEntry")
        self.prepaid_amt.grid(row=row, column=1, sticky="we", padx=2, pady=2)
        ttk.Button(f, text="Amortize", command=self._do_amortize_prepaid,
                  style="Techfix.TButton").grid(row=row, column=2, padx=2, pady=2, sticky="ew")

        # Row 3: Depreciation
        row += 1
        ttk.Label(f, text="Depreciation:").grid(row=row, column=0, sticky="e", padx=2, pady=2)
        self.depr_amt = ttk.Entry(f, style="Techfix.TEntry")
        self.depr_amt.grid(row=row, column=1, sticky="we", padx=2, pady=2)
        ttk.Button(f, text="Calculate", command=self._do_depreciate,
                  style="Techfix.TButton").grid(row=row, column=2, padx=2, pady=2, sticky="ew")

        # Configure column weights for the labelframe
        f.columnconfigure(1, weight=1)  # Entry fields expand

        # Adjustment Requests section
        queue = ttk.Labelframe(content, text="Adjustment Requests & Approvals",
                              style="Techfix.TLabelframe")
        queue.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=(2, 0))

        # Input form frame
        queue_inputs = ttk.Frame(queue, style="Techfix.Surface.TFrame")
        queue_inputs.pack(fill=tk.X, padx=2, pady=2)

        # Description row
        desc_frame = ttk.Frame(queue_inputs, style="Techfix.Surface.TFrame")
        desc_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(desc_frame, text="Description:").pack(side=tk.LEFT, padx=(0, 4))
        self.adjust_desc = ttk.Entry(desc_frame, style="Techfix.TEntry")
        self.adjust_desc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Label(desc_frame, text="By:").pack(side=tk.LEFT, padx=(0, 4))
        self.adjust_requested_by = ttk.Entry(desc_frame, style="Techfix.TEntry", width=15)
        self.adjust_requested_by.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(desc_frame, text="Add Request", command=self._queue_adjustment_request,
                  style="Techfix.TButton").pack(side=tk.RIGHT)

        # Notes row
        notes_frame = ttk.Frame(queue_inputs, style="Techfix.Surface.TFrame")
        notes_frame.pack(fill=tk.X)
        ttk.Label(notes_frame, text="Notes:").pack(side=tk.LEFT, padx=(0, 4))
        self.adjust_notes = ttk.Entry(notes_frame, style="Techfix.TEntry")
        self.adjust_notes.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Treeview frame (use grid so scrollbars attach reliably)
        tree_frame = ttk.Frame(queue, style="Techfix.Surface.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Treeview for adjustments
        cols = ("id", "description", "requested_on", "status", "notes")
        self.adjust_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            style="Techfix.Treeview",
            height=15,
            selectmode="extended"
        )

        # Configure columns with better distribution and stretching
        col_config = {
            "id": {"width": 40, "minwidth": 40, "stretch": False, "anchor": "center"},
            "description": {"width": 300, "minwidth": 150, "stretch": True, "anchor": "w"},
            "requested_on": {"width": 150, "minwidth": 100, "stretch": False, "anchor": "center"},
            "status": {"width": 100, "minwidth": 80, "stretch": False, "anchor": "center"},
            "notes": {"width": 300, "minwidth": 150, "stretch": True, "anchor": "w"}
        }

        # Configure columns
        for c in cols:
            self.adjust_tree.heading(c, text=c.replace("_", " ").title(), anchor="center")
            self.adjust_tree.column(
                c,
                width=col_config[c]["width"],
                minwidth=col_config[c]["minwidth"],
                stretch=col_config[c]["stretch"],
                anchor=col_config[c]["anchor"]
            )

        # Add scrollbars and grid them so layout is stable
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.adjust_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.adjust_tree.xview)
        self.adjust_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # grid layout for tree + scrollbars
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.adjust_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, columnspan=2, sticky="ew")

        # Ensure mouse wheel scrolls the treeview
        try:
            self.adjust_tree.bind("<MouseWheel>", lambda e: self.adjust_tree.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        except Exception:
            pass

        # Action buttons frame
        btn_frame = ttk.Frame(queue, style="Techfix.Surface.TFrame")
        btn_frame.pack(fill=tk.X, padx=2, pady=2)

        # Add buttons with pack
        buttons = [
            ("Refresh", self._load_adjustments),
            ("Approve", lambda: self._mark_adjustment_status("approved")),
            ("Post", lambda: self._mark_adjustment_status("posted")),
            ("Draft", lambda: self._mark_adjustment_status("draft"))
        ]

        for text, cmd in buttons:
            btn = ttk.Button(btn_frame, text=text, command=cmd, style="Techfix.TButton")
            btn.pack(side=tk.LEFT, padx=2, pady=2, expand=True, fill=tk.X)

    # Adjustment action handlers
    def _do_adjust_supplies(self) -> None:
        """Create an adjusting journal entry to record supplies used."""
        amt_text = (self.sup_remaining.get() if hasattr(self, 'sup_remaining') else '').strip()
        if not amt_text:
            messagebox.showinfo("No Amount", "Please enter the supplies amount to adjust.")
            return
        try:
            amt = float(amt_text)
        except Exception:
            messagebox.showerror("Invalid Amount", "Please enter a numeric amount for supplies.")
            return

        # Find account ids
        supplies = db.get_account_by_name('Supplies')
        supplies_exp = db.get_account_by_name('Supplies Expense')
        if not supplies or not supplies_exp:
            messagebox.showerror("Missing Accounts", "Required accounts not found: Supplies / Supplies Expense")
            return

        try:
            date_str = (self.adjust_date.get().strip() if hasattr(self, 'adjust_date') else '') or datetime.utcnow().date().isoformat()
            entry_id = db.insert_journal_entry(
                date=date_str,
                description=f"Adjust supplies: used {amt:.2f}",
                lines=[(supplies_exp['id'], amt, 0.0), (supplies['id'], 0.0, amt)],
                is_adjusting=1,
                conn=self.engine.conn,
            )
            messagebox.showinfo("Adjusted", f"Created adjusting entry {entry_id} for supplies ({amt:.2f})")
            self._refresh_after_post()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create adjusting entry: {e}")

    def _do_amortize_prepaid(self) -> None:
        """Amortize prepaid rent into rent expense."""
        amt_text = (self.prepaid_amt.get() if hasattr(self, 'prepaid_amt') else '').strip()
        if not amt_text:
            messagebox.showinfo("No Amount", "Please enter the amount to amortize.")
            return
        try:
            amt = float(amt_text)
        except Exception:
            messagebox.showerror("Invalid Amount", "Please enter a numeric amount for amortization.")
            return

        prepaid = db.get_account_by_name('Prepaid Rent')
        rent_exp = db.get_account_by_name('Rent Expense')
        if not prepaid or not rent_exp:
            messagebox.showerror("Missing Accounts", "Required accounts not found: Prepaid Rent / Rent Expense")
            return

        try:
            date_str = (self.adjust_date.get().strip() if hasattr(self, 'adjust_date') else '') or datetime.utcnow().date().isoformat()
            entry_id = db.insert_journal_entry(
                date=date_str,
                description=f"Amortize prepaid rent: {amt:.2f}",
                lines=[(rent_exp['id'], amt, 0.0), (prepaid['id'], 0.0, amt)],
                is_adjusting=1,
                conn=self.engine.conn,
            )
            messagebox.showinfo("Amortized", f"Created amortization entry {entry_id} ({amt:.2f})")
            self._refresh_after_post()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create amortization entry: {e}")

    def _do_depreciate(self) -> None:
        """Record depreciation expense for equipment."""
        amt_text = (self.depr_amt.get() if hasattr(self, 'depr_amt') else '').strip()
        if not amt_text:
            messagebox.showinfo("No Amount", "Please enter the depreciation amount.")
            return
        try:
            amt = float(amt_text)
        except Exception:
            messagebox.showerror("Invalid Amount", "Please enter a numeric amount for depreciation.")
            return

        depr_exp = db.get_account_by_name('Depreciation Expense')
        acc_depr = db.get_account_by_name('Accumulated Depreciation - Equipment')
        if not depr_exp or not acc_depr:
            messagebox.showerror("Missing Accounts", "Required accounts not found: Depreciation Expense / Accumulated Depreciation - Equipment")
            return

        try:
            date_str = (self.adjust_date.get().strip() if hasattr(self, 'adjust_date') else '') or datetime.utcnow().date().isoformat()
            entry_id = db.insert_journal_entry(
                date=date_str,
                description=f"Record depreciation: {amt:.2f}",
                lines=[(depr_exp['id'], amt, 0.0), (acc_depr['id'], 0.0, amt)],
                is_adjusting=1,
                conn=self.engine.conn,
            )
            messagebox.showinfo("Depreciated", f"Created depreciation entry {entry_id} ({amt:.2f})")
            self._refresh_after_post()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create depreciation entry: {e}")

    def _pick_adjust_date(self) -> None:
        try:
            class DatePicker(tk.Toplevel):
                def __init__(self, parent, callback=None, initial_date=None):
                    super().__init__(parent)
                    self.transient(parent)
                    self.grab_set()
                    self.callback = callback
                    self.title("Pick Date")
                    self.resizable(False, False)

                    today = datetime.now().date()
                    if initial_date:
                        try:
                            dt = datetime.strptime(initial_date, '%Y-%m-%d').date()
                        except Exception:
                            dt = today
                    else:
                        dt = today

                    self.year = dt.year
                    self.month = dt.month

                    header = ttk.Frame(self)
                    header.pack(fill=tk.X, padx=8, pady=6)
                    ttk.Button(header, text="◀", width=3, command=self._prev_month).pack(side=tk.LEFT)
                    self.title_lbl = ttk.Label(header, text="", anchor=tk.CENTER)
                    self.title_lbl.pack(side=tk.LEFT, expand=True)
                    ttk.Button(header, text="▶", width=3, command=self._next_month).pack(side=tk.RIGHT)

                    self.cal_frame = ttk.Frame(self)
                    self.cal_frame.pack(padx=8, pady=(0,8))
                    self._draw_calendar()

                def _draw_calendar(self):
                    for child in self.cal_frame.winfo_children():
                        child.destroy()
                    self.title_lbl.config(text=f"{calendar.month_name[self.month]} {self.year}")
                    wdays = ['Mo','Tu','We','Th','Fr','Sa','Su']
                    for c, wd in enumerate(wdays):
                        ttk.Label(self.cal_frame, text=wd, width=3, anchor='center').grid(row=0, column=c)
                    m = calendar.monthcalendar(self.year, self.month)
                    for r, week in enumerate(m, start=1):
                        for c, day in enumerate(week):
                            if day == 0:
                                ttk.Label(self.cal_frame, text='', width=3).grid(row=r, column=c, padx=1, pady=1)
                            else:
                                b = ttk.Button(self.cal_frame, text=str(day), width=3, command=lambda d=day: self._select_day(d))
                                b.grid(row=r, column=c, padx=1, pady=1)

                def _prev_month(self):
                    self.month -= 1
                    if self.month < 1:
                        self.month = 12
                        self.year -= 1
                    self._draw_calendar()

                def _next_month(self):
                    self.month += 1
                    if self.month > 12:
                        self.month = 1
                        self.year += 1
                    self._draw_calendar()

                def _select_day(self, day):
                    try:
                        d = datetime(self.year, self.month, day).strftime('%Y-%m-%d')
                        if callable(self.callback):
                            self.callback(d)
                    except Exception:
                        pass
                    finally:
                        try:
                            self.grab_release()
                        except Exception:
                            pass
                        self.destroy()

            def _on_pick(d):
                try:
                    self.adjust_date.delete(0, tk.END)
                    self.adjust_date.insert(0, d)
                except Exception:
                    pass

            cur = None
            try:
                cur = self.adjust_date.get().strip()
            except Exception:
                cur = None
            dp = DatePicker(self, callback=_on_pick, initial_date=cur)
            self.wait_window(dp)
        except Exception:
            pass

    def _set_entry_today(self, entry: ttk.Entry) -> None:
        try:
            entry.delete(0, tk.END)
            entry.insert(0, datetime.utcnow().date().isoformat())
        except Exception:
            pass

    def _queue_adjustment_request(self) -> None:
        """Add an adjustment request to the queue."""
        desc = (self.adjust_desc.get() if hasattr(self, 'adjust_desc') else '').strip()
        by = (self.adjust_requested_by.get() if hasattr(self, 'adjust_requested_by') else '').strip()
        notes = (self.adjust_notes.get() if hasattr(self, 'adjust_notes') else '').strip()
        if not desc:
            messagebox.showinfo("Missing Description", "Please enter a description for the adjustment request.")
            return
        try:
            aid = db.create_adjustment_request(self.current_period_id or db.get_current_period()['id'], desc, requested_by=by or None, notes=notes or None, conn=self.engine.conn)
            messagebox.showinfo("Requested", f"Adjustment request {aid} created.")
            self._load_adjustments()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create adjustment request: {e}")

    def _load_adjustments(self) -> None:
        """Load adjustment requests into the treeview."""
        if hasattr(self, 'adjust_tree'):
            for item in self.adjust_tree.get_children():
                self.adjust_tree.delete(item)
        try:
            rows = db.list_adjustment_requests(self.current_period_id or db.get_current_period()['id'], conn=self.engine.conn)
            for r in rows:
                self.adjust_tree.insert('', 'end', values=(r['id'], r['description'], r['requested_on'], r['status'], r['notes'] or ''))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load adjustments: {e}")

    def _mark_adjustment_status(self, status: str) -> None:
        """Update status of selected adjustment requests."""
        sel = self.adjust_tree.selection()
        if not sel:
            messagebox.showinfo("Select Request", "Please select one or more adjustment requests to update.")
            return
        try:
            for item in sel:
                vals = self.adjust_tree.item(item, 'values')
                adj_id = int(vals[0])
                db.update_adjustment_status(adj_id, status, conn=self.engine.conn)
            messagebox.showinfo("Updated", f"Updated {len(sel)} request(s) to '{status}'.")
            self._load_adjustments()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update adjustment(s): {e}")

    def _build_journal_tab(self) -> None:
        """Build the journal entries tab with a list of all journal entries"""
        frame = self.tab_journal
        
        # Create a frame for the toolbar
        toolbar = ttk.Frame(frame, style="Techfix.Surface.TFrame")
        toolbar.pack(fill=tk.X, padx=4, pady=4)
        
        # Add refresh button
        ttk.Button(
            toolbar,
            text="Refresh",
            command=self._load_journal_entries,
            style="Techfix.TButton"
        ).pack(side=tk.LEFT, padx=2)
        # Export to Excel button for journal
        ttk.Button(
            toolbar,
            text="Export to Excel",
            command=lambda: self._export_tree_to_excel(self.journal_tree, default_name=f"journal_{self.fs_date_to.get() if hasattr(self, 'fs_date_to') else ''}.xlsx"),
            style="Techfix.TButton"
        ).pack(side=tk.LEFT, padx=2)
        
        # Add filter controls
        filter_frame = ttk.Frame(toolbar, style="Techfix.Surface.TFrame")
        filter_frame.pack(side=tk.RIGHT, padx=4)
        
        ttk.Label(filter_frame, text="Filter by:", style="Techfix.TLabel").pack(side=tk.LEFT, padx=4)
        
        # Date range filter
        self.journal_date_from = ttk.Entry(filter_frame, width=10, style="Techfix.TEntry")
        self.journal_date_from.pack(side=tk.LEFT, padx=2)
        ttk.Label(filter_frame, text="to", style="Techfix.TLabel").pack(side=tk.LEFT)
        self.journal_date_to = ttk.Entry(filter_frame, width=10, style="Techfix.TEntry")
        self.journal_date_to.pack(side=tk.LEFT, padx=2)
        
        # Account filter
        self.journal_account_filter = ttk.Combobox(
            filter_frame, 
            width=20, 
            state="readonly",
            style="Techfix.TCombobox"
        )
        self.journal_account_filter.pack(side=tk.LEFT, padx=4)
        try:
            accs = db.get_accounts(conn=self.engine.conn)
            names = ["All"] + [f"{a['code']} - {a['name']}" for a in accs]
            self.journal_account_filter['values'] = names
            try:
                self.journal_account_filter.set("All")
            except Exception:
                pass
        except Exception:
            pass
        self.journal_account_filter.bind("<<ComboboxSelected>>", lambda e: self._load_journal_entries())
        
        # Create the treeview for journal entries
        columns = ("date", "reference", "description", "debit", "credit", "account")
        self.journal_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Techfix.Treeview"
        )
        
        # Configure columns
        self.journal_tree.heading("date", text="Date")
        self.journal_tree.heading("reference", text="Reference")
        self.journal_tree.heading("description", text="Description")
        self.journal_tree.heading("debit", text="Debit")
        self.journal_tree.heading("credit", text="Credit")
        self.journal_tree.heading("account", text="Account")
        
        # Set column widths
        self.journal_tree.column("date", width=100, anchor=tk.W)
        self.journal_tree.column("reference", width=100, anchor=tk.W)
        self.journal_tree.column("description", width=250, anchor=tk.W)
        self.journal_tree.column("debit", width=100, anchor=tk.E)
        self.journal_tree.column("credit", width=100, anchor=tk.E)
        self.journal_tree.column("account", width=200, anchor=tk.W)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.journal_tree.yview)
        self.journal_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack the treeview and scrollbar
        self.journal_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
        
        # Bind double-click event
        self.journal_tree.bind("<Double-1>", self._on_journal_entry_double_click)
        
        self._load_journal_entries()

    def _load_journal_entries(self):
        for item in self.journal_tree.get_children():
            self.journal_tree.delete(item)
        try:
            rows = db.fetch_journal(period_id=self.engine.current_period_id, conn=self.engine.conn)
            # Optional account filtering from dropdown
            sel = ''
            try:
                sel = self.journal_account_filter.get().strip()
            except Exception:
                sel = ''
            if sel and sel.lower() != 'all':
                try:
                    code, name_match = sel.split(' - ', 1)
                except Exception:
                    code, name_match = sel, ''
                rows = [r for r in rows if ((('code' in r.keys()) and r['code'] == code) or r['name'] == name_match)]
            # Optional date range filter (from/to)
            from_s = to_s = ''
            try:
                from_s = self.journal_date_from.get().strip()
            except Exception:
                from_s = ''
            try:
                to_s = self.journal_date_to.get().strip()
            except Exception:
                to_s = ''
            if from_s or to_s:
                from_dt = None
                to_dt = None
                try:
                    if from_s:
                        from_dt = datetime.strptime(from_s, '%Y-%m-%d').date()
                except Exception:
                    from_dt = None
                try:
                    if to_s:
                        to_dt = datetime.strptime(to_s, '%Y-%m-%d').date()
                except Exception:
                    to_dt = None
                def _in_range(dstr: str) -> bool:
                    try:
                        d = datetime.strptime(dstr, '%Y-%m-%d').date()
                    except Exception:
                        return False
                    if from_dt and d < from_dt:
                        return False
                    if to_dt and d > to_dt:
                        return False
                    return True
                rows = [r for r in rows if _in_range(r['date'])]
            current_entry = None
            total_debit = 0.0
            total_credit = 0.0
            for r in rows:
                eid = r["entry_id"]
                date = r["date"]
                desc = r["description"]
                try:
                    doc_ref = r["document_ref"] if "document_ref" in r.keys() else None
                except Exception:
                    doc_ref = None
                try:
                    ext_ref = r["external_ref"] if "external_ref" in r.keys() else None
                except Exception:
                    ext_ref = None
                ref = (str(doc_ref).strip() if doc_ref else "") or (str(ext_ref).strip() if ext_ref else "")
                acct = r["name"]
                debit = r["debit"]
                credit = r["credit"]
                try:
                    total_debit += float(debit or 0)
                except Exception:
                    pass
                try:
                    total_credit += float(credit or 0)
                except Exception:
                    pass
                iid = f"je-{eid}-line-{r['line_id']}"
                # Insert a header row (first line for an entry) with the date and description
                if current_entry != eid:
                    self.journal_tree.insert('', 'end', iid=iid, values=(date, ref, desc, f"{debit:,.2f}" if debit else "", f"{credit:,.2f}" if credit else "", acct))
                    current_entry = eid
                else:
                    # Subsequent lines for the same entry should show blanks for date/description
                    self.journal_tree.insert('', 'end', iid=iid, values=("", "", "", f"{debit:,.2f}" if debit else "", f"{credit:,.2f}" if credit else "", acct))
            # Insert totals row
            try:
                self.journal_tree.insert('', 'end', values=("", "", "Totals:", f"{total_debit:,.2f}", f"{total_credit:,.2f}", ""), tags=('totals',))
                self.journal_tree.tag_configure('totals', background=self.palette.get('tab_selected_bg', '#e0ecff'))
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load journal entries: {str(e)}")

    def _load_recent_transactions(self, limit: int = 50) -> None:
        """Populate the Recent Transactions tree with the most recent entries, including drafts without lines."""
        try:
            if hasattr(self, 'txn_recent_tree'):
                for it in self.txn_recent_tree.get_children():
                    self.txn_recent_tree.delete(it)
            conn = self.engine.conn
            pid = self.engine.current_period_id
            clause = "WHERE je.period_id = ?" if pid else ""
            params = ([int(pid)] if pid else []) + [limit]
            sql = (
                """
                SELECT je.id AS entry_id, je.date AS date, je.description AS description, je.status AS status
                FROM journal_entries je
                """
                + (clause or "")
                + """
                ORDER BY date(je.date) DESC, je.id DESC
                LIMIT ?
                """
            )
            cur = conn.execute(sql, params)
            entries = cur.fetchall()
            for e in entries:
                eid = e['entry_id'] if 'entry_id' in e.keys() else e['id']
                date = e['date'] if 'date' in e.keys() else ''
                desc = e['description'] if 'description' in e.keys() else ''
                # Aggregate debit/credit and pick a representative account name (first line)
                try:
                    rsum = conn.execute(
                        """
                        SELECT COALESCE(SUM(jl.debit),0) AS debit, COALESCE(SUM(jl.credit),0) AS credit
                        FROM journal_lines jl
                        WHERE jl.entry_id=?
                        """,
                        (eid,)
                    ).fetchone()
                    debit = float(rsum['debit'] if 'debit' in rsum.keys() else 0) if rsum else 0.0
                    credit = float(rsum['credit'] if 'credit' in rsum.keys() else 0) if rsum else 0.0
                    racct = conn.execute(
                        """
                        SELECT a.name
                        FROM journal_lines jl
                        JOIN accounts a ON a.id = jl.account_id
                        WHERE jl.entry_id=?
                        ORDER BY jl.id
                        LIMIT 1
                        """,
                        (eid,)
                    ).fetchone()
                    acct = (racct['name'] if racct and 'name' in racct.keys() else '')
                except Exception:
                    debit = 0.0
                    credit = 0.0
                    acct = ''
                self.txn_recent_tree.insert(
                    '', 'end',
                    values=(date, eid, desc, f"{debit:,.2f}" if debit else '', f"{credit:,.2f}" if credit else '', acct),
                    tags=('row',)
                )
            try:
                self.txn_recent_tree.tag_configure('row', background=self.palette.get('surface_bg', '#ffffff'))
            except Exception:
                pass
            try:
                self.txn_recent_tree.yview_moveto(0)
            except Exception:
                pass
        except Exception:
            pass
    
    def _on_journal_entry_double_click(self, event):
        """Handle double-click on a journal entry"""
        sel = self.journal_tree.selection()
        if not sel:
            return
        item = sel[0]
        # Try to extract the entry id from the item's IID which we set when populating the tree
        iid = str(item)
        entry_id = None
        try:
            if iid.startswith('je-'):
                # IID format: je-<entry_id>-line-<line_id>
                parts = iid.split('-')
                if len(parts) >= 3:
                    entry_id = int(parts[1])
        except Exception:
            entry_id = None

        # Fallback: if we couldn't parse an entry_id from the IID, try reading the visible date column
        if entry_id is None:
            values = self.journal_tree.item(item, 'values')
            if values:
                # If the first displayed column contains a date, this is a header row; otherwise do nothing
                maybe_date = values[0]
                try:
                    # If the date value exists, try to find the corresponding entry by matching date+description
                    if maybe_date:
                        desc = values[2] if len(values) > 2 else None
                        # Query DB for an entry with this date and description (pick the latest match)
                        cur = self.engine.conn.execute("SELECT id FROM journal_entries WHERE date=? AND description=? ORDER BY id DESC LIMIT 1", (maybe_date, desc))
                        row = cur.fetchone()
                        if row:
                            entry_id = int(row['id'])
                except Exception:
                    entry_id = None

        if entry_id:
            try:
                self._load_transaction_for_editing(entry_id)
                self.notebook.select(self.tab_txn)
            except Exception as e:
                messagebox.showerror('Error', f'Failed to open transaction: {e}')
    
    def _load_transaction_for_editing(self, txn_id):
        """Load a transaction into the form for editing"""
        # This method would be implemented to load the selected transaction
        # into the transaction form for editing
        pass

    def _build_ledger_tab(self) -> None:
        """Build the ledger tab with a list of all accounts and their balances"""
        frame = self.tab_ledger
        
        # Create a frame for the toolbar
        toolbar = ttk.Frame(frame, style="Techfix.Surface.TFrame")
        toolbar.pack(fill=tk.X, padx=4, pady=4)
        
        # Add refresh button
        ttk.Button(
            toolbar,
            text="Refresh",
            command=self._load_ledger_entries,
            style="Techfix.TButton"
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            toolbar,
            text="Post to Ledger",
            command=self._post_to_ledger_action,
            style="Techfix.TButton"
        ).pack(side=tk.LEFT, padx=6)
        # Export ledger to Excel
        ttk.Button(
            toolbar,
            text="Export to Excel",
            command=lambda: self._export_tree_to_excel(self.ledger_tree, default_name=f"ledger_{self.fs_date_to.get() if hasattr(self, 'fs_date_to') else ''}.xlsx"),
            style="Techfix.TButton"
        ).pack(side=tk.LEFT, padx=6)
        
        # Add account filter
        filter_frame = ttk.Frame(toolbar, style="Techfix.Surface.TFrame")
        filter_frame.pack(side=tk.RIGHT, padx=4)
        
        ttk.Label(filter_frame, text="Account:", style="Techfix.TLabel").pack(side=tk.LEFT, padx=4)
        self.ledger_account_filter = ttk.Combobox(
            filter_frame,
            width=30,
            state="readonly",
            style="Techfix.TCombobox"
        )
        self.ledger_account_filter.pack(side=tk.LEFT, padx=4)
        self.ledger_account_filter.bind("<<ComboboxSelected>>", lambda e: self._load_ledger_entries())
        try:
            accs = db.get_accounts(conn=self.engine.conn)
            names = ["All"] + [f"{a['code']} - {a['name']}" for a in accs]
            self.ledger_account_filter['values'] = names
            try:
                self.ledger_account_filter.set("All")
            except Exception:
                pass
        except Exception:
            pass
        
        # Create the treeview for ledger entries
        columns = ("account", "debit", "credit", "balance")
        self.ledger_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Techfix.Treeview"
        )
        
        # Configure columns
        self.ledger_tree.heading("account", text="Account", anchor=tk.W)
        self.ledger_tree.heading("debit", text="Debit", anchor=tk.E)
        self.ledger_tree.heading("credit", text="Credit", anchor=tk.E)
        self.ledger_tree.heading("balance", text="Balance", anchor=tk.E)
        
        # Set column widths
        self.ledger_tree.column("account", width=300, anchor=tk.W)
        self.ledger_tree.column("debit", width=150, anchor=tk.E)
        self.ledger_tree.column("credit", width=150, anchor=tk.E)
        self.ledger_tree.column("balance", width=150, anchor=tk.E)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.ledger_tree.yview)
        self.ledger_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack the treeview and scrollbar
        self.ledger_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
        
        # Bind double-click event
        self.ledger_tree.bind("<Double-1>", self._on_ledger_entry_double_click)
        
        # Load initial data
        self._load_ledger_entries()

    def _load_ledger_entries(self):
        for item in self.ledger_tree.get_children():
            self.ledger_tree.delete(item)
        try:
            rows = db.compute_trial_balance(period_id=self.engine.current_period_id, conn=self.engine.conn)
            sel = ''
            try:
                sel = self.ledger_account_filter.get().strip()
            except Exception:
                sel = ''
            if sel and sel.lower() != 'all':
                try:
                    code, name_match = sel.split(' - ', 1)
                except Exception:
                    code, name_match = sel, ''
                rows = [r for r in rows if (('code' in r.keys() and r['code'] == code) or r['name'] == name_match)]
            # Hide accounts with zero activity in current period
            def _has_activity(r):
                d, c = self._balance_to_columns(r)
                return bool((d or 0) != 0 or (c or 0) != 0)
            rows = [r for r in rows if _has_activity(r)]
            total_debit = 0.0
            total_credit = 0.0
            for r in rows:
                name = r['name']
                try:
                    code = r['code'] if 'code' in r.keys() else ''
                    name = f"{code} - {name}" if code else name
                except Exception:
                    pass
                d, c = self._balance_to_columns(r)
                try:
                    total_debit += float(d or 0)
                except Exception:
                    pass
                try:
                    total_credit += float(c or 0)
                except Exception:
                    pass
                bal = d if d else c
                side = 'Dr' if d else ('Cr' if c else '')
                self.ledger_tree.insert('', 'end', values=(name, f"{d:,.2f}" if d else '', f"{c:,.2f}" if c else '', f"{bal:,.2f} {side}" if bal else ''))
            # Totals row
            try:
                self.ledger_tree.insert('', 'end', values=("Totals", f"{total_debit:,.2f}" if total_debit else '', f"{total_credit:,.2f}" if total_credit else '', ""), tags=('totals',))
                self.ledger_tree.tag_configure('totals', background=self.palette.get('tab_selected_bg', '#e0ecff'))
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ledger entries: {str(e)}")

    def _record_transaction(self, status: str) -> None:
        try:
            date = self.txn_date.get().strip() if hasattr(self, 'txn_date') else ''
            desc = self.txn_desc.get().strip() if hasattr(self, 'txn_desc') else ''
            debit_acct = self.debit_acct.get().strip() if hasattr(self, 'debit_acct') else ''
            credit_acct = self.credit_acct.get().strip() if hasattr(self, 'credit_acct') else ''
            debit_amt_txt = self.debit_amt.get().strip() if hasattr(self, 'debit_amt') else ''
            credit_amt_txt = self.credit_amt.get().strip() if hasattr(self, 'credit_amt') else ''
            doc_ref = self.txn_doc_ref.get().strip() if hasattr(self, 'txn_doc_ref') else None
            ext_ref = self.txn_external_ref.get().strip() if hasattr(self, 'txn_external_ref') else None
            memo = self.txn_memo.get('1.0', tk.END).strip() if hasattr(self, 'txn_memo') else None
            source_type = self.txn_source_type.get().strip() if hasattr(self, 'txn_source_type') else None
            attach = self.txn_attachment_path.get().strip() if hasattr(self, 'txn_attachment_path') else None
            is_adjust = bool(self.txn_is_adjust.get()) if hasattr(self, 'txn_is_adjust') else False
            schedule = bool(self.txn_schedule_reverse.get()) if hasattr(self, 'txn_schedule_reverse') else False
            reverse_on = self.txn_reverse_date.get().strip() if schedule and hasattr(self, 'txn_reverse_date') else None
            if status == 'draft':
                if not date:
                    date = datetime.now().strftime('%Y-%m-%d')
                if not desc:
                    desc = 'Draft'
                lines: list[JournalLine] = []
                try:
                    if debit_acct and credit_acct and debit_amt_txt and credit_amt_txt:
                        debit_amt = float(debit_amt_txt)
                        credit_amt = float(credit_amt_txt)
                        if round(debit_amt - credit_amt, 2) == 0:
                            did = self.account_id_by_display.get(debit_acct)
                            cid = self.account_id_by_display.get(credit_acct)
                            if did and cid:
                                lines = [JournalLine(account_id=did, debit=debit_amt), JournalLine(account_id=cid, credit=credit_amt)]
                except Exception:
                    lines = []
                entry_id = self.engine.record_entry(
                    date,
                    desc,
                    lines,
                    is_adjusting=is_adjust,
                    document_ref=doc_ref or None,
                    external_ref=ext_ref or None,
                    memo=memo or None,
                    source_type=source_type or None,
                    status=status,
                    attachments=[('document', attach)] if attach else None,
                    schedule_reverse_on=reverse_on or None,
                )
                messagebox.showinfo('Saved', f'Draft {entry_id} saved')
                try:
                    if self.current_period_id:
                        self.period_form_cache[int(self.current_period_id)] = self._snapshot_txn_form()
                except Exception:
                    pass
                self._clear_transaction_form()
                try:
                    self._load_recent_transactions()
                except Exception:
                    pass
                return
            if not date or not desc:
                messagebox.showerror('Error', 'Date and description are required')
                return
            if not debit_acct or not credit_acct:
                messagebox.showerror('Error', 'Select both debit and credit accounts')
                return
            debit_amt = float(debit_amt_txt)
            credit_amt = float(credit_amt_txt)
            if round(debit_amt - credit_amt, 2) != 0:
                messagebox.showerror('Error', 'Debits must equal credits')
                return
            did = self.account_id_by_display.get(debit_acct)
            cid = self.account_id_by_display.get(credit_acct)
            lines = [JournalLine(account_id=did, debit=debit_amt), JournalLine(account_id=cid, credit=credit_amt)]
            entry_id = self.engine.record_entry(
                date,
                desc,
                lines,
                is_adjusting=is_adjust,
                document_ref=doc_ref or None,
                external_ref=ext_ref or None,
                memo=memo or None,
                source_type=source_type or None,
                status=status,
                attachments=[('document', attach)] if attach else None,
                schedule_reverse_on=reverse_on or None,
            )
            messagebox.showinfo('Recorded', f'Journal entry {entry_id} recorded')
            try:
                if self.current_period_id:
                    self.period_form_cache[int(self.current_period_id)] = self._snapshot_txn_form()
            except Exception:
                pass
            self._refresh_after_post()
            self._clear_transaction_form()
        except Exception as e:
            messagebox.showerror('Error', f'Failed to record transaction: {e}')

    def _on_ledger_entry_double_click(self, event):
        """Handle double-click on a ledger entry"""
        item = self.ledger_tree.selection()[0]
        values = self.ledger_tree.item(item, 'values')
        
        if values:
            account_name = values[0].split(' (')[0]  # Extract account name
            self._view_account_details(account_name)

    def _view_account_details(self, account_name):
        """Show detailed transactions for the selected account"""
        # This method would show a detailed view of transactions for the selected account
        messagebox.showinfo(
            "Account Details",
            f"Showing transactions for account: {account_name}\n\n"
            "This would show a detailed transaction history for the selected account."
        )

    def _build_fs_tab(self) -> None:
        frame = self.tab_fs
        
        # Date range controls
        controls = ttk.Frame(frame, style="Techfix.Surface.TFrame")
        controls.pack(fill=tk.X, padx=12, pady=12)
        
        # Date range selection
        date_frame = ttk.Frame(controls, style="Techfix.Surface.TFrame")
        date_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(date_frame, text="From (YYYY-MM-DD):", style="Techfix.AppBar.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.fs_date_from = ttk.Entry(date_frame, width=12, style="Techfix.TEntry")
        self.fs_date_from.pack(side=tk.LEFT, padx=(0, 12))
        
        ttk.Label(date_frame, text="To (YYYY-MM-DD):", style="Techfix.AppBar.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.fs_date_to = ttk.Entry(date_frame, width=12, style="Techfix.TEntry")
        self.fs_date_to.pack(side=tk.LEFT)
        
        # Default to current date
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")
        self.fs_date_to.insert(0, today)
        
        # Action buttons
        btn_frame = ttk.Frame(controls, style="Techfix.Surface.TFrame")
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(
            btn_frame, 
            text="🔁 Generate", 
            command=self._load_financials, 
            style="Techfix.TButton"
        ).pack(side=tk.LEFT, padx=4)
        
        ttk.Button(
            btn_frame,
            text="💾 Export to Excel",
            command=self._export_fs,
            style="Techfix.TButton"
        ).pack(side=tk.LEFT, padx=4)
        
        ttk.Button(
            btn_frame,
            text="💾 Export to Text",
            command=self._export_financials,
            style="Techfix.TButton"
        ).pack(side=tk.LEFT, padx=4)
        
        # Create notebook for different financial statements
        self.fs_notebook = ttk.Notebook(frame, style="Techfix.TNotebook")
        self.fs_notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        
        # Income Statement Tab
        self.income_statement_frame = ttk.Frame(self.fs_notebook, style="Techfix.Surface.TFrame")
        self.fs_notebook.add(self.income_statement_frame, text="Income Statement")
        
        # Balance Sheet Tab
        self.balance_sheet_frame = ttk.Frame(self.fs_notebook, style="Techfix.Surface.TFrame")
        self.fs_notebook.add(self.balance_sheet_frame, text="Balance Sheet")
        
        # Cash Flow Tab (placeholder for future implementation)
        self.cash_flow_frame = ttk.Frame(self.fs_notebook, style="Techfix.Surface.TFrame")
        self.fs_notebook.add(self.cash_flow_frame, text="Cash Flow")
        try:
            self.fs_notebook.bind("<<NotebookTabChanged>>", self._on_fs_tab_changed)
        except Exception:
            pass
        
        # Create text widgets for each statement
        self._create_fs_text_widgets()

    def _on_fs_tab_changed(self, event=None):
        try:
            w = event.widget if event and hasattr(event, 'widget') else getattr(self, 'fs_notebook', None)
            if not w:
                return
            tab_id = w.select()
            if not tab_id:
                return
            try:
                frame = self.nametowidget(tab_id)
            except Exception:
                frame = None
            if frame:
                try:
                    self._animate_tab_pulse(frame)
                except Exception:
                    pass
        except Exception:
            pass

    def _build_trial_tab(self) -> None:
        """Build the Trial Balance tab"""
        frame = self.tab_trial

        # Controls frame with refresh
        controls = ttk.Frame(frame, style="Techfix.Surface.TFrame")
        controls.pack(fill=tk.X, padx=12, pady=8)

        ttk.Label(controls, text="As of (YYYY-MM-DD):", style="Techfix.AppBar.TLabel").pack(side=tk.LEFT)
        self.tb_date = ttk.Entry(controls, width=14, style="Techfix.TEntry")
        self.tb_date.pack(side=tk.LEFT, padx=(6, 12))

        ttk.Button(controls, text="Refresh", command=self._load_trial_balances, style="Techfix.TButton").pack(side=tk.LEFT)
        # Export trial balance to Excel
        ttk.Button(controls, text="Export to Excel", command=lambda: self._export_tree_to_excel(self.trial_tree, default_name=f"trial_balance_{self.tb_date.get() if hasattr(self, 'tb_date') else ''}.xlsx"), style="Techfix.TButton").pack(side=tk.LEFT, padx=(6,0))
        self.tb_status_label = ttk.Label(controls, text="Unadjusted Trial Balance", style="Techfix.AppBar.TLabel")
        self.tb_status_label.pack(side=tk.RIGHT)

        cols = ("code", "name", "debit", "credit")
        self.trial_tree = ttk.Treeview(frame, columns=cols, show="headings", style="Techfix.Treeview")
        for c in cols:
            anchor = tk.E if c in ("debit", "credit") else tk.W
            width = 120 if c in ("debit", "credit") else 220
            self.trial_tree.heading(c, text=c.title(), anchor=anchor)
            self.trial_tree.column(c, stretch=True, width=width, anchor=anchor)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.trial_tree.yview)
        self.trial_tree.configure(yscrollcommand=vsb.set)
        self.trial_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 12))

        # Load initial data
        try:
            self._load_trial_balances()
        except Exception:
            pass

    def _load_trial_balances(self) -> None:
        """Compute and display the trial balance"""
        # Clear existing items
        if hasattr(self, 'trial_tree'):
            for item in self.trial_tree.get_children():
                self.trial_tree.delete(item)

        try:
            as_of = None
            if hasattr(self, 'tb_date'):
                d = self.tb_date.get().strip()
                as_of = d or None

            rows = db.compute_trial_balance(up_to_date=as_of, include_temporary=True, period_id=self.engine.current_period_id, conn=self.engine.conn)
            try:
                statuses = self.engine.get_cycle_status()
                step5 = next((r for r in statuses if int(r['step']) == 5), None)
                if step5 and (step5['status'] == 'completed'):
                    self.tb_status_label.configure(text="Adjusted Trial Balance")
                else:
                    self.tb_status_label.configure(text="Unadjusted Trial Balance")
            except Exception:
                pass
            # Show only accounts with non-zero balance/activity for the active period
            def _has_activity(r: dict) -> bool:
                dcol, ccol = self._balance_to_columns(r)
                return bool((dcol or 0) != 0 or (ccol or 0) != 0)
            rows = [r for r in rows if _has_activity(r)]

            for r in rows:
                dcol, ccol = self._balance_to_columns(r)
                code = r['code'] if 'code' in r.keys() else ''
                name = r['name'] if 'name' in r.keys() else ''
                self.trial_tree.insert('', 'end', values=(code, name, f"{dcol:,.2f}" if dcol else "", f"{ccol:,.2f}" if ccol else ""))
            # Add totals row
            try:
                total_d = 0.0
                total_c = 0.0
                for item in self.trial_tree.get_children():
                    vals = self.trial_tree.item(item, 'values')
                    try:
                        if vals and vals[2]:
                            total_d += float(str(vals[2]).replace(',', ''))
                    except Exception:
                        pass
                    try:
                        if vals and vals[3]:
                            total_c += float(str(vals[3]).replace(',', ''))
                    except Exception:
                        pass
                self.trial_tree.insert('', 'end', values=("", "Totals", f"{total_d:,.2f}", f"{total_c:,.2f}"), tags=('totals',))
                self.trial_tree.tag_configure('totals', background=self.palette.get('tab_selected_bg', '#e0ecff'))
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load trial balances: {str(e)}")

    def _export_tree_to_excel(self, tree: ttk.Treeview, *, default_name: str = "export.xlsx") -> None:
        """Export the contents of a Treeview to an Excel file using `db.export_rows_to_excel`.

        Rows are exported in the order they appear in the tree. Column headers are taken
        from `tree['columns']`. The totals row (if present) will be exported as-is.
        """
        try:
            cols = list(tree['columns']) if tree and 'columns' in tree.keys() else []
            headers = [str(c).title() for c in cols]
            rows = []
            for iid in tree.get_children():
                vals = tree.item(iid, 'values') or ()
                # Ensure the row is a simple list matching headers length
                row = [vals[i] if i < len(vals) else '' for i in range(len(headers))]
                rows.append(row)

            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
                initialfile=default_name,
            )
            if not filename:
                return
            from pathlib import Path
            try:
                from openpyxl import Workbook
                from openpyxl.utils import get_column_letter
                from openpyxl.styles import Font
            except Exception:
                # fallback to simple CSV/Excel writer
                db.export_rows_to_excel(rows, headers, Path(filename), sheet_name=Path(filename).stem)
                messagebox.showinfo("Export Successful", f"Exported to {filename}")
                return

            wb = Workbook()
            ws = wb.active
            ws.title = Path(filename).stem[:31]

            # write headers
            for cidx, h in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=cidx, value=h)
                cell.font = Font(bold=True)

            # write rows
            for ridx, row in enumerate(rows, start=2):
                for cidx, val in enumerate(row, start=1):
                    # try to write numeric values as numbers
                    if isinstance(val, (int, float)):
                        ws.cell(row=ridx, column=cidx, value=val)
                    else:
                        # attempt to parse numeric strings
                        s = str(val).replace(',', '') if val is not None else ''
                        try:
                            num = float(s)
                            ws.cell(row=ridx, column=cidx, value=num)
                        except Exception:
                            ws.cell(row=ridx, column=cidx, value=val)

            # Add totals for numeric columns (columns where all except header are numeric)
            max_row = ws.max_row
            for cidx in range(1, len(headers) + 1):
                # check if column appears numeric
                is_numeric = True
                for rr in range(2, max_row + 1):
                    v = ws.cell(row=rr, column=cidx).value
                    if v is None or isinstance(v, (int, float)):
                        continue
                    try:
                        float(str(v).replace(',', ''))
                    except Exception:
                        is_numeric = False
                        break
                if is_numeric and max_row >= 2:
                    col_letter = get_column_letter(cidx)
                    total_row = max_row + 1
                    ws.cell(row=total_row, column=cidx, value=f"=SUM({col_letter}2:{col_letter}{max_row})")

            # auto-width
            for i in range(1, len(headers) + 1):
                ws.column_dimensions[get_column_letter(i)].width = 15

            wb.save(filename)
            messagebox.showinfo("Export Successful", f"Exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export to Excel: {e}")

    def _balance_to_columns(self, row: dict) -> tuple[float, float]:
        """Convert a trial balance row into debit/credit columns.

        Returns (debit_amount, credit_amount)
        """
        try:
            normal = (row['normal_side'] if 'normal_side' in row.keys() else 'debit').lower()
            net_debit = float(row['net_debit'] if 'net_debit' in row.keys() and row['net_debit'] is not None else 0)
            net_credit = float(row['net_credit'] if 'net_credit' in row.keys() and row['net_credit'] is not None else 0)

            if normal == 'debit':
                bal = net_debit - net_credit
                if bal >= 0:
                    return (bal, 0.0)
                else:
                    return (0.0, abs(bal))
            else:
                bal = net_credit - net_debit
                if bal >= 0:
                    return (0.0, bal)
                else:
                    return (abs(bal), 0.0)
        except Exception:
            return (0.0, 0.0)
        
    def _create_fs_text_widgets(self):
        """Create and configure text widgets for financial statements"""
        # Create text widgets directly in their respective frames
        self.income_text = self._create_fs_text_widget(self.income_statement_frame)
        self.balance_sheet_text = self._create_fs_text_widget(self.balance_sheet_frame)
        self.cash_flow_text = self._create_fs_text_widget(self.cash_flow_frame)
        
        # Add some content to the cash flow tab
        self.cash_flow_text.insert(tk.END, "Cash Flow Statement\n" + "="*20 + "\n\n")
        self.cash_flow_text.insert(tk.END, "Cash flow statement will be implemented in a future update.\n")
        
    def _create_fs_text_widget(self, parent):
        """Helper to create a consistent text widget for financial statements"""
        # Create a frame to hold everything
        container = ttk.Frame(parent, style="Techfix.Surface.TFrame")
        container.pack(fill=tk.BOTH, expand=True)
        
        # Create text widget with improved styling
        text_widget = tk.Text(
            container,
            wrap=tk.WORD,
            font=FONT_MONO,
            bg=self.palette["surface_bg"],
            fg=self.palette["text_primary"],
            insertbackground=self.palette["text_primary"],
            selectbackground=self.palette["accent_color"],
            selectforeground="white",
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=20
        )
        
        # Configure tags for formatting
        text_widget.tag_configure("header", font=("Segoe UI", 16, "bold"), 
                                foreground=self.palette["accent_color"])
        text_widget.tag_configure("subheader", font=("Segoe UI", 10), 
                                foreground=self.palette["text_secondary"])
        text_widget.tag_configure("section", font=("Segoe UI", 12, "bold"), 
                                foreground=self.palette["text_primary"])
        text_widget.tag_configure("total", font=("Segoe UI", 10, "bold"), 
                                foreground=self.palette["text_primary"])
        text_widget.tag_configure("net", font=("Segoe UI", 12, "bold"), 
                                foreground=self.palette["accent_color"])
        text_widget.tag_configure("warning", foreground="red")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Pack them with scrollbar on right, text on left
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Make text widget read-only
        text_widget.config(state=tk.DISABLED)
        
        # Add a method to update the text widget
        def update_text(content, tags=None):
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            if tags:
                text_widget.insert(tk.END, content, tags)
            else:
                text_widget.insert(tk.END, content)
            text_widget.config(state=tk.DISABLED)
            text_widget.see(tk.END)  # Scroll to the end
            
        # Add the update method to the text widget
        text_widget.update_text = update_text
        
        # Configure grid weights to make the container expand properly
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        return text_widget
        
    def _export_financials(self):
        """Export the current financial statements to a file"""
        # Get the currently selected tab
        current_tab = self.fs_notebook.select()
        if not current_tab:
            messagebox.showinfo("Export", "Please select a financial statement to export.")
            return
            
        tab_index = self.fs_notebook.index(current_tab)
        tab_name = self.fs_notebook.tab(tab_index, "text")
        
        # Get the text widget for the current tab
        if tab_index == 0:  # Income Statement
            content = self.income_text.get(1.0, tk.END)
        elif tab_index == 1:  # Balance Sheet
            content = self.balance_sheet_text.get(1.0, tk.END)
        else:  # Cash Flow or other tabs
            messagebox.showinfo("Export", "Export not available for this statement yet.")
            return
        
        # Ask for save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"{tab_name.replace(' ', '_')}_{self.fs_date_to.get() or 'report'}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Export Successful", f"{tab_name} exported successfully!")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export {tab_name}: {str(e)}")

    def _generate_income_statement(self, trial_balance: list, as_of_date: str = None) -> None:
        """Generate and display the income statement from trial balance data"""
        try:
            # Group accounts by type
            revenue = []
            expenses = []
            
            for row in trial_balance:
                account_type = row['type'].lower()
                # Use net_credit for revenue and net_debit for expenses
                if account_type == 'revenue':
                    amount = row['net_credit'] - row['net_debit']
                    if abs(amount) > 0.01:  # Only include accounts with non-zero balances (allowing for rounding)
                        revenue.append((row['name'], amount))
                elif account_type == 'expense':
                    amount = row['net_debit'] - row['net_credit']
                    if abs(amount) > 0.01:  # Only include accounts with non-zero balances (allowing for rounding)
                        expenses.append((row['name'], amount))
            
            # Helper to format amounts (use parentheses for negative values)
            def fmt(a: float) -> str:
                try:
                    a = float(a or 0)
                except Exception:
                    return str(a)
                if a < 0:
                    return f"({abs(a):,.2f})"
                return f"{a:,.2f}"

            # Calculate totals (signed sums) and net income
            total_revenue = sum(amt for _, amt in revenue)
            total_expenses = sum(amt for _, amt in expenses)
            net_income = total_revenue - total_expenses
            
            # Format the income statement
            content = []
            content.append(('Income Statement\n', 'header'))
            content.append((f'For the period ended {as_of_date or "current date"}\n\n', 'subheader'))
            
            # Add revenues
            content.append(('Revenues\n', 'section'))
            for name, amount in revenue:
                content.append((f'{name}: {fmt(amount)}\n', None))
            
            content.append((f'\nTotal Revenue: {fmt(total_revenue)}\n\n', 'total'))
            
            # Add expenses
            content.append(('Expenses\n', 'section'))
            for name, amount in expenses:
                content.append((f'{name}: {fmt(amount)}\n', None))
            
            content.append((f'\nTotal Expenses: {fmt(total_expenses)}\n\n', 'total'))
            content.append((f'Net Income: {fmt(net_income)}\n', 'net'))
            
            # Update the text widget using the custom update_text method
            self.income_text.config(state=tk.NORMAL)
            self.income_text.delete(1.0, tk.END)
            for text, tag in content:
                if tag:
                    self.income_text.insert(tk.END, text, tag)
                else:
                    self.income_text.insert(tk.END, text)
            self.income_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate income statement: {str(e)}")
            raise
    
    def _generate_balance_sheet(self, trial_balance: list, as_of_date: str = None) -> None:
        """Generate and display the balance sheet from trial balance data"""
        try:
            # Group accounts by type
            assets = []
            liabilities = []
            equity = []
            
            for row in trial_balance:
                account_type = row['type'].lower()
                # Calculate balance based on normal_side
                if row['normal_side'].lower() == 'debit':
                    balance = row['net_debit'] - row['net_credit']
                else:
                    balance = row['net_credit'] - row['net_debit']
                
                if abs(balance) < 0.01:  # Skip if balance is effectively zero
                    continue
                    
                if account_type == 'asset':
                    assets.append((row['name'], balance))
                elif account_type == 'contra asset' or account_type == 'contra_asset':
                    # Contra-assets reduce total assets; store as negative amount so totals reflect reduction
                    try:
                        contra_amount = -abs(balance)
                    except Exception:
                        contra_amount = -float(balance)
                    assets.append((row['name'], contra_amount))
                elif account_type == 'liability':
                    liabilities.append((row['name'], balance))
                elif account_type == 'equity':
                    equity.append((row['name'], balance))
            
            # Helper to format amounts (use parentheses for negative values)
            def fmt(a: float) -> str:
                try:
                    a = float(a or 0)
                except Exception:
                    return str(a)
                if a < 0:
                    return f"({abs(a):,.2f})"
                return f"{a:,.2f}"

            # Calculate totals
            total_assets = sum(amt for _, amt in assets)
            total_liabilities = sum(amt for _, amt in liabilities)
            total_equity = sum(amt for _, amt in equity)
            
            # Build the balance sheet content
            content = []
            content.append(("Balance Sheet\n", "header"))
            content.append((f"As of {as_of_date or 'current date'}\n\n", "subheader"))
            
            # Add assets section
            content.append(("Assets\n", "section"))
            for name, amount in assets:
                if amount != 0:  # Only show accounts with non-zero balances
                    content.append((f"{name}: {amount:,.2f}\n", None))
            content.append((f"\nTotal Assets: {fmt(total_assets)}\n\n", "total"))
            
            # Add liabilities section
            content.append(("Liabilities\n", "section"))
            for name, amount in liabilities:
                if amount != 0:  # Only show accounts with non-zero balances
                    content.append((f"{name}: {amount:,.2f}\n", None))
            content.append((f"\nTotal Liabilities: {fmt(total_liabilities)}\n\n", "total"))
            
            # Add equity section
            content.append(("Equity\n", "section"))
            for name, amount in equity:
                if amount != 0:  # Only show accounts with non-zero balances
                    content.append((f"{name}: {amount:,.2f}\n", None))
            # If temporary accounts (revenue/expense) are present but not closed, show Net Income and include it in equity
            temp_net = 0.0
            for row in trial_balance:
                # trial_balance rows are sqlite3.Row objects; use index access
                t = (row['type'] or '').lower() if 'type' in row.keys() else ''
                if t in ('revenue', 'expense'):
                    # compute effect on equity: credits increase equity, debits decrease
                    nd = float(row['net_debit'] or 0) if 'net_debit' in row.keys() else 0.0
                    nc = float(row['net_credit'] or 0) if 'net_credit' in row.keys() else 0.0
                    temp_net += (nc - nd)
            if abs(temp_net) >= 0.01:
                content.append((f"Net Income (unclosed): {fmt(temp_net)}\n", None))
                total_equity = round(float(total_equity) + temp_net, 2)

            content.append((f"\nTotal Equity: {fmt(total_equity)}\n\n", "total"))
            
            # Check accounting equation
            accounting_eq = total_assets - (total_liabilities + total_equity)
            if abs(accounting_eq) > 0.01:  # Allow for small floating point differences
                content.append((
                    f"\nWarning: Accounting equation does not balance!\n"
                    f"Assets ({fmt(total_assets)}) ≠ Liabilities + Equity ({fmt(total_liabilities + total_equity)})\n"
                    f"Difference: {fmt(accounting_eq)}\n", 
                    "warning"
                ))
            
            # Update the text widget using the custom update_text method
            self.balance_sheet_text.config(state=tk.NORMAL)
            self.balance_sheet_text.delete(1.0, tk.END)
            for text, tag in content:
                if tag:
                    self.balance_sheet_text.insert(tk.END, text, tag)
                else:
                    self.balance_sheet_text.insert(tk.END, text)
            self.balance_sheet_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate balance sheet: {str(e)}")
            raise

    def _regenerate_financial_statements(self, as_of_date: str | None = None) -> None:
        """Re-generate income statement and balance sheet text without modifying cycle status.

        This is used when switching themes to refresh the displayed text and tags without
        calling engine methods that change cycle step statuses.
        """
        try:
            date_to = as_of_date or (self.fs_date_to.get().strip() if hasattr(self, 'fs_date_to') else None)
            inc_temp_bs = True
            try:
                statuses = self.engine.get_cycle_status()
                step8 = next((r for r in statuses if int(r['step']) == 8), None)
                if step8 and (step8['status'] == 'completed'):
                    inc_temp_bs = False
            except Exception:
                pass
            rows = db.compute_trial_balance(up_to_date=date_to, include_temporary=inc_temp_bs, period_id=self.engine.current_period_id, conn=self.engine.conn)
            # Re-generate text widgets only (these functions write to Text widgets)
            try:
                self._generate_income_statement(rows, date_to)
            except Exception:
                pass
            try:
                self._generate_balance_sheet(rows, date_to)
            except Exception:
                pass
        except Exception:
            # Fail silently during theme refresh to avoid interrupting UI
            pass
    
    def _load_financials(self, mark_status: bool = True) -> None:
        """Load and display financial statements based on date range"""
        try:
            # Get date range from the UI
            date_from = self.fs_date_from.get().strip() or None
            date_to = self.fs_date_to.get().strip() or None
            
            # Clear previous content using the update_text method
            self.income_text.update_text("")
            self.balance_sheet_text.update_text("")
            self.cash_flow_text.update_text("")
            
            # Get trial balance data for the specified date range
            rows_is = db.compute_trial_balance(
                from_date=date_from,
                up_to_date=date_to,
                include_temporary=True,
                period_id=self.engine.current_period_id,
                conn=self.engine.conn
            )
            inc_temp_bs = True
            try:
                statuses = self.engine.get_cycle_status()
                step8 = next((r for r in statuses if int(r['step']) == 8), None)
                if step8 and (step8['status'] == 'completed'):
                    inc_temp_bs = False
            except Exception:
                pass
            rows_bs = db.compute_trial_balance(
                up_to_date=date_to,
                include_temporary=inc_temp_bs,
                period_id=self.engine.current_period_id,
                conn=self.engine.conn
            )
            
            # Process data for financial statements
            self._generate_income_statement(rows_is, date_to)
            self._generate_balance_sheet(rows_bs, date_to)
            # Generate cash flow using backend engine and render it
            try:
                # Determine safe start/end for cash flow
                start = date_from or (
                    (self.engine.current_period['start_date'] if self.engine.current_period and 'start_date' in self.engine.current_period.keys() else None)
                ) or '1900-01-01'
                end = date_to or (datetime.date.today().isoformat())
                cf = self.engine.generate_cash_flow(start, end)
                # Format cash flow content
                if isinstance(cf, dict) and cf.get('error'):
                    self.cash_flow_text.config(state=tk.NORMAL)
                    self.cash_flow_text.delete(1.0, tk.END)
                    self.cash_flow_text.insert(tk.END, f"Cash Flow Error: {cf.get('error')}\n", 'warning')
                    self.cash_flow_text.config(state=tk.DISABLED)
                else:
                    content = []
                    content.append(("Cash Flow Statement\n", 'header'))
                    content.append((f"Period: {start} → {end}\n\n", 'subheader'))
                    sections = cf.get('sections', {}) if isinstance(cf, dict) else {}
                    totals = cf.get('totals', {}) if isinstance(cf, dict) else {}
                    for sec in ('Operating', 'Investing', 'Financing'):
                        items = sections.get(sec, [])
                        content.append((f"{sec}\n", 'section'))
                        if not items:
                            content.append(("  (no activity)\n\n", None))
                        else:
                            for it in items:
                                try:
                                    amt = float(it.get('amount', 0))
                                except Exception:
                                    amt = 0.0
                                content.append((f"  {it.get('date','')}: Entry #{it.get('entry_id','')}: {amt:,.2f}\n", None))
                            content.append((f"\n  Total {sec}: {totals.get(sec,0):,.2f}\n\n", 'total'))
                    content.append((f"Net Change in Cash: {cf.get('net_change_in_cash',0):,.2f}\n", 'net'))
                    # Write to widget
                    try:
                        self.cash_flow_text.config(state=tk.NORMAL)
                        self.cash_flow_text.delete(1.0, tk.END)
                        for text, tag in content:
                            if tag:
                                self.cash_flow_text.insert(tk.END, text, tag)
                            else:
                                self.cash_flow_text.insert(tk.END, text)
                        self.cash_flow_text.config(state=tk.DISABLED)
                    except Exception:
                        pass
            except Exception:
                # If cash flow generation fails, don't block financials display
                pass
            
            # Only mark as completed if we got this far without errors and caller allows status changes
            if mark_status:
                self.engine.set_cycle_step_status(
                    7,
                    "completed",
                    note=f"Financial statements generated as of {date_to or 'latest'}",
                )
                self.engine.set_cycle_step_status(
                    8,
                    "in_progress",
                    note="Ready to prepare closing entries",
                )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate financial statements: {str(e)}")
            # Don't mark as completed or change cycle status if caller disallowed status changes
            if mark_status:
                try:
                    self.engine.set_cycle_step_status(
                        7,
                        "in_progress",
                        note=f"Error generating statements: {str(e)[:100]}",
                    )
                except Exception:
                    pass
        try:
            # Only update cycle step statuses here if caller allowed status changes
            if mark_status:
                self.engine.set_cycle_step_status(
                    7,
                    "completed",
                    note=f"Financial statements generated as of {date_to or 'latest'}",
                )
                self.engine.set_cycle_step_status(
                    8,
                    "in_progress",
                    note="Ready to prepare closing entries",
                )
            # Always refresh cycle status display in the UI
            self._load_cycle_status()
        except Exception:
            pass

    # --------------------- Closing Tab ---------------------
    def _build_closing_tab(self) -> None:
        frame = self.tab_closing
        frame.grid_rowconfigure(1, weight=2)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        top = ttk.Frame(frame, style="Techfix.Surface.TFrame")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        ttk.Label(top, text="Closing Date (YYYY-MM-DD)").pack(side=tk.LEFT, padx=(0, 6))
        self.close_date = ttk.Entry(top, width=16, style="Techfix.TEntry")
        self.close_date.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(top, text="Make Closing Entries", command=self._do_close, style="Techfix.TButton").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh Preview", command=self._load_closing_preview, style="Techfix.TButton").pack(
            side=tk.LEFT, padx=(12, 0)
        )

        preview = ttk.Labelframe(frame, text="Closing Entry Preview", style="Techfix.TLabelframe")
        preview.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        cols = ("code", "name", "action", "amount")
        self.closing_preview_tree = ttk.Treeview(preview, columns=cols, show="headings", style="Techfix.Treeview")
        for c in cols:
            width = 100 if c == "amount" else 160
            self.closing_preview_tree.heading(c, text=c.title(), anchor="w")
            self.closing_preview_tree.column(c, width=width, stretch=True)
        self.closing_preview_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._load_closing_preview()

        log_frame = ttk.Labelframe(frame, text="Closing Log", style="Techfix.TLabelframe")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.close_log = tk.Text(
            log_frame,
            height=8,
            bg=self.palette["surface_bg"],
            fg=self.palette["text_primary"],
            font=FONT_MONO,
            bd=0,
            highlightthickness=0,
            highlightbackground=self.palette.get("surface_bg", "#ffffff"),
            relief=tk.FLAT,
        )
        self.close_log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._load_closing_log()

    def _do_close(self) -> None:
        date = self.close_date.get().strip()
        try:
            if not date:
                date = datetime.utcnow().date().isoformat()
            else:
                datetime.strptime(date, '%Y-%m-%d')
        except Exception:
            messagebox.showerror('Error', 'Enter closing date as YYYY-MM-DD')
            return
        ids = self.engine.make_closing_entries(date)
        self.close_log.insert(tk.END, f"Created closing entries: {ids}\n")
        self._refresh_after_post()
        self._load_closing_preview()
        self._load_closing_log()

    def _load_closing_preview(self) -> None:
        """Populate the Closing Entry Preview with amounts that would be posted."""
        # Clear existing rows
        if hasattr(self, 'closing_preview_tree'):
            for it in self.closing_preview_tree.get_children():
                self.closing_preview_tree.delete(it)

        try:
            if not self.engine.current_period_id:
                return
            pid = self.engine.current_period_id
            conn = self.engine.conn
            cur = conn.cursor()
            inserted = False

            # Revenues to close
            cur.execute(
                """
                SELECT a.code, a.name, ROUND(COALESCE(SUM(jl.credit) - SUM(jl.debit),0),2) AS balance
                FROM accounts a
                LEFT JOIN journal_lines jl ON jl.account_id = a.id
                LEFT JOIN journal_entries je ON je.id = jl.entry_id
                WHERE a.type = 'Revenue' AND a.is_active=1 AND je.period_id = ?
                GROUP BY a.id, a.code, a.name
                HAVING ABS(balance) > 0.005
                """,
                (pid,)
            )
            for r in cur.fetchall():
                amt = float(r['balance'])
                action = 'Close revenue → Capital (credit)' if amt >= 0 else 'Close revenue (reverse-sign) → Capital (debit)'
                self.closing_preview_tree.insert('', 'end', values=(r['code'], r['name'], action, f"{abs(amt):,.2f}"))
                inserted = True

            # Expenses to close
            cur.execute(
                """
                SELECT a.code, a.name, ROUND(COALESCE(SUM(jl.debit) - SUM(jl.credit),0),2) AS balance
                FROM accounts a
                LEFT JOIN journal_lines jl ON jl.account_id = a.id
                LEFT JOIN journal_entries je ON je.id = jl.entry_id
                WHERE a.type = 'Expense' AND a.is_active=1 AND je.period_id = ?
                GROUP BY a.id, a.code, a.name
                HAVING ABS(balance) > 0.005
                """,
                (pid,)
            )
            for e in cur.fetchall():
                amt = float(e['balance'])
                action = 'Close expense → Capital (debit)' if amt > 0 else 'Close expense (reverse-sign) → Capital (credit)'
                self.closing_preview_tree.insert('', 'end', values=(e['code'], e['name'], action, f"{abs(amt):,.2f}"))
                inserted = True

            # Owner's Drawings (close to capital)
            drawings = db.get_account_by_name("Owner's Drawings", conn)
            if drawings:
                cur.execute(
                    """
                    SELECT ROUND(COALESCE(SUM(debit) - SUM(credit),0),2) AS balance
                    FROM journal_lines jl
                    JOIN journal_entries je ON je.id = jl.entry_id
                    WHERE jl.account_id = ? AND je.period_id = ?
                    """,
                    (drawings['id'], pid),
                )
                bal = float(cur.fetchone()[0] or 0)
                if bal > 0.005:
                    self.closing_preview_tree.insert('', 'end', values=(drawings['code'], "Owner's Drawings", 'Close drawings → Capital (debit)', f"{bal:,.2f}"))
                    inserted = True

            if not inserted:
                self.closing_preview_tree.insert('', 'end', values=("", "", "No amounts to close", ""))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load closing preview: {e}")

    def _load_closing_log(self) -> None:
        try:
            if hasattr(self, 'close_log'):
                self.close_log.delete('1.0', tk.END)
            rows = db.list_audit_log(limit=200, conn=self.engine.conn)
            for r in rows:
                action = r['action']
                det = r['details']
                try:
                    d = json.loads(det) if det else {}
                except Exception:
                    d = {}
                if action == 'journal_entry_created' and bool(d.get('is_closing')) and (not self.engine.current_period_id or int(d.get('period_id', 0) or 0) == int(self.engine.current_period_id)):
                    ts = r['timestamp']
                    eid = d.get('entry_id')
                    desc = d.get('description')
                    self.close_log.insert(tk.END, f"[{ts}] entry {eid} {desc}\n")
            if hasattr(self, 'close_log'):
                self.close_log.see(tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load closing log: {e}")

    # --------------------- Post-Closing Tab ---------------------
    def _build_postclosing_tab(self) -> None:
        frame = self.tab_postclosing
        controls = ttk.Frame(frame, style="Techfix.Surface.TFrame")
        controls.pack(fill=tk.X, padx=12, pady=(12, 6))
        ttk.Label(controls, text="As of (YYYY-MM-DD)").pack(side=tk.LEFT)
        self.pctb_date = ttk.Entry(controls, width=16, style="Techfix.TEntry")
        self.pctb_date.pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Refresh", command=self._load_postclosing_tb, style="Techfix.TButton").pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Complete Post-Closing TB", command=self._complete_postclosing_tb_action, style="Techfix.TButton").pack(side=tk.LEFT, padx=6)

        # Two-pane layout: left = Post-Closing TB, right = Reversing Schedule
        content = ttk.Frame(frame, style="Techfix.App.TFrame")
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Left pane: Post-Closing Trial Balance
        tb_wrap = ttk.Labelframe(content, text="Post-Closing Trial Balance", style="Techfix.TLabelframe")
        tb_wrap.grid(row=0, column=0, sticky="nsew", padx=0)
        cols = ("code", "name", "debit", "credit")
        self.pctb_tree = ttk.Treeview(tb_wrap, columns=cols, show="headings", style="Techfix.Treeview")
        for c in cols:
            self.pctb_tree.heading(c, text=c.title(), anchor="w")
            self.pctb_tree.column(c, stretch=True, width=140, anchor="w")
        pctb_scroll = ttk.Scrollbar(tb_wrap, orient=tk.VERTICAL, command=self.pctb_tree.yview)
        self.pctb_tree.configure(yscrollcommand=pctb_scroll.set)
        self.pctb_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        pctb_scroll.pack(side=tk.LEFT, fill=tk.Y, padx=(0,4), pady=4)

        # Right pane: Reversing Schedule
        sched_wrap = ttk.Labelframe(content, text="Reversing Entry Schedule", style="Techfix.TLabelframe")
        sched_wrap.grid(row=0, column=1, sticky="nsew", padx=0)
        schedule_controls = ttk.Frame(sched_wrap, style="Techfix.Surface.TFrame")
        schedule_controls.pack(fill=tk.X, padx=4, pady=(4, 4))
        ttk.Button(schedule_controls, text="Refresh Schedule", command=self._load_reversing_queue, style="Techfix.TButton").pack(side=tk.LEFT, padx=8)
        ttk.Button(schedule_controls, text="Complete Reversing Schedule", command=self._complete_reversing_schedule_action, style="Techfix.TButton").pack(side=tk.LEFT, padx=8)
        rcols = ("id", "original_entry", "reverse_on", "reversal_entry", "status")
        self.reversing_tree = ttk.Treeview(sched_wrap, columns=rcols, show="headings", style="Techfix.Treeview")
        for c in rcols:
            width = 80 if c == "id" else 140
            self.reversing_tree.heading(c, text=c.replace("_", " ").title(), anchor="w")
            self.reversing_tree.column(c, width=width, stretch=(c != "status"))
        rev_scroll = ttk.Scrollbar(sched_wrap, orient=tk.VERTICAL, command=self.reversing_tree.yview)
        self.reversing_tree.configure(yscrollcommand=rev_scroll.set)
        self.reversing_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        rev_scroll.pack(side=tk.LEFT, fill=tk.Y, padx=(0,4), pady=4)

    def _load_reversing_queue(self) -> None:
        """Load the reversing entry schedule into the treeview."""
        if hasattr(self, 'reversing_tree'):
            for it in self.reversing_tree.get_children():
                self.reversing_tree.delete(it)

        try:
            rows = self.engine.list_reversing_queue()
            for r in rows:
                self.reversing_tree.insert('', 'end', values=(r['id'], r['original_entry_id'], r['reverse_on'], r.get('reversed_entry_id') if 'reversed_entry_id' in r.keys() else '', r['status']))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load reversing queue: {e}")

    def _complete_reversing_schedule_action(self) -> None:
        try:
            as_of = (self.pctb_date.get().strip() if hasattr(self, 'pctb_date') else '') or None
            created = self.engine.process_reversing_schedule(as_of)
            self._load_reversing_queue()
            self._load_cycle_status()
            messagebox.showinfo("Completed", f"Posted {len(created)} reversing entr(ies)")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to complete reversing schedule: {e}")

    # --------------------- Export Tab ---------------------
    def _build_export_tab(self) -> None:
        frame = self.tab_export
        wrapper = ttk.Labelframe(frame, text="Export Options", style="Techfix.TLabelframe")
        wrapper.pack(fill=tk.X, padx=12, pady=12)

        for col in range(2):
            wrapper.columnconfigure(col, weight=1)

        buttons = [
            ("Export Journal (Excel)", self._export_journal),
            ("Export Ledger (Excel)", self._export_ledger),
            ("Export Trial Balance (Excel)", self._export_tb),
            ("Export Financials (Excel)", self._export_fs),
            ("Export All (Excel)", self._export_all_to_excel),
            ("Export Documentation (PDF)", self._export_program_docs_pdf),
        ]

        for idx, (label, command) in enumerate(buttons):
            r, c = divmod(idx, 2)
            ttk.Button(wrapper, text=label, command=command, style="Techfix.TButton").grid(
                row=r, column=c, padx=8, pady=8, sticky="ew"
            )

    def _export_journal(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")])
        if not path:
            return
        rows = db.fetch_journal(period_id=self.engine.current_period_id, conn=self.engine.conn)
        headers = ["date","entry_id","description","code","name","debit","credit"]
        try:
            from openpyxl import Workbook
            from openpyxl.utils import get_column_letter
            from openpyxl.styles import Font

            wb = Workbook()
            ws = wb.active
            ws.title = "Journal"

            for cidx, h in enumerate(headers, start=1):
                ws.cell(row=1, column=cidx, value=h).font = Font(bold=True)

            for ridx, r in enumerate(rows, start=2):
                ws.cell(row=ridx, column=1, value=r["date"])
                ws.cell(row=ridx, column=2, value=r["entry_id"])
                ws.cell(row=ridx, column=3, value=r["description"])
                ws.cell(row=ridx, column=4, value=r["code"])
                ws.cell(row=ridx, column=5, value=r["name"])
                try:
                    ws.cell(row=ridx, column=6, value=float(r["debit"] or 0))
                except Exception:
                    ws.cell(row=ridx, column=6, value=r["debit"])
                try:
                    ws.cell(row=ridx, column=7, value=float(r["credit"] or 0))
                except Exception:
                    ws.cell(row=ridx, column=7, value=r["credit"])

            last = ws.max_row
            # Add SUM formulas for debit (col 6) and credit (col 7) if there are data rows
            if last >= 2:
                col_f = get_column_letter(6)
                col_g = get_column_letter(7)
                total_row = last + 1
                ws.cell(row=total_row, column=5, value="Totals:").font = Font(bold=True)
                ws.cell(row=total_row, column=6, value=f"=SUM({col_f}2:{col_f}{last})")
                ws.cell(row=total_row, column=7, value=f"=SUM({col_g}2:{col_g}{last})")

            # auto-width
            for i in range(1, len(headers) + 1):
                ws.column_dimensions[get_column_letter(i)].width = 15

            wb.save(path)
            messagebox.showinfo("Exported", "Journal exported to Excel.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_ledger(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")])
        if not path:
            return
        rows = db.fetch_ledger(period_id=self.engine.current_period_id, conn=self.engine.conn)
        headers = ["code","name","date","description","debit","credit"]
        try:
            from openpyxl import Workbook
            from openpyxl.utils import get_column_letter
            from openpyxl.styles import Font

            wb = Workbook()
            ws = wb.active
            ws.title = "Ledger"

            for cidx, h in enumerate(headers, start=1):
                ws.cell(row=1, column=cidx, value=h).font = Font(bold=True)

            for ridx, r in enumerate(rows, start=2):
                ws.cell(row=ridx, column=1, value=r["code"]) if "code" in r.keys() else ws.cell(row=ridx, column=1, value="")
                ws.cell(row=ridx, column=2, value=r["name"]) if "name" in r.keys() else ws.cell(row=ridx, column=2, value="")
                ws.cell(row=ridx, column=3, value=r["date"]) if "date" in r.keys() else ws.cell(row=ridx, column=3, value="")
                ws.cell(row=ridx, column=4, value=r["description"]) if "description" in r.keys() else ws.cell(row=ridx, column=4, value="")
                try:
                    ws.cell(row=ridx, column=5, value=float(r["debit"] or 0))
                except Exception:
                    ws.cell(row=ridx, column=5, value=r["debit"] if "debit" in r.keys() else "")
                try:
                    ws.cell(row=ridx, column=6, value=float(r["credit"] or 0))
                except Exception:
                    ws.cell(row=ridx, column=6, value=r["credit"] if "credit" in r.keys() else "")

            last = ws.max_row
            if last >= 2:
                col_e = get_column_letter(5)
                col_f = get_column_letter(6)
                total_row = last + 1
                ws.cell(row=total_row, column=4, value="Totals:").font = Font(bold=True)
                ws.cell(row=total_row, column=5, value=f"=SUM({col_e}2:{col_e}{last})")
                ws.cell(row=total_row, column=6, value=f"=SUM({col_f}2:{col_f}{last})")

            for i in range(1, len(headers) + 1):
                ws.column_dimensions[get_column_letter(i)].width = 15

            wb.save(path)
            messagebox.showinfo("Exported", "Ledger exported to Excel.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_tb(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")])
        if not path:
            return
        rows = db.compute_trial_balance(period_id=self.engine.current_period_id, conn=self.engine.conn)
        # derive debit/credit
        headers = ["code","name","debit","credit"]
        try:
            from openpyxl import Workbook
            from openpyxl.utils import get_column_letter
            from openpyxl.styles import Font

            wb = Workbook()
            ws = wb.active
            ws.title = "Trial Balance"
            for cidx, h in enumerate(headers, start=1):
                ws.cell(row=1, column=cidx, value=h).font = Font(bold=True)

            for ridx, r in enumerate(rows, start=2):
                d, c = self._balance_to_columns(r)
                ws.cell(row=ridx, column=1, value=r["code"] if "code" in r.keys() else "")
                ws.cell(row=ridx, column=2, value=r["name"] if "name" in r.keys() else "")
                ws.cell(row=ridx, column=3, value=float(d or 0))
                ws.cell(row=ridx, column=4, value=float(c or 0))

            last = ws.max_row
            if last >= 2:
                col_c = get_column_letter(3)
                col_d = get_column_letter(4)
                total_row = last + 1
                ws.cell(row=total_row, column=2, value="Totals:").font = Font(bold=True)
                ws.cell(row=total_row, column=3, value=f"=SUM({col_c}2:{col_c}{last})")
                ws.cell(row=total_row, column=4, value=f"=SUM({col_d}2:{col_d}{last})")

            for i in range(1, len(headers) + 1):
                ws.column_dimensions[get_column_letter(i)].width = 15

            wb.save(path)
            messagebox.showinfo("Exported", "Trial balance exported to Excel.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_fs(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", 
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"financial_statements_{self.fs_date_to.get() or 'report'}.xlsx"
        )
        if not path:
            return
            
        try:
            # Get the content from all financial statement tabs
            statements = []
            
            # Get Income Statement
            self.income_text.config(state=tk.NORMAL)
            income_content = self.income_text.get("1.0", tk.END).splitlines()
            self.income_text.config(state=tk.DISABLED)
            if any(line.strip() for line in income_content):
                statements.append(("Income Statement", income_content))
            
            # Get Balance Sheet
            self.balance_sheet_text.config(state=tk.NORMAL)
            balance_content = self.balance_sheet_text.get("1.0", tk.END).splitlines()
            self.balance_sheet_text.config(state=tk.DISABLED)
            if any(line.strip() for line in balance_content):
                statements.append(("Balance Sheet", balance_content))
            
            # Get Cash Flow Statement if available
            if hasattr(self, 'cash_flow_text'):
                self.cash_flow_text.config(state=tk.NORMAL)
                cash_flow_content = self.cash_flow_text.get("1.0", tk.END).splitlines()
                self.cash_flow_text.config(state=tk.DISABLED)
                if any(line.strip() for line in cash_flow_content):
                    statements.append(("Cash Flow", cash_flow_content))
            
            if not statements:
                messagebox.showinfo("No Data", "No financial statement data available to export.")
                return
            
            # Create Excel workbook with multiple sheets
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment
            from openpyxl.utils import get_column_letter
            
            wb = Workbook()
            
            # Remove default sheet if not needed
            if statements:
                wb.remove(wb.active)
            
            # Add each statement as a separate sheet
            for sheet_name, lines in statements:
                ws = wb.create_sheet(title=sheet_name[:31])  # Excel sheet name max 31 chars
                
                # Add header with formatting
                header = ws.cell(row=1, column=1, value=sheet_name)
                header.font = Font(bold=True, size=14)
                ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
                ws.row_dimensions[1].height = 24
                
                # Add content
                for row_idx, line in enumerate(lines, start=3):  # Start from row 3 to leave space for header
                    if not line.strip():
                        continue
                    ws.cell(row=row_idx, column=1, value=line)
                
                # Auto-adjust column width
                for col in ws.columns:
                    if not col:
                        continue  # Skip empty columns
                        
                    max_length = 0
                    try:
                        # Get the column letter from the first cell in the column
                        column_letter = col[0].column_letter
                        
                        # Find the maximum content length in the column
                        for cell in col:
                            try:
                                if cell.value and len(str(cell.value).strip()) > max_length:
                                    max_length = len(str(cell.value).strip())
                            except:
                                pass
                                
                        # Set column width with some padding and a maximum
                        if max_length > 0:
                            adjusted_width = (max_length + 2) * 1.2
                            ws.column_dimensions[column_letter].width = min(adjusted_width, 50)  # Cap at 50
                    except (IndexError, AttributeError) as e:
                        print(f"Warning: Could not adjust column width: {e}")
            
            # Save the workbook
            wb.save(path)
            messagebox.showinfo("Export Successful", "Financial statements exported to Excel successfully!")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export financial statements: {str(e)}")
            raise

    def _export_all_to_excel(self) -> None:
        """Export Journal, Ledger, Trial Balance, and Financial Statements into one Excel workbook."""
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"techfix_export_{datetime.now().date().isoformat()}.xlsx",
        )
        if not path:
            return

        try:
            try:
                from openpyxl import Workbook
                from openpyxl.utils import get_column_letter
                from openpyxl.styles import Font
            except ImportError as e:
                raise RuntimeError("openpyxl is required for Excel export. Install with: pip install openpyxl") from e

            wb = Workbook()

            # --- Journal sheet ---
            ws_j = wb.active
            ws_j.title = "Journal"
            journal_rows = db.fetch_journal(period_id=self.engine.current_period_id, conn=self.engine.conn)
            j_headers = ["entry_id", "date", "description", "code", "name", "debit", "credit"]
            for cidx, h in enumerate(j_headers, start=1):
                cell = ws_j.cell(row=1, column=cidx, value=h)
                cell.font = Font(bold=True)
            for ridx, r in enumerate(journal_rows, start=2):
                ws_j.cell(row=ridx, column=1, value=r["entry_id"])
                ws_j.cell(row=ridx, column=2, value=r["date"])
                ws_j.cell(row=ridx, column=3, value=r["description"])
                ws_j.cell(row=ridx, column=4, value=r["code"])
                ws_j.cell(row=ridx, column=5, value=r["name"])
                # numeric values
                try:
                    ws_j.cell(row=ridx, column=6, value=float(r["debit"] or 0))
                except Exception:
                    ws_j.cell(row=ridx, column=6, value=r["debit"])
                try:
                    ws_j.cell(row=ridx, column=7, value=float(r["credit"] or 0))
                except Exception:
                    ws_j.cell(row=ridx, column=7, value=r["credit"])

            # Add totals row for journal debit/credit
            last = ws_j.max_row
            if last >= 2:
                fcol = get_column_letter(6)
                gcol = get_column_letter(7)
                total_row = last + 1
                ws_j.cell(row=total_row, column=5, value="Totals:").font = Font(bold=True)
                ws_j.cell(row=total_row, column=6, value=f"=SUM({fcol}2:{fcol}{last})")
                ws_j.cell(row=total_row, column=7, value=f"=SUM({gcol}2:{gcol}{last})")

            # Auto-width
            for i, _ in enumerate(j_headers, start=1):
                ws_j.column_dimensions[get_column_letter(i)].width = 15

            # --- Ledger sheet ---
            ws_l = wb.create_sheet(title="Ledger")
            l_headers = ["account_id", "code", "name", "date", "description", "debit", "credit"]
            for cidx, h in enumerate(l_headers, start=1):
                cell = ws_l.cell(row=1, column=cidx, value=h)
                cell.font = Font(bold=True)
            ledger_rows = db.fetch_ledger(period_id=self.engine.current_period_id, conn=self.engine.conn)
            for ridx, r in enumerate(ledger_rows, start=2):
                # r is a sqlite3.Row; access fields by key with safety checks
                if "account_id" in r.keys():
                    ws_l.cell(row=ridx, column=1, value=r["account_id"])
                if "code" in r.keys():
                    ws_l.cell(row=ridx, column=2, value=r["code"])
                else:
                    # fallback blank
                    ws_l.cell(row=ridx, column=2, value="")
                ws_l.cell(row=ridx, column=3, value=r["name"])
                if "date" in r.keys():
                    ws_l.cell(row=ridx, column=4, value=r["date"])
                if "description" in r.keys():
                    ws_l.cell(row=ridx, column=5, value=r["description"])
                # debit/credit as numeric when possible
                try:
                    ws_l.cell(row=ridx, column=6, value=float(r["debit"] or 0))
                except Exception:
                    try:
                        ws_l.cell(row=ridx, column=6, value=r["debit"])
                    except Exception:
                        ws_l.cell(row=ridx, column=6, value="")
                try:
                    ws_l.cell(row=ridx, column=7, value=float(r["credit"] or 0))
                except Exception:
                    try:
                        ws_l.cell(row=ridx, column=7, value=r["credit"])
                    except Exception:
                        ws_l.cell(row=ridx, column=7, value="")

            # Add totals row for ledger debit/credit
            last_l = ws_l.max_row
            if last_l >= 2:
                ecol = get_column_letter(6)
                fcol = get_column_letter(7)
                total_row = last_l + 1
                ws_l.cell(row=total_row, column=5, value="Totals:").font = Font(bold=True)
                ws_l.cell(row=total_row, column=6, value=f"=SUM({ecol}2:{ecol}{last_l})")
                ws_l.cell(row=total_row, column=7, value=f"=SUM({fcol}2:{fcol}{last_l})")

            for i, _ in enumerate(l_headers, start=1):
                ws_l.column_dimensions[get_column_letter(i)].width = 15

            # --- Trial Balance sheet ---
            ws_tb = wb.create_sheet(title="Trial Balance")
            tb_headers = ["code", "name", "debit", "credit"]
            for cidx, h in enumerate(tb_headers, start=1):
                cell = ws_tb.cell(row=1, column=cidx, value=h)
                cell.font = Font(bold=True)
            tb_rows = db.compute_trial_balance(period_id=self.engine.current_period_id, conn=self.engine.conn)
            for ridx, r in enumerate(tb_rows, start=2):
                d, c = self._balance_to_columns(r)
                ws_tb.cell(row=ridx, column=1, value=r["code"] if "code" in r.keys() else "")
                ws_tb.cell(row=ridx, column=2, value=r["name"] if "name" in r.keys() else "")
                ws_tb.cell(row=ridx, column=3, value=float(d or 0))
                ws_tb.cell(row=ridx, column=4, value=float(c or 0))
            # Add totals row for trial balance
            last_tb = ws_tb.max_row
            if last_tb >= 2:
                ccol = get_column_letter(3)
                dcol = get_column_letter(4)
                total_row = last_tb + 1
                ws_tb.cell(row=total_row, column=2, value="Totals:").font = Font(bold=True)
                ws_tb.cell(row=total_row, column=3, value=f"=SUM({ccol}2:{ccol}{last_tb})")
                ws_tb.cell(row=total_row, column=4, value=f"=SUM({dcol}2:{dcol}{last_tb})")
            for i, _ in enumerate(tb_headers, start=1):
                ws_tb.column_dimensions[get_column_letter(i)].width = 15

            # --- Financial statements sheets ---
            # Income Statement
            self.income_text.config(state=tk.NORMAL)
            income_lines = self.income_text.get("1.0", tk.END).splitlines()
            self.income_text.config(state=tk.DISABLED)
            if any(line.strip() for line in income_lines):
                ws_inc = wb.create_sheet(title="Income Statement")
                for ridx, line in enumerate(income_lines, start=1):
                    ws_inc.cell(row=ridx, column=1, value=line)
                ws_inc.column_dimensions[get_column_letter(1)].width = 120

            # Balance Sheet
            self.balance_sheet_text.config(state=tk.NORMAL)
            bs_lines = self.balance_sheet_text.get("1.0", tk.END).splitlines()
            self.balance_sheet_text.config(state=tk.DISABLED)
            if any(line.strip() for line in bs_lines):
                ws_bs = wb.create_sheet(title="Balance Sheet")
                for ridx, line in enumerate(bs_lines, start=1):
                    ws_bs.cell(row=ridx, column=1, value=line)
                ws_bs.column_dimensions[get_column_letter(1)].width = 120

            # Cash Flow
            if hasattr(self, 'cash_flow_text'):
                self.cash_flow_text.config(state=tk.NORMAL)
                cf_lines = self.cash_flow_text.get("1.0", tk.END).splitlines()
                self.cash_flow_text.config(state=tk.DISABLED)
                if any(line.strip() for line in cf_lines):
                    ws_cf = wb.create_sheet(title="Cash Flow")
                    for ridx, line in enumerate(cf_lines, start=1):
                        ws_cf.cell(row=ridx, column=1, value=line)
                    ws_cf.column_dimensions[get_column_letter(1)].width = 120

            # Save workbook
            wb.save(path)
            messagebox.showinfo("Export Successful", f"All data exported to {path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export all data: {str(e)}")
            raise

    def _export_program_docs_pdf(self) -> None:
        """Generate a PDF with program documentation (overview, usage, modules)."""
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"techfix_documentation_{__import__('datetime').date.today().isoformat()}.pdf",
        )
        if not path:
            return
        try:
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.units import inch
                from reportlab.pdfgen import canvas
            except ImportError as e:
                raise RuntimeError("reportlab is required for PDF export. Install with: pip install reportlab") from e

            c = canvas.Canvas(path, pagesize=letter)
            width, height = letter
            margin = 0.75 * inch

            def draw_title(title: str, y: float) -> float:
                c.setFont("Helvetica-Bold", 16)
                c.drawString(margin, y, title)
                return y - 0.3 * inch

            def draw_text(lines: list[str], y: float, font="Helvetica", size=10) -> float:
                c.setFont(font, size)
                for ln in lines:
                    if y < margin + 0.5 * inch:
                        c.showPage(); y = height - margin
                        c.setFont(font, size)
                    c.drawString(margin, y, ln)
                    y -= 0.18 * inch
                return y

            from datetime import date
            y = height - margin
            y = draw_title("TechFix Documentation", y)
            c.setFont("Helvetica", 10)
            c.drawString(margin, y, f"Generated: {date.today().isoformat()}")
            y -= 0.3 * inch

            # Overview
            y = draw_title("Overview", y)
            overview = [
                "TechFix is a desktop accounting practice app (Tkinter + SQLite).",
                "It guides users through the 10-step accounting cycle and produces statements.",
            ]
            y = draw_text(overview, y)

            # Features
            y = draw_title("Key Features", y)
            features = [
                "• Journalization, Ledger, Trial Balance (adjusted/unadjusted)",
                "• Financial Statements (Income Statement, Balance Sheet, Cash Flow)",
                "• Closing and Post-Closing Trial Balance, Reversing Schedule",
                "• Exports: Journal/Ledger/TB/Financials to Excel; All-in-one workbook",
                "• Configurable data directory via TECHFIX_DATA_DIR",
            ]
            y = draw_text(features, y)

            # Modules
            y = draw_title("Modules", y)
            mods = [
                "• techfix/db.py – schema, queries, trial balance, exports",
                "• techfix/accounting.py – orchestration, cycle status, closing/reversing",
                "• techfix/gui.py – Tkinter UI, tabs, theme, exports",
                "• main.py – entry point",
            ]
            y = draw_text(mods, y)

            # Usage
            y = draw_title("Usage", y)
            usage = [
                "Run: python -m techfix or python TECHFIX/TECHFIX/main.py",
                "Configure DB location: set TECHFIX_DATA_DIR to a writable folder",
                "Use the Transactions tab to record entries; Refresh Cycle to update views",
                "Use Export tab for Excel and Documentation outputs",
            ]
            y = draw_text(usage, y)

            # Current Period & Cycle
            try:
                pid = int(self.engine.current_period_id or 0)
                y = draw_title("Current Period", y)
                cp = self.engine.current_period or {}
                cp_lines = [
                    f"• Name: {cp.get('name','')}",
                    f"• Start: {cp.get('start_date','')}  End: {cp.get('end_date','')}  Closed: {cp.get('is_closed',0)}",
                ]
                y = draw_text(cp_lines, y)
                y = draw_title("Cycle Status", y)
                rows = self.engine.get_cycle_status()
                cyc_lines = [f"• {int(r['step'])}. {r['step_name']}: {r['status']}" for r in rows]
                y = draw_text(cyc_lines or ["• (no data)"], y)
            except Exception:
                pass

            y = draw_title("Workflow", y)
            wf_lines = [
                "1. Record transactions in the Transactions pane (debits/credits).",
                "2. Use Refresh Cycle to update Journal, Ledger and Trial Balance.",
                "3. Generate Financial Statements and review the accounting equation.",
                "4. Make Closing Entries, prepare Post‑Closing TB, schedule reversals.",
                "5. Export reports (Excel) and documentation (PDF) from the Export tab.",
            ]
            y = draw_text(wf_lines, y)

            y = draw_title("Equations & Treatment", y)
            eq_lines = [
                "• Income Statement: Net Income = Revenues − Expenses.",
                "• Owner’s Equity Statement: Ending Capital = Beginning Capital + Net Income − Withdrawals.",
                "• Balance Sheet: Assets = Liabilities + Ending Owner’s Equity.",
                "• Contra‑assets reduce total assets (e.g., accumulated depreciation).",
                "• Trial Balance displays net debit/credit by account based on normal side.",
            ]
            y = draw_text(eq_lines, y)

            # Trial Balance Totals
            try:
                y = draw_title("Trial Balance Totals", y)
                inc_temp_bs = True
                try:
                    statuses = self.engine.get_cycle_status()
                    step8 = next((r for r in statuses if int(r['step']) == 8), None)
                    if step8 and (step8['status'] == 'completed'):
                        inc_temp_bs = False
                except Exception:
                    pass
                tb_rows = db.compute_trial_balance(include_temporary=inc_temp_bs, period_id=self.engine.current_period_id, conn=self.engine.conn)
                total_d = 0.0
                total_c = 0.0
                for r in tb_rows:
                    d_amt, c_amt = self._balance_to_columns(r)
                    total_d += float(d_amt or 0)
                    total_c += float(c_amt or 0)
                y = draw_text([f"• Total Debit: {total_d:,.2f}", f"• Total Credit: {total_c:,.2f}"], y)
            except Exception:
                pass

            # Config & Paths
            try:
                y = draw_title("Config", y)
                from pathlib import Path
                data_dir = str(db.DB_DIR.resolve())
                db_path = str(db.DB_PATH.resolve())
                y = draw_text([f"• TECHFIX_DATA_DIR: {data_dir}", f"• Database: {db_path}"], y)
            except Exception:
                pass

            # Read README.md if available and append
            try:
                from pathlib import Path
                readme = Path(__file__).resolve().parents[2] / "README.md"
                if readme.exists():
                    y = draw_title("README Summary", y)
                    # Take first ~40 non-empty lines
                    lines = [ln.strip() for ln in readme.read_text(encoding="utf-8").splitlines() if ln.strip()][:40]
                    y = draw_text(lines, y)
            except Exception:
                pass

            c.showPage(); c.save()
            messagebox.showinfo("Exported", f"Documentation exported to PDF: {path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export documentation: {e}")

    # --------------------- Shared helpers ---------------------
    def _load_all_views(self) -> None:
        self._load_cycle_status()
        if hasattr(self, 'journal_tree'):
            self._load_journal_entries()
        if hasattr(self, 'ledger_tree'):
            self._load_ledger_entries()
        if hasattr(self, 'trial_tree'):
            self._load_trial_balances()
        try:
            self._load_postclosing_tb()
        except Exception:
            pass
        # Load financials without changing cycle step statuses during startup
        self._load_financials(mark_status=False)
        self._load_adjustments()
        self._load_closing_preview()
        self._load_reversing_queue()
        try:
            self._load_recent_transactions()
        except Exception:
            pass

    def _refresh_after_post(self) -> None:
        self._load_journal_entries()
        self._load_ledger_entries()
        self._load_trial_balances()
        self._load_postclosing_tb()
        self._load_cycle_status()
        self._load_adjustments()
        self._load_closing_preview()
        self._load_reversing_queue()
        try:
            self._load_recent_transactions()
        except Exception:
            pass

    def _load_postclosing_tb(self) -> None:
        if not hasattr(self, 'pctb_tree'):
            return
        for item in self.pctb_tree.get_children():
            self.pctb_tree.delete(item)
        try:
            as_of = (self.pctb_date.get().strip() if hasattr(self, 'pctb_date') else '') or None
            rows = db.compute_trial_balance(up_to_date=as_of, include_temporary=False, period_id=self.engine.current_period_id, conn=self.engine.conn)
            # Only show accounts with non-zero balances in post-closing snapshot
            def _has_activity_pc(r: dict) -> bool:
                d, c = self._balance_to_columns(r)
                return bool((d or 0) != 0 or (c or 0) != 0)
            rows = [r for r in rows if _has_activity_pc(r)]
            for r in rows:
                code = r['code'] if 'code' in r.keys() else ''
                name = r['name'] if 'name' in r.keys() else ''
                d, c = self._balance_to_columns(r)
                self.pctb_tree.insert('', 'end', values=(code, name, f"{d:,.2f}" if d else '', f"{c:,.2f}" if c else ''))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load post-closing TB: {e}")

    def _complete_postclosing_tb_action(self) -> None:
        try:
            as_of = (self.pctb_date.get().strip() if hasattr(self, 'pctb_date') else '') or None
            rows = db.compute_trial_balance(up_to_date=as_of, include_temporary=False, period_id=self.engine.current_period_id, conn=self.engine.conn)
            self._load_postclosing_tb()
            self.engine.capture_trial_balance_snapshot("post_closing", as_of or "latest", rows)
            self.engine.set_cycle_step_status(9, "completed", f"Post-closing TB prepared as of {as_of or 'latest'}")
            self.engine.set_cycle_step_status(10, "in_progress", "Schedule reversing entries pending")
            self._load_cycle_status()
            messagebox.showinfo("Completed", "Post-closing trial balance marked completed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to complete post-closing TB: {e}")


if __name__ == "__main__":
    app = TechFixApp()
    app.mainloop()
