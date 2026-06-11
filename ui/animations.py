"""
ui/animations.py — Animated tools for UI (Ripple etc.)
"""
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QPoint, QRect, QEasingCurve, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen


class RippleButton(QPushButton):
    """Button that gives a ripple effect when clicked."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._ripple_radius = 0.0
        self._ripple_center = QPoint()
        self._ripple_color = QColor(255, 255, 255, 60)
        self._anim = QPropertyAnimation(self, b"rippleRadius", self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    def rippleRadius(self):
        return self._ripple_radius

    def setRippleRadius(self, r):
        self._ripple_radius = r
        self.update()

    rippleRadius = pyqtProperty(float, rippleRadius, setRippleRadius)

    def mousePressEvent(self, event):
        self._ripple_center = event.pos()
        self._ripple_radius = 0
        w, h = self.width(), self.height()
        max_radius = ((w ** 2) + (h ** 2)) ** 0.5
        self._anim.setStartValue(0)
        self._anim.setEndValue(max_radius)
        self._anim.start()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._ripple_radius > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setClipRect(self.rect())
            painter.setBrush(QBrush(self._ripple_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self._ripple_center, int(self._ripple_radius), int(self._ripple_radius))


class SidebarBtn(QPushButton):
    """Navigation button for the left menu."""

    def __init__(self, icon_str, text, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setText(f" {icon_str}   {text}")
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Style will be applied via qss
