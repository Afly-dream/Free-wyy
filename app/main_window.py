# -*- coding: utf-8 -*-
"""
应用主窗口 (QMainWindow)，负责组装所有UI组件
"""
import sys
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QApplication
from PyQt6.QtCore import QFile

from .scanner_tab import ScannerTab
from .analyzer_tab import AnalyzerTab

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MAX-超级工具集")
        self.setGeometry(100, 100, 1200, 800)

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 创建标签页
        self.scanner_tab = ScannerTab()
        self.analyzer_tab = AnalyzerTab()

        # 添加标签页
        self.tabs.addTab(self.scanner_tab, "链接扫描器")
        self.tabs.addTab(self.analyzer_tab, "链接分析器")

    def setup_connections(self):
        """设置跨标签页的信号和槽连接"""
        self.scanner_tab.send_vip_button.clicked.connect(self.send_vip_links_to_analyzer)
        self.scanner_tab.send_gift_button.clicked.connect(self.send_gift_links_to_analyzer)
    
    def send_vip_links_to_analyzer(self):
        """获取扫描器中选中的VIP链接并发送到分析器"""
        selected_links = self.scanner_tab.get_selected_links('vip')
        if selected_links:
            self.analyzer_tab.add_links_to_input('VIP', selected_links)
            self.tabs.setCurrentWidget(self.analyzer_tab) # 自动切换到分析器标签页

    def send_gift_links_to_analyzer(self):
        """获取扫描器中选中的礼品链接并发送到分析器"""
        selected_links = self.scanner_tab.get_selected_links('gift')
        if selected_links:
            self.analyzer_tab.add_links_to_input('礼品', selected_links)
            self.tabs.setCurrentWidget(self.analyzer_tab) # 自动切换到分析器标签页

    def closeEvent(self, event):
        """确保在关闭主窗口时，所有后台线程都能被正确处理"""
        # 调用子控件的closeEvent，确保线程被关闭
        self.scanner_tab.closeEvent(event)
        # 分析器标签页的线程是在需要时才创建，并且通常运行时间较短，
        # 但为保险起见，也应添加类似的逻辑（如果需要长时间运行）
        # self.analyzer_tab.closeEvent(event) 
        super().closeEvent(event)

def load_stylesheet(app):
    """加载QSS样式表"""
    try:
        # 在正常的Python环境中，可以使用相对路径
        # 在PyInstaller打包后，sys._MEIPASS是包含资源的临时文件夹
        base_path = getattr(sys, '_MEIPASS', '.')
        style_path = f"{base_path}/ui/style.qss"
        
        file = QFile(style_path)
        if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = file.readAll()
            app.setStyleSheet(stream.data().decode("utf-8"))
            print("样式表加载成功。")
            return True
    except Exception as e:
        print(f"无法加载样式表: {e}")
    return False 