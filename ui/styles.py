"""
ui/styles.py — AppGuard dark theme stylesheet (QSS)
"""

APP_STYLE = """
/* ── Genel ── */
QMainWindow, QDialog {
    background-color: #0d0d1a;
    color: #e2e8f0;
}
QWidget {
    background-color: #0d0d1a;
    color: #e2e8f0;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}

/* ── ScrollArea ── */
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical {
    background: #1a1a2e; width: 8px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #3d3d5c; border-radius: 4px; min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Butonlar ── */
QPushButton {
    background-color: #7c3aed;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover { background-color: #6d28d9; }
QPushButton:pressed { background-color: #5b21b6; }
QPushButton:disabled { background-color: #374151; color: #6b7280; }

QPushButton[flat="true"] {
    background: transparent;
    color: #94a3b8;
    padding: 4px 8px;
}
QPushButton[flat="true"]:hover { color: #e2e8f0; background: #1e1e38; }

QPushButton[danger="true"] {
    background-color: #dc2626;
}
QPushButton[danger="true"]:hover { background-color: #b91c1c; }

QPushButton[success="true"] {
    background-color: #16a34a;
}
QPushButton[success="true"]:hover { background-color: #15803d; }

QPushButton[secondary="true"] {
    background-color: #1e1e38;
    color: #94a3b8;
    border: 1px solid #2d2d50;
}
QPushButton[secondary="true"]:hover { background-color: #2d2d50; color: #e2e8f0; }

/* ── Input Fields ── */
QLineEdit {
    background-color: #1a1a2e;
    color: #e2e8f0;
    border: 2px solid #2d2d50;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: #7c3aed;
}
QLineEdit:focus { border-color: #7c3aed; }
QLineEdit:disabled { background-color: #111122; color: #4b5563; }

/* ── Etiketler ── */
QLabel { background: transparent; }
QLabel[title="true"] {
    font-size: 22px;
    font-weight: 700;
    color: #f1f5f9;
}
QLabel[subtitle="true"] {
    font-size: 13px;
    color: #64748b;
}
QLabel[section="true"] {
    font-size: 11px;
    font-weight: 700;
    color: #6b7280;
    letter-spacing: 1px;
}
QLabel[error="true"] { color: #f87171; }
QLabel[success="true"] { color: #4ade80; }
QLabel[warning="true"] { color: #fbbf24; }

/* ── Kart panelleri ── */
QFrame[card="true"] {
    background-color: #13132a;
    border: 1px solid #1e1e38;
    border-radius: 12px;
}
QFrame[card="true"]:hover {
    border-color: #3d3d7a;
}

/* ── Toggle (CheckBox) ── */
QCheckBox {
    spacing: 8px;
    color: #94a3b8;
}
QCheckBox::indicator {
    width: 40px; height: 22px;
    border-radius: 11px;
    background: #374151;
    border: none;
}
QCheckBox::indicator:checked { background: #7c3aed; }
QCheckBox::indicator:hover { border: 1px solid #7c3aed; }

/* ── No toolbar ── */
QMainWindow::separator { background: #1e1e38; width: 1px; }

/* ── Divider Line ── */
QFrame[line="true"] {
    background-color: #1e1e38;
    border: none;
    max-height: 1px;
    min-height: 1px;
}

/* ── Liste ── */
QListWidget {
    background: #13132a;
    border: 1px solid #1e1e38;
    border-radius: 10px;
    outline: none;
}
QListWidget::item {
    padding: 10px 14px;
    border-bottom: 1px solid #1a1a30;
    color: #cbd5e1;
}
QListWidget::item:selected {
    background: #1e1e4a;
    color: #f1f5f9;
}
QListWidget::item:hover { background: #18182e; }

/* ── Combo Box ── */
QComboBox {
    background: #1a1a2e;
    color: #e2e8f0;
    border: 2px solid #2d2d50;
    border-radius: 8px;
    padding: 8px 12px;
}
QComboBox:focus { border-color: #7c3aed; }
QComboBox QAbstractItemView {
    background: #1a1a2e;
    border: 1px solid #2d2d50;
    color: #e2e8f0;
    selection-background-color: #7c3aed;
}

/* ── ToolTip ── */
QToolTip {
    background: #1e1e38;
    color: #e2e8f0;
    border: 1px solid #3d3d5c;
    border-radius: 6px;
    padding: 4px 8px;
}
"""

# Custom style for password dialog
PASSWORD_DIALOG_STYLE = APP_STYLE + """
QDialog {
    border: 1px solid #2d2d50;
    border-radius: 16px;
}
"""
