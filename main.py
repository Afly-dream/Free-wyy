# -*- coding: utf-8 -*-
"""
应用程序主入口
"""
import sys
from PyQt6.QtWidgets import QApplication

# 将 'MAX' 目录的父目录添加到 sys.path
# 这允许我们使用 'from app.main_window import MainWindow' 这样的绝对导入
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main_window import MainWindow, load_stylesheet

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 加载样式表
    load_stylesheet(app)
    
    # 创建并显示主窗口
    main_win = MainWindow()
    main_win.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 