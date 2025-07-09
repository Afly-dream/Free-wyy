# -*- coding: utf-8 -*-
"""
所有后台工作线程 (QThread) 的定义
"""
import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .logic.analyzer import OptimalGiftAnalyzer

# --- 辅助函数 ---

BASE62_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
BASE = 62

def base62_to_int(s):
    """将 Base62 字符串转换为整数"""
    num = 0
    for char in s:
        if char in BASE62_CHARS:
            num = num * BASE + BASE62_CHARS.index(char)
    return num

def int_to_base62(n, length=6):
    """将整数转换为指定长度的 Base62 字符串"""
    if n == 0:
        return BASE62_CHARS[0] * length
    s = ''
    while n > 0:
        s = BASE62_CHARS[n % BASE] + s
        n //= BASE
    return s.rjust(length, BASE62_CHARS[0])

def to_beijing_time(timestamp_ms):
    """将毫秒时间戳转换为北京时间字符串"""
    try:
        beijing_tz = timezone(timedelta(hours=8))
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=beijing_tz)
        return dt.strftime('%Y-%m-%d %H:%M:%S (北京时间)')
    except (ValueError, TypeError):
        return '无效时间'

# --- 扫描器工作线程 ---

class ScannerWorker(QThread):
    """
    在独立线程中运行扫描任务，采用高效的共享原子计数器策略。
    """
    log_message = pyqtSignal(str)
    result_found = pyqtSignal(str, str)  # link_type, url
    finished = pyqtSignal()

    def __init__(self, prefix, start_suffix, end_suffix, max_workers, 
                 sleep_every, sleep_for, parent=None):
        super().__init__(parent)
        self.prefix = prefix
        self.start_id = base62_to_int(start_suffix)
        self.end_id = base62_to_int(end_suffix)
        self.max_workers = max_workers
        self.sleep_every = sleep_every
        self.sleep_for = sleep_for

        self._is_running = True
        self._is_paused = False
        self.pause_lock = threading.Lock()
        
        self.id_lock = threading.Lock()
        self.current_id = self.start_id
        
        self.checked_count = 0
        self.found_count = 0
        self.start_time = 0
        
        # 节流相关
        self.throttle_lock = threading.Lock()
        self.requests_since_sleep = 0

    def run(self):
        """执行扫描的主函数。"""
        self.start_time = time.time()
        
        self.log_message.emit(f"扫描任务启动: 从 {self.prefix}{int_to_base62(self.start_id)} "
                              f"到 {self.prefix}{int_to_base62(self.end_id)}")
        self.log_message.emit(f"使用 {self.max_workers} 个线程进行扫描。")
        if self.sleep_every > 0 and self.sleep_for > 0:
            self.log_message.emit(f"节流策略: 每 {self.sleep_every} 次请求暂停 {self.sleep_for} 秒。")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务让所有工作线程启动
            for _ in range(self.max_workers):
                executor.submit(self.check_link_worker)
            
            # 等待所有线程完成它们的工作
            # .shutdown() 会自动处理等待
        
        if self._is_running: # 正常完成
            self.log_message.emit("--- 扫描完成 ---")
        else: # 被用户停止
            self.log_message.emit("--- 扫描已停止 ---")
            
        self.finished.emit()

    def check_link_worker(self):
        """单个线程的工作循环"""
        while self._is_running and self.get_next_id() < self.end_id:
            with self.pause_lock:
                if not self._is_running: return

            current_id = self.get_next_id()
            if current_id is None: # 任务已完成
                break

            self.handle_throttling()

            self.checked_count += 1
            suffix = int_to_base62(current_id)
            code = self.prefix + suffix
            url = f"http://163cn.tv/{code}"
            
            try:
                resp = requests.head(url, allow_redirects=False, timeout=5)
                if resp.status_code in [301, 302] and 'Location' in resp.headers:
                    location = resp.headers['Location']
                    link_type = None
                    if 'vip-invite-cashier' in location:
                        link_type = 'vip'
                    elif 'gift-receive' in location:
                        link_type = 'gift'
                    
                    if link_type:
                        self.log_message.emit(f"[✅ {link_type.upper()} 链接] {url}")
                        self.result_found.emit(link_type, url)
                        self.found_count += 1
                    else:
                        self.log_message.emit(f"[⚠️ 跳转但不符] {url} → {location[:100]}...")

                else:
                    # Log non-redirects like 404, 200, etc.
                    self.log_message.emit(f"[❌ 无效] {url} → 状态码: {resp.status_code}")

            except requests.exceptions.RequestException:
                pass # 静默处理网络错误
            except Exception as e:
                self.log_message.emit(f"[⚠️ 错误] {url} -> {e}")

    def get_next_id(self):
        """线程安全地获取下一个要处理的ID"""
        with self.id_lock:
            if self.current_id >= self.end_id:
                return None
            check_id = self.current_id
            self.current_id += 1
            return check_id

    def handle_throttling(self):
        """处理请求节流"""
        if self.sleep_every <= 0 or self.sleep_for <= 0:
            return
        
        with self.throttle_lock:
            self.requests_since_sleep += 1
            if self.requests_since_sleep % self.sleep_every == 0:
                self.log_message.emit(f"[节流] 已达 {self.requests_since_sleep} 次请求，暂停 {self.sleep_for} 秒...")
                time.sleep(self.sleep_for)
                
    def get_speed(self):
        elapsed_time = time.time() - self.start_time
        return self.checked_count / elapsed_time if elapsed_time > 0 else 0

    def stop(self):
        self._is_running = False

    def pause(self):
        if not self._is_paused:
            self.pause_lock.acquire()
            self._is_paused = True
            self.log_message.emit("扫描已暂停。")

    def resume(self):
        if self._is_paused:
            self.pause_lock.release()
            self._is_paused = False
            self.log_message.emit("扫描已恢复。")


# --- 分析器工作线程 ---

class AnalyzerWorker(QThread):
    """分析器工作线程，用于礼品卡分析"""
    progress_updated = pyqtSignal(int, int)  # current, total
    single_result_ready = pyqtSignal(dict)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, links, max_workers=10, parent=None):
        super().__init__(parent)
        self.links = links
        self.max_workers = max_workers
        self.analyzer = OptimalGiftAnalyzer()
        self.is_running = True

    def run(self):
        if not self.links:
            self.finished.emit()
            return
            
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.analyzer.analyze_gift_link, url): url for url in self.links}
            total = len(self.links)
            completed = 0

            for future in as_completed(future_to_url):
                if not self.is_running:
                    future.cancel()
                    continue

                try:
                    result = future.result()
                    self.single_result_ready.emit(result)
                except Exception as e:
                    url = future_to_url[future]
                    error_msg = f"处理链接 {url} 时发生严重错误: {e}"
                    self.error_occurred.emit(error_msg)
                    self.single_result_ready.emit({'status': 'system_error', 'short_url': url, 'message': error_msg})
                
                completed += 1
                self.progress_updated.emit(completed, total)
        
        self.finished.emit()

    def stop(self):
        self.is_running = False


# --- VIP检查工作线程 ---

class VipCheckWorker(QThread):
    """VIP链接状态检查线程"""
    progress_updated = pyqtSignal(int, int)
    single_result_ready = pyqtSignal(dict)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, links, max_workers=10, parent=None):
        super().__init__(parent)
        self.links = links
        self.max_workers = max_workers
        self.is_running = True

    def run(self):
        if not self.links:
            self.finished.emit()
            return

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.check_vip_link, url): url for url in self.links}
            total = len(self.links)
            completed = 0

            for future in as_completed(future_to_url):
                if not self.is_running:
                    future.cancel()
                    continue

                try:
                    result = future.result()
                    self.single_result_ready.emit(result)
                except Exception as e:
                    url = future_to_url[future]
                    error_msg = f"检查VIP链接 {url} 时发生错误: {e}"
                    self.error_occurred.emit(error_msg)
                    self.single_result_ready.emit({'status': 'error', 'short_url': url, 'message': error_msg})
                
                completed += 1
                self.progress_updated.emit(completed, total)

        self.finished.emit()
        
    def check_vip_link(self, short_url):
        """
        检查单个VIP链接的状态 (重构后的强大版本)
        1. 获取重定向URL
        2. 提取参数
        3. 轮询多个API端点
        """
        try:
            # 第一步: 获取重定向链接
            head_resp = requests.head(short_url, allow_redirects=False, timeout=10)
            if head_resp.status_code not in [301, 302] or 'Location' not in head_resp.headers:
                return {'status': 'invalid', 'short_url': short_url, 'message': f'非跳转链接 (HTTP {head_resp.status_code})', 'status_text': '无效'}

            redirect_url = head_resp.headers['Location']
            if 'vip-invite-cashier' not in redirect_url:
                return {'status': 'not_vip', 'short_url': short_url, 'message': '非VIP邀请链接', 'status_text': '非VIP'}

            # 第二步: 提取参数
            parsed = urlparse(redirect_url)
            query_params = parse_qs(parsed.query)
            token_info = {
                'token': query_params.get('token', [None])[0],
                'recordId': query_params.get('recordId', [None])[0],
            }
            if not token_info['token'] and not token_info['recordId']:
                 return {'status': 'error', 'short_url': short_url, 'message': '无法从URL中提取token或recordId', 'status_text': '参数提取失败'}

            # 第三步: 轮询API
            api_urls = [
                'https://interface.music.163.com/api/vipactivity/app/vip/invitation/detail/info/get',
                'https://interface.music.163.com/api/vip/invitation/detail',
                'https://music.163.com/api/vip/invitation/detail'
            ]
            
            for api_url in api_urls:
                try:
                    params = {k: v for k, v in token_info.items() if v is not None}
                    response = requests.get(api_url, params=params, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data and data['data']:
                            detail_data = data['data']
                            expire_time = (detail_data.get('expireTime') or
                                         detail_data.get('tokenExpireTime'))

                            if expire_time:
                                current_time = int(time.time() * 1000)
                                is_valid = expire_time > current_time
                                status_text = '有效' if is_valid else '已过期'
                                return {
                                    'status': 'success',
                                    'short_url': short_url,
                                    'status_text': status_text,
                                    'expire_date': to_beijing_time(expire_time),
                                    'is_valid': is_valid,
                                    'message': f'API检查成功: {api_url}'
                                }
                except requests.RequestException:
                    continue # 尝试下一个API

            return {'status': 'error', 'short_url': short_url, 'message': '所有API端点检查失败', 'status_text': 'API检查失败'}

        except requests.RequestException as e:
            return {'status': 'error', 'short_url': short_url, 'message': f'网络错误: {e}', 'status_text': '网络错误'}
    
    def stop(self):
        self.is_running = False

# --- 文件操作工作线程 ---
class FileOperationThread(QThread):
    """文件操作工作线程"""
    operation_completed = pyqtSignal(bool, str, object)  # 成功状态, 消息, 返回数据
    
    def __init__(self, operation_type, file_path=None, data=None, parent=None):
        super().__init__(parent)
        self.operation_type = operation_type
        self.file_path = file_path
        self.data = data
        self.result_data = None

    def run(self):
        """执行文件操作"""
        try:
            if self.operation_type == 'load_text':
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.result_data = content
                self.operation_completed.emit(True, f"已从 {self.file_path} 加载内容。", self.result_data)
            
            elif self.operation_type == 'save_text':
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    f.write(self.data)
                self.operation_completed.emit(True, f"数据已保存到 {self.file_path}。", None)

        except Exception as e:
            self.operation_completed.emit(False, f"文件操作失败: {e}", None) 