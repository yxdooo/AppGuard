import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, PrimaryPushButton, ListWidget, FluentIcon as FIF,
    Action, RoundMenu
)
from core.usb_detector import get_removable_drives
from core.i18n import t

class UsbInterface(ScrollArea):
    usb_removed = pyqtSignal(str) # serial
    usb_added = pyqtSignal(str, str) # serial, label

    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("UsbInterface")
        self.main_window = main_window
        
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setStyleSheet("ScrollArea {background: transparent; border: none}")
        self.view.setStyleSheet("QWidget {background: transparent}")
        
        self.vBoxLayout.setContentsMargins(36, 36, 36, 36)
        self.vBoxLayout.setSpacing(16)
        self.vBoxLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        headerLayout = QHBoxLayout()
        self.titleLabel = SubtitleLabel(t("tab_usb"), self.view)
        headerLayout.addWidget(self.titleLabel)
        
        self.addBtn = PrimaryPushButton(FIF.ADD, t("btn_add_usb"), self.view)
        self.addBtn.clicked.connect(self._on_add_usb)
        headerLayout.addWidget(self.addBtn, 0, Qt.AlignmentFlag.AlignRight)
        
        self.vBoxLayout.addLayout(headerLayout)
        
        self.usbList = ListWidget(self.view)
        self.usbList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.usbList.customContextMenuRequested.connect(self._show_context_menu)
        self.vBoxLayout.addWidget(self.usbList)

    def load_usbs(self, usb_list):
        self.usbList.clear()
        for usb in usb_list:
            from PyQt6.QtWidgets import QListWidgetItem
            from PyQt6.QtCore import QSize
            item = QListWidgetItem(f"  🔑  {usb['label']}  ({usb['serial']})")
            item.setData(Qt.ItemDataRole.UserRole, usb["serial"])
            item.setSizeHint(QSize(0, 44))
            self.usbList.addItem(item)

    def _on_add_usb(self):
        usbs = get_removable_drives()
        if not usbs:
            QMessageBox.warning(self, t("error_title"), t("usb_not_found"))
            return
            
        items = [f"{u['letter']} - {u['label']} ({u['serial']})" for u in usbs]
        choice, ok = QInputDialog.getItem(self, t("usb_select_title"), t("usb_select_lbl"), items, 0, False)
        
        if ok and choice:
            idx = items.index(choice)
            selected = usbs[idx]
            self.usb_added.emit(selected["serial"], selected["label"] or "USB Key")

    def _show_context_menu(self, pos):
        item = self.usbList.itemAt(pos)
        if not item: return
        
        serial = item.data(Qt.ItemDataRole.UserRole)
        menu = RoundMenu(parent=self)
        
        delete_action = Action(FIF.DELETE, t("btn_remove_usb"))
        delete_action.triggered.connect(lambda: self.usb_removed.emit(serial))
        
        menu.addAction(delete_action)
        menu.exec(self.usbList.mapToGlobal(pos))
