"""
ui/mini_widget.py — Desktop Mini Widget
"""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush, QPen
from ui.theme import get_accent_color, get_style

class MiniWidget(QWidget):
    def __init__(self, config, on_open_dashboard, parent=None):
        super().__init__(parent)
        self.config = config
        self.on_open_dashboard = on_open_dashboard
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._drag_pos = None
        self._build_ui()
        self.update_stats()

    def _build_ui(self):
        self.setFixedSize(160, 80)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        
        # Top bar
        top = QHBoxLayout()
        icon = QLabel("🛡️ AppGuard")
        icon.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        top.addWidget(icon)
        top.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(16, 16)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #94a3b8; border: none; font-size: 10px; } QPushButton:hover { color: #f87171; }")
        close_btn.clicked.connect(self.hide)
        top.addWidget(close_btn)
        lay.addLayout(top)
        
        # Content
        self.stat_lbl = QLabel("0 Uygulama")
        self.stat_lbl.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        lay.addWidget(self.stat_lbl)
        
        open_btn = QPushButton("Open Panel")
        open_btn.setFixedHeight(22)
        open_btn.setStyleSheet(f"background: {get_accent_color()}; color: white; border-radius: 4px; font-size: 10px;")
        open_btn.clicked.connect(self.on_open_dashboard)
        lay.addWidget(open_btn)

    def update_stats(self):
        apps = len(self.config.get_protected_apps())
        self.stat_lbl.setText(f"{apps} Protected")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Semi-transparent background
        painter.setBrush(QBrush(QColor(15, 15, 35, 230)))
        painter.setPen(QPen(QColor(45, 45, 80), 1))
        painter.drawRoundedRect(0, 0, self.width()-1, self.height()-1, 8, 8)
        
        # Accent line
        painter.setBrush(QBrush(QColor(get_accent_color())))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 4, self.height()-1, 4, 4)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
