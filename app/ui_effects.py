from PyQt6.QtWidgets import (QWidget, QFrame, QGraphicsDropShadowEffect, 
                            QGraphicsBlurEffect, QLabel, QPushButton, QLineEdit,
                            QTextEdit, QTableWidget, QProgressBar, QSpinBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QLinearGradient, QBrush

class ModernFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        from PyQt6.QtCore import QRectF
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 15, 15)

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(40, 40, 50, 220))
        gradient.setColorAt(1, QColor(30, 30, 40, 200))

        painter.fillPath(path, QBrush(gradient))

        painter.setPen(QColor(100, 100, 120, 180))
        painter.drawPath(path)

class BlurredBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(20, 25, 35, 255))
        gradient.setColorAt(0.5, QColor(25, 30, 40, 255))
        gradient.setColorAt(1, QColor(30, 35, 45, 255))
        
        painter.fillRect(self.rect(), QBrush(gradient))

class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(60, 70, 80, 200);
                color: #ffffff;
                border: 2px solid rgba(100, 120, 140, 180);
                border-radius: 10px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(80, 90, 100, 220);
                border: 2px solid rgba(120, 140, 160, 200);
            }
            QPushButton:pressed {
                background: rgba(40, 50, 60, 180);
            }
            QPushButton:disabled {
                background: rgba(50, 50, 50, 150);
                color: rgba(150, 150, 150, 180);
                border: 2px solid rgba(80, 80, 80, 120);
            }
        """)
        
        self.scale_animation = QPropertyAnimation(self, b"geometry")
        self.scale_animation.setDuration(100)
        self.scale_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def enterEvent(self, event):
        super().enterEvent(event)
        current_rect = self.geometry()
        expanded_rect = QRect(
            current_rect.x() - 2,
            current_rect.y() - 2,
            current_rect.width() + 4,
            current_rect.height() + 4
        )
        self.scale_animation.setStartValue(current_rect)
        self.scale_animation.setEndValue(expanded_rect)
        self.scale_animation.start()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        current_rect = self.geometry()
        normal_rect = QRect(
            current_rect.x() + 2,
            current_rect.y() + 2,
            current_rect.width() - 4,
            current_rect.height() - 4
        )
        self.scale_animation.setStartValue(current_rect)
        self.scale_animation.setEndValue(normal_rect)
        self.scale_animation.start()

class ModernLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLineEdit {
                background: rgba(50, 60, 70, 200);
                color: #ffffff;
                border: 2px solid rgba(80, 90, 100, 180);
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid rgba(0, 150, 255, 200);
                background: rgba(60, 70, 80, 220);
            }
        """)

class ModernTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QTextEdit {
                background: rgba(50, 60, 70, 200);
                color: #ffffff;
                border: 2px solid rgba(80, 90, 100, 180);
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 2px solid rgba(0, 150, 255, 200);
                background: rgba(60, 70, 80, 220);
            }
        """)

class ModernTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QTableWidget {
                background: rgba(45, 55, 65, 220);
                color: #ffffff;
                border: 2px solid rgba(80, 90, 100, 180);
                border-radius: 8px;
                gridline-color: rgba(80, 90, 100, 120);
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(80, 90, 100, 120);
            }
            QTableWidget::item:selected {
                background: rgba(0, 120, 200, 150);
            }
            QHeaderView::section {
                background: rgba(60, 70, 80, 200);
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

class ModernProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                background: rgba(50, 60, 70, 200);
                border: 2px solid rgba(80, 90, 100, 180);
                border-radius: 8px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4ff, stop:1 #ff1493);
                border-radius: 6px;
            }
        """)

class ModernSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QSpinBox {
                background: rgba(50, 60, 70, 200);
                color: #ffffff;
                border: 2px solid rgba(80, 90, 100, 180);
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
            QSpinBox:focus {
                border: 2px solid rgba(0, 150, 255, 200);
                background: rgba(60, 70, 80, 220);
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: rgba(70, 80, 90, 200);
                border: none;
                border-radius: 4px;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: rgba(90, 100, 110, 220);
            }
        """)

class ModernLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background: transparent;
                font-weight: bold;
            }
        """)
