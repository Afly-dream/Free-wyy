import sys
import os
import subprocess
import threading
import time

def start_crash_monitor():
    try:
        subprocess.run([sys.executable, "crash_monitor.py"], 
                      cwd=os.getcwd(),
                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except Exception as e:
        print(f"Failed to start crash monitor: {e}")

def main():
    print("启动网易云音乐链接工具集...")
    
    monitor_thread = threading.Thread(target=start_crash_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    time.sleep(0.5)
    
    try:
        subprocess.run([sys.executable, "main.py"], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序启动失败: {e}")

if __name__ == "__main__":
    main()
