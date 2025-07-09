import sys
import os
import atexit
import subprocess
import threading
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from app.main_window import MainWindow

def create_normal_exit_flag():
    with open("normal_exit.flag", "w") as f:
        f.write("normal")

def remove_normal_exit_flag():
    try:
        if os.path.exists("normal_exit.flag"):
            os.remove("normal_exit.flag")
    except:
        pass

def start_crash_monitor():
    try:
        # 检查是否已经有监控程序在运行
        if os.path.exists("monitor_running.flag"):
            return

        # 创建监控运行标志
        with open("monitor_running.flag", "w") as f:
            f.write("running")

        # 启动监控程序
        subprocess.Popen([sys.executable, "crash_monitor.py"],
                        cwd=os.getcwd(),
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except Exception:
        pass

def cleanup_monitor_flag():
    try:
        if os.path.exists("monitor_running.flag"):
            os.remove("monitor_running.flag")
    except:
        pass

def main():
    # 检查是否是被监控程序启动的
    is_monitored = "--monitored" in sys.argv

    if not is_monitored:
        # 启动崩溃监控程序
        monitor_thread = threading.Thread(target=start_crash_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(0.2)  # 给监控程序一点启动时间

    remove_normal_exit_flag()
    atexit.register(create_normal_exit_flag)
    atexit.register(cleanup_monitor_flag)

    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    main_win = MainWindow()
    main_win.show()

    try:
        result = app.exec()
        sys.exit(result)
    except Exception as e:
        remove_normal_exit_flag()
        cleanup_monitor_flag()
        raise e

if __name__ == '__main__':
    main()
