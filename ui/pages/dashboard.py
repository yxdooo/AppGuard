import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from qfluentwidgets import (
    FluentWindow, SubtitleLabel, setTheme, Theme, 
    FluentIcon as FIF, NavigationItemPosition, ScrollArea,
    CardWidget, BodyLabel, PrimaryPushButton
)

from core.i18n import t

class DashboardInterface(ScrollArea):
    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("DashboardInterface")
        self.main_window = main_window
        
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("ScrollArea {background: transparent; border: none}")
        self.view.setStyleSheet("QWidget {background: transparent}")
        
        self.vBoxLayout.setContentsMargins(36, 36, 36, 36)
        self.vBoxLayout.setSpacing(24)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Title
        self.titleLabel = SubtitleLabel(t("tab_dashboard"), self.view)
        self.vBoxLayout.addWidget(self.titleLabel)
        
        # Stat Cards
        self.statsLayout = QHBoxLayout()
        self.statsLayout.setSpacing(16)
        
        self.card_apps = self._create_card(t("stats_apps"), "0")
        self.card_groups = self._create_card(t("stats_groups"), "0")
        self.card_usb = self._create_card(t("stats_usb"), "0")
        
        self.statsLayout.addWidget(self.card_apps[0])
        self.statsLayout.addWidget(self.card_groups[0])
        self.statsLayout.addWidget(self.card_usb[0])
        
        self.vBoxLayout.addLayout(self.statsLayout)
        
        # Emergency Lock Button
        self.emergencyBtn = PrimaryPushButton(FIF.POWER_BUTTON, t("emergency_lock_btn"), self.view)
        self.emergencyBtn.clicked.connect(self._on_emergency_click)
        self.vBoxLayout.addWidget(self.emergencyBtn)
        self.vBoxLayout.addStretch(1)

    def _create_card(self, title, value):
        card = CardWidget(self.view)
        card.setFixedSize(200, 120)
        lay = QVBoxLayout(card)
        
        title_lbl = BodyLabel(title, card)
        val_lbl = SubtitleLabel(value, card)
        val_lbl.setStyleSheet("font-size: 32px; font-weight: bold;")
        
        lay.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignTop)
        lay.addWidget(val_lbl, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
        return card, val_lbl
        
    def _on_emergency_click(self):
        if hasattr(self.main_window, "_emergency_lock_signal"):
            self.main_window._emergency_lock_signal()

    def update_stats(self, apps_count, groups_count, usb_count):
        self.card_apps[1].setText(str(apps_count))
        self.card_groups[1].setText(str(groups_count))
        self.card_usb[1].setText(str(usb_count))
