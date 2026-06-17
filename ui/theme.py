"""
ui/theme.py — Dynamic QSS theme generator
Generates complete UI style based on selected color accent.
"""

# For each theme: (main color, dark, darker)
ACCENT_COLORS: dict[str, tuple[str, str, str]] = {
    "purple": ("#7c3aed", "#6d28d9", "#5b21b6"),
    "blue":   ("#2563eb", "#1d4ed8", "#1e40af"),
    "red":    ("#e11d48", "#be123c", "#9f1239"),
    "green":  ("#16a34a", "#15803d", "#166534"),
    "orange": ("#ea580c", "#c2410c", "#9a3412"),
}

_current = "purple"


def set_accent(name: str) -> None:
    global _current
    if name in ACCENT_COLORS:
        _current = name


def get_accent() -> str:
    return _current


def get_accent_color() -> str:
    return ACCENT_COLORS[_current][0]


def get_style(inner_bg: str = "#0d0d1a") -> str:
    a, d, dd = ACCENT_COLORS[_current]
    return f"""
/* ── General ── */
QMainWindow, QWidget {{ background: {inner_bg}; color: #e2e8f0;
    font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }}
QDialog {{ background: #0f0f23; }}

/* ── Tab ── */
QTabWidget::pane {{ border: 1px solid #2d2d50; border-radius: 10px;
    background: #13132a; margin-top: -1px; }}
QTabBar::tab {{ background: #1a1a2e; color: #64748b; padding: 10px 22px;
    border: 1px solid #2d2d50; border-bottom: none;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    margin-right: 3px; font-weight: 600; }}
QTabBar::tab:selected {{ background: {a}; color: white; border-color: {a}; }}
QTabBar::tab:hover:!selected {{ background: #1e1e38; color: #94a3b8; }}

/* ── Buttons ── */
QPushButton {{ background: {a}; color: white; border: none; border-radius: 8px;
    padding: 9px 18px; font-weight: 600; font-size: 13px;
    font-family: 'Segoe UI', Arial, sans-serif; }}
QPushButton:hover {{ background: {d}; }}
QPushButton:pressed {{ background: {dd}; }}
QPushButton:disabled {{ background: #374151; color: #6b7280; }}
QPushButton[role="secondary"] {{ background: #1e1e38; color: #94a3b8; border: 1px solid #2d2d50; }}
QPushButton[role="secondary"]:hover {{ background: #2d2d50; color: #e2e8f0; }}
QPushButton[role="danger"] {{ background: #dc2626; }}
QPushButton[role="danger"]:hover {{ background: #b91c1c; }}
QPushButton[role="success"] {{ background: #16a34a; }}
QPushButton[role="success"]:hover {{ background: #15803d; }}
QPushButton[role="icon"] {{ background: #1e1e38; color: #e2e8f0;
    border: 1px solid #2d2d50; font-size: 16px; padding: 0; }}
QPushButton[role="icon"]:hover {{ background: #2d2d50; }}

/* ── List ── */
QListWidget {{ background: #13132a; border: 1px solid #1e1e38;
    border-radius: 10px; outline: none; padding: 4px; }}
QListWidget::item {{ padding: 10px 12px; border-radius: 6px; color: #cbd5e1;
    border-bottom: 1px solid #1a1a30; }}
QListWidget::item:selected {{ background: {dd}; color: #f1f5f9; }}
QListWidget::item:hover {{ background: #18182e; }}

/* ── Input ── */
QLineEdit {{ background: #1a1a2e; color: #e2e8f0; border: 2px solid #2d2d50;
    border-radius: 8px; padding: 10px 14px; font-size: 13px;
    selection-background-color: {a}; }}
QLineEdit:focus {{ border-color: {a}; }}
QLineEdit:disabled {{ background: #111122; color: #4b5563; }}

/* ── Combo ── */
QComboBox {{ background: #1a1a2e; color: #e2e8f0; border: 2px solid #2d2d50;
    border-radius: 8px; padding: 8px 12px; font-size: 13px; }}
QComboBox:focus {{ border-color: {a}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: #1a1a2e; color: #e2e8f0;
    border: 1px solid #2d2d50; selection-background-color: {a}; outline: none; }}

/* ── CheckBox ── */
QCheckBox {{ spacing: 10px; color: #94a3b8; font-size: 13px; }}
QCheckBox::indicator {{ width: 42px; height: 22px; border-radius: 11px; background: #374151; }}
QCheckBox::indicator:checked {{ background: {a}; }}

/* ── ScrollBar ── */
QScrollBar:vertical {{ background: #1a1a2e; width: 8px; }}
QScrollBar::handle:vertical {{ background: #3d3d5c; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Menu ── */
QMenu {{ background: #1a1a2e; color: #e2e8f0; border: 1px solid #2d2d50;
    border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 8px 20px; border-radius: 4px; }}
QMenu::item:selected {{ background: {a}; }}
QMenu::separator {{ background: #2d2d50; height: 1px; margin: 4px 8px; }}

/* ── Tooltip ── */
QToolTip {{ background: #1e1e38; color: #e2e8f0; border: 1px solid #3d3d5c;
    border-radius: 6px; padding: 4px 8px; }}

/* ── Frame divider ── */
QFrame[role="divider"] {{ background: #1e1e38; min-height: 1px; max-height: 1px; border: none; }}
"""
