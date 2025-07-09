import sys
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                            QHBoxLayout, QApplication, QGraphicsDropShadowEffect,
                            QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QLinearGradient
from .scanner_tab import ScannerTab
from .analyzer_tab import AnalyzerTab
from .ui_effects import ModernFrame, BlurredBackground

class ModernTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: rgba(40, 50, 60, 220);
                border-radius: 15px;
            }
            QTabBar::tab {
                background: rgba(60, 70, 80, 200);
                color: #ffffff;
                padding: 12px 24px;
                margin: 2px;
                border-radius: 10px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: rgba(80, 90, 100, 240);
                color: #00d4ff;
            }
            QTabBar::tab:hover {
                background: rgba(70, 80, 90, 220);
            }
        """)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("网易云音乐链接工具集")
        self.setGeometry(100, 100, 1400, 900)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.init_ui()
        self.setup_animations()
        
    def init_ui(self):
        central_widget = BlurredBackground()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        title_frame = ModernFrame()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(20, 15, 20, 15)
        
        from PyQt6.QtWidgets import QLabel, QPushButton
        title_label = QLabel("网易云音乐链接工具集")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 0, 0, 0.7);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 0, 0, 0.9);
            }
        """)
        close_btn.clicked.connect(self.close)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        
        self.tabs = ModernTabWidget()
        
        self.scanner_tab = ScannerTab()
        self.analyzer_tab = AnalyzerTab()
        
        self.tabs.addTab(self.scanner_tab, "🔍 链接扫描器")
        self.tabs.addTab(self.analyzer_tab, "🔬 链接分析器")
        
        main_layout.addWidget(title_frame)
        main_layout.addWidget(self.tabs)
        
    def setup_animations(self):
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowOpacity(0)
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
