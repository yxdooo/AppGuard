from PyQt6.QtWidgets import QWidget, QListWidgetItem
from PyQt6.QtCore import QSize, QVBoxLayout, QHBoxLayout, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    ScrollArea, SubtitleLabel, PrimaryPushButton, ListWidget, FluentIcon as FIF,
    Action, RoundMenu
)
from core.i18n import t

class GroupsInterface(ScrollArea):
    group_added = pyqtSignal(str) # name
    group_removed = pyqtSignal(str) # group_id
    group_selected = pyqtSignal(str) # group_id

    def __init__(self, main_window, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("GroupsInterface")
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
        self.titleLabel = SubtitleLabel(t("tab_groups"), self.view)
        headerLayout.addWidget(self.titleLabel)
        
        self.addBtn = PrimaryPushButton(FIF.ADD, t("btn_add_group"), self.view)
        self.addBtn.clicked.connect(self._on_add_group)
        headerLayout.addWidget(self.addBtn, 0, Qt.AlignmentFlag.AlignRight)
        
        self.vBoxLayout.addLayout(headerLayout)
        
        self.groupList = ListWidget(self.view)
        self.groupList.itemClicked.connect(self._on_item_clicked)
        self.groupList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.groupList.customContextMenuRequested.connect(self._show_context_menu)
        self.vBoxLayout.addWidget(self.groupList)

    def load_groups(self, groups_dict):
        self.groupList.clear()
        for gid, g in groups_dict.items():
            n = len(g.get("app_ids", []))
            item = QListWidgetItem(f"  ğŸ—‚  {g['name']}  ({n} apps)")
            item.setData(Qt.ItemDataRole.UserRole, gid)
            item.setSizeHint(QSize(0, 46))
            self.groupList.addItem(item)

    def _on_add_group(self):
        text, ok = QInputDialog.getText(self, "New Group", "Group Name:")
        if ok and text:
            self.group_added.emit(text)

    def _on_item_clicked(self, item):
        gid = item.data(Qt.ItemDataRole.UserRole)
        self.group_selected.emit(gid)

    def _show_context_menu(self, pos):
        item = self.groupList.itemAt(pos)
        if not item: return
        
        gid = item.data(Qt.ItemDataRole.UserRole)
        menu = RoundMenu(parent=self)
        
        delete_action = Action(FIF.DELETE, t("btn_remove_group"))
        delete_action.triggered.connect(lambda: self.group_removed.emit(gid))
        
        menu.addAction(delete_action)
        menu.exec(self.groupList.mapToGlobal(pos))

