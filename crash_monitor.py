import sys
import os
import time
import subprocess
import psutil
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import json
from datetime import datetime

class CrashMonitor:
    def __init__(self):
        self.main_process = None
        self.monitoring = True
        self.crash_log_file = "crash_log.txt"
        
    def start_main_program(self):
        try:
            # 添加--monitored参数，告诉main.py它已经被监控了
            self.main_process = subprocess.Popen([sys.executable, "main.py", "--monitored"],
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE,
                                               cwd=os.getcwd())
            return True
        except Exception as e:
            self.log_error(f"Failed to start main program: {str(e)}")
            return False
    
    def monitor_process(self):
        while self.monitoring:
            if self.main_process is None:
                break
                
            try:
                if self.main_process.poll() is not None:
                    return_code = self.main_process.returncode
                    if return_code != 0:
                        self.handle_crash(return_code)
                    break
                time.sleep(1)
            except Exception as e:
                self.log_error(f"Monitor error: {str(e)}")
                break
    
    def handle_crash(self, return_code):
        try:
            if os.path.exists("normal_exit.flag"):
                os.remove("normal_exit.flag")
                return

            stdout, stderr = self.main_process.communicate(timeout=5)
            crash_info = {
                "timestamp": datetime.now().isoformat(),
                "return_code": return_code,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore')
            }

            with open(self.crash_log_file, 'w', encoding='utf-8') as f:
                json.dump(crash_info, f, indent=2, ensure_ascii=False)

            self.show_crash_dialog()
        except Exception as e:
            self.log_error(f"Error handling crash: {str(e)}")
    
    def show_crash_dialog(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        dialog = CrashDialog(root, self.crash_log_file)
        root.wait_window(dialog.dialog)
        root.destroy()
    
    def log_error(self, message):
        try:
            with open("monitor_error.log", "a", encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()}: {message}\n")
        except:
            pass
    
    def monitor_existing_process(self):
        # 监控已经运行的main.py进程
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']
                        if cmdline and any('main.py' in arg for arg in cmdline):
                            # 找到main.py进程
                            self.monitor_pid(proc.info['pid'])
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.log_error(f"Error monitoring existing process: {str(e)}")

    def monitor_pid(self, pid):
        try:
            process = psutil.Process(pid)
            while self.monitoring:
                if not process.is_running():
                    # 进程已经结束，检查是否是正常退出
                    if not os.path.exists("normal_exit.flag"):
                        # 非正常退出，显示崩溃对话框
                        self.handle_pid_crash()
                    else:
                        # 正常退出，清理标志文件
                        os.remove("normal_exit.flag")
                    break
                time.sleep(1)
        except psutil.NoSuchProcess:
            # 进程不存在，可能已经退出
            if not os.path.exists("normal_exit.flag"):
                self.handle_pid_crash()
        except Exception as e:
            self.log_error(f"Error monitoring PID {pid}: {str(e)}")

    def handle_pid_crash(self):
        try:
            crash_info = {
                "timestamp": datetime.now().isoformat(),
                "return_code": -1,
                "stdout": "Process monitoring detected crash",
                "stderr": "Main process terminated unexpectedly"
            }

            with open(self.crash_log_file, 'w', encoding='utf-8') as f:
                json.dump(crash_info, f, indent=2, ensure_ascii=False)

            self.show_crash_dialog()
        except Exception as e:
            self.log_error(f"Error handling PID crash: {str(e)}")

    def stop_monitoring(self):
        self.monitoring = False

class CrashDialog:
    def __init__(self, parent, log_file):
        self.log_file = log_file
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("程序异常退出")
        self.dialog.geometry("500x400")
        self.dialog.resizable(True, True)
        
        self.setup_ui()
        self.center_window()
        
    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg='#2d3748', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        title_label = tk.Label(main_frame, 
                              text="⚠️ 程序异常退出", 
                              font=('Microsoft YaHei', 16, 'bold'),
                              fg='#ffffff', bg='#2d3748')
        title_label.pack(pady=(0, 10))
        
        message_label = tk.Label(main_frame,
                                text="检测到程序非正常退出，是否查看错误日志并提交问题报告？",
                                font=('Microsoft YaHei', 10),
                                fg='#e2e8f0', bg='#2d3748',
                                wraplength=450)
        message_label.pack(pady=(0, 15))
        
        log_frame = tk.LabelFrame(main_frame, text="错误日志", 
                                 font=('Microsoft YaHei', 9),
                                 fg='#ffffff', bg='#2d3748')
        log_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 height=10,
                                                 font=('Consolas', 9),
                                                 bg='#1a202c', fg='#e2e8f0',
                                                 insertbackground='#ffffff')
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.load_log_content()
        
        button_frame = tk.Frame(main_frame, bg='#2d3748')
        button_frame.pack(fill='x')
        
        submit_btn = tk.Button(button_frame, text="提交Issue", 
                              command=self.submit_issue,
                              font=('Microsoft YaHei', 10),
                              bg='#4299e1', fg='white',
                              relief='flat', padx=20, pady=8)
        submit_btn.pack(side='left', padx=(0, 10))
        
        close_btn = tk.Button(button_frame, text="关闭", 
                             command=self.close_dialog,
                             font=('Microsoft YaHei', 10),
                             bg='#718096', fg='white',
                             relief='flat', padx=20, pady=8)
        close_btn.pack(side='right')
    
    def load_log_content(self):
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.log_text.insert('1.0', content)
        except Exception as e:
            self.log_text.insert('1.0', f"无法读取日志文件: {str(e)}")
    
    def submit_issue(self):
        import webbrowser
        issue_url = "https://github.com/Afly-dream/Free-wyy/issues/new"
        webbrowser.open(issue_url)
        self.close_dialog()
    
    def close_dialog(self):
        self.dialog.destroy()
    
    def center_window(self):
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

def main():
    # 检查是否已经有主程序在运行
    if os.path.exists("monitor_running.flag"):
        # 如果有，就监控现有的进程
        monitor = CrashMonitor()
        monitor.monitor_existing_process()
    else:
        # 否则启动新的主程序
        monitor = CrashMonitor()

        if monitor.start_main_program():
            monitor_thread = threading.Thread(target=monitor.monitor_process)
            monitor_thread.daemon = True
            monitor_thread.start()

            try:
                monitor_thread.join()
            except KeyboardInterrupt:
                monitor.stop_monitoring()
        else:
            print("Failed to start main program")

if __name__ == "__main__":
    main()
