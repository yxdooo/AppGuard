import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, CardWidget, BodyLabel, 
    PrimaryPushButton, ListWidget, FluentIcon as FIF,
    Action, RoundMenu
)
from ui.password_dialog import _get_exe_icon
from core.i18n import t

class AppLockInterface(ScrollArea):
    app_added = pyqtSignal(str, str) # name, exe_path
    app_removed = pyqtSignal(str) # app_id
    app_selected = pyqtSignal(str) # app_id

    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("AppLockInterface")
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
        
        # Header
        headerLayout = QHBoxLayout()
        self.titleLabel = SubtitleLabel(t("tab_apps"), self.view)
        headerLayout.addWidget(self.titleLabel)
        
        self.addBtn = PrimaryPushButton(FIF.ADD, t("btn_add_app"), self.view)
        self.addBtn.clicked.connect(self._on_add_app)
        headerLayout.addWidget(self.addBtn, 0, Qt.AlignmentFlag.AlignRight)
        
        self.vBoxLayout.addLayout(headerLayout)
        
        # List
        self.appList = ListWidget(self.view)
        self.appList.itemClicked.connect(self._on_item_clicked)
        self.appList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.appList.customContextMenuRequested.connect(self._show_context_menu)
        self.vBoxLayout.addWidget(self.appList)

    def load_apps(self, apps_dict):
        self.appList.clear()
        for app_id, app in apps_dict.items():
            from PyQt6.QtWidgets import QListWidgetItem
            from PyQt6.QtCore import QSize
            name = app.get("name", "?")
            exe = app.get("exe_path", "")
            item = QListWidgetItem(f"  {name}\n  {os.path.basename(exe)}")
            item.setData(Qt.ItemDataRole.UserRole, app_id)
            item.setIcon(_get_exe_icon(exe, 32))
            item.setSizeHint(QSize(0, 56))
            self.appList.addItem(item)

    def _on_add_app(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Application", "C:\\Program Files", "Executable (*.exe)")
        if path:
            name = os.path.basename(path).replace(".exe", "")
            self.app_added.emit(name, path)

    def _on_item_clicked(self, item):
        app_id = item.data(Qt.ItemDataRole.UserRole)
        self.app_selected.emit(app_id)

    def _show_context_menu(self, pos):
        item = self.appList.itemAt(pos)
        if not item: return
        
        app_id = item.data(Qt.ItemDataRole.UserRole)
        menu = RoundMenu(parent=self)
        
        delete_action = Action(FIF.DELETE, t("btn_remove"))
        delete_action.triggered.connect(lambda: self.app_removed.emit(app_id))
        
        menu.addAction(delete_action)
        menu.exec(self.appList.mapToGlobal(pos))
