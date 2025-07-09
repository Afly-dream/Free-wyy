import time
import requests
import threading
import json
import random
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import QThread, pyqtSignal
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from requests.exceptions import RequestException, ConnectionError, Timeout, HTTPError, TooManyRedirects, SSLError

BASE62_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
BASE = 62

def base62_to_int(s):
    num = 0
    for char in s:
        if char in BASE62_CHARS:
            num = num * BASE + BASE62_CHARS.index(char)
    return num

def int_to_base62(n, length=6):
    if n == 0:
        return BASE62_CHARS[0] * length
    s = ''
    while n > 0:
        s = BASE62_CHARS[n % BASE] + s
        n //= BASE
    return s.rjust(length, BASE62_CHARS[0])

def to_beijing_time(timestamp_ms):
    try:
        beijing_tz = timezone(timedelta(hours=8))
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=beijing_tz)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return '无效时间'

class NetEaseEncryption:
    def __init__(self):
        self.character = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        self.iv = '0102030405060708'
        self.public_key = '010001'
        self.modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b' \
                       '5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417' \
                       '629ec4ee341f56135fccf695280104e0312ecbda92557c93' \
                       '870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b' \
                       '424d813cfe4875d3e82047b97ddef52741d546b8e289dc69' \
                       '35b3ece0462db0a22b8e7'
        self.nonce = '0CoJUm6Qyw8W8jud'
    
    def create_random_string(self, length=16):
        return ''.join(random.sample(self.character, length))
    
    def aes_encrypt(self, text, key):
        text = pad(text.encode(), AES.block_size)
        key = key.encode()
        iv = self.iv.encode()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(text)
        return base64.b64encode(encrypted).decode()
    
    def rsa_encrypt(self, text, e, n):
        text_hex = text[::-1].encode().hex()
        encrypted = pow(int(text_hex, 16), int(e, 16), int(n, 16))
        return format(encrypted, 'x')
    
    def encrypt_params(self, data):
        random_str = self.create_random_string(16)
        first_encrypt = self.aes_encrypt(data, self.nonce)
        second_encrypt = self.aes_encrypt(first_encrypt, random_str)
        rsa_encrypted = self.rsa_encrypt(random_str, self.public_key, self.modulus)
        return {
            'params': second_encrypt,
            'encSecKey': rsa_encrypted
        }

class ScannerWorker(QThread):
    log_message = pyqtSignal(str)
    result_found = pyqtSignal(str, str)
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
        
        self.throttle_lock = threading.Lock()
        self.requests_since_sleep = 0

    def run(self):
        self.start_time = time.time()
        
        self.log_message.emit(f"扫描任务启动: 从 {self.prefix}{int_to_base62(self.start_id)} "
                              f"到 {self.prefix}{int_to_base62(self.end_id)}")
        self.log_message.emit(f"使用 {self.max_workers} 个线程进行扫描。")
        if self.sleep_every > 0 and self.sleep_for > 0:
            self.log_message.emit(f"节流策略: 每 {self.sleep_every} 次请求暂停 {self.sleep_for} 秒。")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for _ in range(self.max_workers):
                executor.submit(self.check_link_worker)
        
        if self._is_running:
            self.log_message.emit("扫描完成")
        else:
            self.log_message.emit("扫描已停止")
            
        self.finished.emit()

    def check_link_worker(self):
        while self._is_running and self.get_next_id() < self.end_id:
            with self.pause_lock:
                if not self._is_running: return

            current_id = self.get_next_id()
            if current_id is None:
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
                    elif 'vip-trialcard' in location:
                        link_type = 'audio'
                    elif 'gift-receive' in location:
                        link_type = 'gift'

                    if link_type:
                        type_names = {'vip': 'VIP', 'audio': '音质', 'gift': '礼品'}
                        self.log_message.emit(f"[✅ {type_names[link_type]} 链接] {url}")
                        self.result_found.emit(link_type, url)
                        self.found_count += 1
                    else:
                        self.log_message.emit(f"[⚠️ 跳转但不符] {url} → {location[:100]}...")

                else:
                    self.log_message.emit(f"[❌ 无效] {url} → 状态码: {resp.status_code}")

            except requests.exceptions.RequestException:
                pass
            except Exception as e:
                self.log_message.emit(f"[⚠️ 错误] {url} -> {e}")

    def get_next_id(self):
        with self.id_lock:
            if self.current_id >= self.end_id:
                return None
            check_id = self.current_id
            self.current_id += 1
            return check_id

    def handle_throttling(self):
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

class OptimalGiftAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://music.163.com/',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })
        self.encryption = NetEaseEncryption()
        self.api_url = 'https://music.163.com/weapi/vipgift/app/gift/index'

    def extract_gift_params(self, redirect_url):
        try:
            parsed_url = urlparse(redirect_url)
            params = parse_qs(parsed_url.query)

            return {
                'd': params.get('d', [''])[0],
                'p': params.get('p', [''])[0],
                'userid': params.get('userid', [''])[0],
                'app_version': params.get('app_version', ['9.1.80'])[0],
                'dlt': params.get('dlt', ['0846'])[0]
            }
        except Exception:
            return None

    def call_gift_api(self, gift_params):
        try:
            api_data = {
                'd': gift_params['d'],
                'p': gift_params['p'],
                'userid': gift_params['userid'],
                'app_version': gift_params['app_version'],
                'dlt': gift_params['dlt'],
                'csrf_token': ''
            }

            encrypted_data = self.encryption.encrypt_params(json.dumps(api_data))

            response = self.session.post(
                self.api_url,
                data=encrypted_data,
                timeout=10
            )

            if response.status_code == 200:
                try:
                    result = response.json()
                    return self.parse_api_response(result, gift_params)
                except json.JSONDecodeError:
                    return {
                        'status': 'api_exception',
                        'message': 'API响应格式错误'
                    }
            else:
                return {
                    'status': 'api_exception',
                    'message': f'HTTP错误({response.status_code})'
                }

        except Exception as e:
            return {
                'status': 'api_exception',
                'message': f'请求异常: {str(e)}'
            }

    def parse_api_response(self, api_result, gift_params):
        try:
            if not api_result:
                return {
                    'status': 'api_exception',
                    'message': 'API返回空响应'
                }

            if 'code' in api_result and api_result['code'] != 200:
                error_code = api_result['code']
                error_msg = api_result.get('message', '未知API错误')
                return {
                    'status': 'api_exception',
                    'message': f'API业务错误: {error_msg}'
                }

            if 'data' not in api_result:
                return {
                    'status': 'api_exception',
                    'message': 'API响应缺少数据字段'
                }

            data = api_result['data']
            current_time = int(time.time() * 1000)

            record = data.get('record', {})
            sku = data.get('sku', {})
            sender = data.get('sender', {})

            expire_time = record.get('expireTime', 0)
            total_count = record.get('totalCount', 0)
            used_count = record.get('usedCount', 0)

            if expire_time > 0 and current_time > expire_time:
                gift_status = 'expired'
                status_text = '已过期'
            elif used_count >= total_count:
                gift_status = 'claimed'
                status_text = '已领取完'
            elif total_count > used_count:
                gift_status = 'available'
                status_text = f'可领取 ({total_count - used_count}/{total_count})'
            else:
                gift_status = 'unknown'
                status_text = '状态未知'

            expire_date = ''
            if expire_time > 0:
                expire_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire_time / 1000))

            return {
                'status': 'success',
                'gift_status': gift_status,
                'status_text': status_text,
                'sender_id': gift_params.get('userid', ''),
                'sender_name': sender.get('nickName', ''),
                'gift_data': gift_params.get('d', ''),
                'gift_type': sku.get('goods', ''),
                'gift_price': sku.get('price', 0),
                'total_count': total_count,
                'used_count': used_count,
                'available_count': max(0, total_count - used_count),
                'expire_time': expire_time,
                'expire_date': expire_date,
                'is_expired': current_time > expire_time if expire_time > 0 else False
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'响应解析失败: {str(e)}'
            }

    def analyze_gift_link(self, short_url):
        try:
            resp = self.session.head(short_url, allow_redirects=False, timeout=10)

            if resp.status_code not in [301, 302]:
                if resp.status_code == 404:
                    return {
                        "status": "invalid",
                        "message": "链接不存在(404)",
                        "short_url": short_url
                    }
                else:
                    return {
                        "status": "invalid",
                        "message": f"无效的短链接(HTTP {resp.status_code})",
                        "short_url": short_url
                    }

            if 'Location' not in resp.headers:
                return {
                    "status": "invalid",
                    "message": "短链接缺少重定向信息",
                    "short_url": short_url
                }

            redirect_url = resp.headers['Location']

            if 'gift-receive' not in redirect_url:
                return {
                    "status": "not_gift",
                    "message": "不是礼品卡链接",
                    "redirect_url": redirect_url,
                    "short_url": short_url
                }

            gift_params = self.extract_gift_params(redirect_url)
            if not gift_params:
                return {
                    "status": "error",
                    "message": "参数提取失败",
                    "short_url": short_url
                }

            api_result = self.call_gift_api(gift_params)

            api_result['short_url'] = short_url
            api_result['redirect_url'] = redirect_url

            return api_result

        except Exception as e:
            return {
                "status": "system_exception",
                "short_url": short_url,
                "message": f"系统异常: {str(e)}"
            }

class AnalyzerWorker(QThread):
    progress_updated = pyqtSignal(int, int, str)
    single_result_ready = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, links, max_workers=5, parent=None):
        super().__init__(parent)
        self.links = links
        self.max_workers = max_workers
        self.analyzer = OptimalGiftAnalyzer()
        self.is_running = True
        self.is_paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()

    def check_vip_expiry(self, redirect_url):
        try:
            parsed = urlparse(redirect_url)
            query_params = parse_qs(parsed.query)

            token = query_params.get('token', [None])[0]
            record_id = query_params.get('recordId', [None])[0]

            if not token and not record_id:
                return {
                    'is_valid': False,
                    'expire_date': None,
                    'error': '无法提取token或recordId'
                }

            api_urls = [
                'https://interface.music.163.com/api/vipactivity/app/vip/invitation/detail/info/get',
                'https://interface.music.163.com/api/vip/invitation/detail',
                'https://music.163.com/api/vip/invitation/detail'
            ]

            for api_url in api_urls:
                try:
                    params = {}
                    if token:
                        params['token'] = token
                    if record_id:
                        params['recordId'] = record_id

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
                                expire_date = to_beijing_time(expire_time)
                                remaining_days = (expire_time - current_time) / (1000 * 60 * 60 * 24)

                                return {
                                    'is_valid': is_valid,
                                    'expire_time': expire_time,
                                    'expire_date': expire_date,
                                    'remaining_days': remaining_days,
                                    'method': 'api',
                                    'error': None
                                }
                except:
                    continue

            return {
                'is_valid': False,
                'expire_date': None,
                'error': '所有API端点检查失败'
            }

        except Exception as e:
            return {
                'is_valid': False,
                'expire_date': None,
                'error': f'检查失败: {str(e)}'
            }

    def analyze_single_link(self, link):
        try:
            is_vip_link = False
            redirect_url = None

            try:
                response = requests.head(link, allow_redirects=False, timeout=5)
                if response.status_code in [301, 302] and 'Location' in response.headers:
                    redirect_url = response.headers['Location']
                    is_vip_link = 'vip-invite-cashier' in redirect_url
                    is_audio_link = 'vip-trialcard' in redirect_url
                else:
                    response = requests.get(link, allow_redirects=True, timeout=10)
                    redirect_url = response.url
                    is_vip_link = 'vip-invite-cashier' in redirect_url
                    is_audio_link = 'vip-trialcard' in redirect_url
            except:
                pass

            if (is_vip_link or is_audio_link) and redirect_url:
                expiry_result = self.check_vip_expiry(redirect_url)

                if is_audio_link:
                    link_type = 'audio'
                    gift_type = '音质试用卡'
                else:
                    link_type = 'vip'
                    gift_type = 'VIP邀请'

                result = {
                    'status': 'success',
                    'short_url': link,
                    'redirect_url': redirect_url,
                    'is_vip_link': is_vip_link,
                    'is_audio_link': is_audio_link,
                    'gift_type': gift_type,
                    'gift_price': 0,
                    'sender_name': '',
                    'gift_count': '',
                }

                if expiry_result.get('error'):
                    if is_audio_link:
                        result['audio_status'] = 'expiry_check_failed'
                        result['status_text'] = f"音质有效期检查失败: {expiry_result['error']}"
                    else:
                        result['vip_status'] = 'expiry_check_failed'
                        result['status_text'] = f"VIP有效期检查失败: {expiry_result['error']}"
                    result['gift_status'] = 'unknown'
                elif expiry_result.get('is_valid') is False:
                    expire_date = expiry_result.get('expire_date', 'Unknown')
                    if is_audio_link:
                        result['audio_status'] = 'expired'
                        result['status_text'] = '音质已过期'
                    else:
                        result['vip_status'] = 'expired'
                        result['status_text'] = 'VIP已过期'
                    result['gift_status'] = 'expired'
                    result['expire_date'] = expire_date
                else:
                    expire_date = expiry_result.get('expire_date', 'Unknown')
                    remaining_days = expiry_result.get('remaining_days', 0)
                    if is_audio_link:
                        result['audio_status'] = 'valid'
                        result['status_text'] = f'音质有效 - 剩余{remaining_days:.1f}天'
                    else:
                        result['vip_status'] = 'valid'
                        result['status_text'] = f'VIP有效 - 剩余{remaining_days:.1f}天'
                    result['gift_status'] = 'available'
                    result['expire_date'] = expire_date

                return result
            else:
                result = self.analyzer.analyze_gift_link(link)
                result['is_vip_link'] = False

                if result.get('status') != 'success' and redirect_url:
                    result['redirect_url'] = redirect_url
                    if 'gift-receive' in redirect_url:
                        result['message'] = '检测到礼品卡链接，但分析失败'
                    else:
                        result['message'] = '未知类型的链接'

                return result

        except Exception as e:
            return {
                'status': 'error',
                'message': f'分析失败: {str(e)}',
                'short_url': link,
                'is_vip_link': False
            }

    def run(self):
        try:
            results = []
            total = len(self.links)
            completed_count = 0
            lock = threading.Lock()

            def process_link_with_callback(link):
                nonlocal completed_count

                if not self.is_running:
                    return None

                self.pause_event.wait()

                if not self.is_running:
                    return None

                result = self.analyze_single_link(link)
                self.single_result_ready.emit(result)

                with lock:
                    completed_count += 1
                    status_text = "已暂停..." if self.is_paused else "分析中..."
                    if result['status'] == 'success':
                        if result.get('is_audio_link', False):
                            audio_status = result.get('status_text', '音质状态未知')
                            status_text = f"{audio_status}"
                        elif result.get('is_vip_link', False):
                            vip_status = result.get('status_text', 'VIP状态未知')
                            status_text = f"{vip_status}"
                        else:
                            status_text = f"{result.get('status_text', 'Unknown')}"
                    else:
                        status_text = f"错误: {result.get('message', 'Unknown')}"

                    self.progress_updated.emit(completed_count, total, status_text)

                return result

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_link = {executor.submit(process_link_with_callback, link): link
                                 for link in self.links}

                for future in as_completed(future_to_link):
                    if not self.is_running:
                        for f in future_to_link:
                            f.cancel()
                        break

                    try:
                        result = future.result()
                        if result is not None:
                            results.append(result)
                    except Exception as e:
                        link = future_to_link[future]
                        error_result = {
                            'status': 'error',
                            'message': f'处理失败: {str(e)}',
                            'short_url': link,
                            'is_vip_link': False
                        }
                        results.append(error_result)
                        self.single_result_ready.emit(error_result)

            if self.is_running:
                self.finished.emit()

        except Exception as e:
            pass

    def pause(self):
        self.is_paused = True
        self.pause_event.clear()

    def resume(self):
        self.is_paused = False
        self.pause_event.set()

    def stop(self):
        self.is_running = False
        self.pause_event.set()

class FileOperationWorker(QThread):
    operation_completed = pyqtSignal(bool, str, object)

    def __init__(self, operation_type, file_path=None, data=None, parent=None):
        super().__init__(parent)
        self.operation_type = operation_type
        self.file_path = file_path
        self.data = data
        self.result_data = None

    def run(self):
        try:
            if self.operation_type == 'load':
                self._load_file()
            elif self.operation_type == 'save':
                self._save_file()
        except Exception as e:
            self.operation_completed.emit(False, f"操作失败: {str(e)}", None)

    def _load_file(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.result_data = content
            self.operation_completed.emit(True, f"已加载文件: {self.file_path}", self.result_data)
        except Exception as e:
            self.operation_completed.emit(False, f"加载文件失败: {str(e)}", None)

    def _save_file(self):
        try:
            if self.file_path.endswith('.json'):
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
            else:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    if isinstance(self.data, list):
                        for item in self.data:
                            if isinstance(item, dict):
                                f.write(item.get('short_url', str(item)) + '\n')
                            else:
                                f.write(str(item) + '\n')
                    else:
                        f.write(str(self.data))

            count = len(self.data) if isinstance(self.data, list) else 1
            self.operation_completed.emit(True, f"已保存 {count} 项到: {self.file_path}", None)
        except Exception as e:
            self.operation_completed.emit(False, f"保存文件失败: {str(e)}", None)
