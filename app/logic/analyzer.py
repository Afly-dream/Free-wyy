# -*- coding: utf-8 -*-
"""
网易云音乐礼品卡最优分析器
直接调用API接口，实现高效的礼品卡状态判断
"""

import requests
import json
import time
import threading
from urllib.parse import urlparse, parse_qs
from requests.exceptions import (
    RequestException, ConnectionError, Timeout,
    HTTPError, TooManyRedirects, SSLError
)

from .encryption import NetEaseEncryption


class OptimalGiftAnalyzer:
    """最优礼品卡分析器 - 直接调用API"""

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

        # 线程锁
        self.lock = threading.Lock()
        self.results = []

    def classify_exception(self, exception):
        """分类异常类型，返回详细的异常信息"""
        if isinstance(exception, ConnectionError):
            return {
                'error_type': 'api_exception',
                'error_category': 'connection_error',
                'error_message': '网络连接失败',
                'technical_details': str(exception)
            }
        elif isinstance(exception, Timeout):
            return {
                'error_type': 'api_exception',
                'error_category': 'timeout',
                'error_message': '请求超时',
                'technical_details': str(exception)
            }
        elif isinstance(exception, HTTPError):
            return {
                'error_type': 'api_exception',
                'error_category': 'http_error',
                'error_message': 'HTTP请求错误',
                'technical_details': str(exception)
            }
        elif isinstance(exception, TooManyRedirects):
            return {
                'error_type': 'api_exception',
                'error_category': 'redirect_error',
                'error_message': '重定向次数过多',
                'technical_details': str(exception)
            }
        elif isinstance(exception, SSLError):
            return {
                'error_type': 'api_exception',
                'error_category': 'ssl_error',
                'error_message': 'SSL证书错误',
                'technical_details': str(exception)
            }
        elif isinstance(exception, RequestException):
            return {
                'error_type': 'api_exception',
                'error_category': 'request_error',
                'error_message': '请求异常',
                'technical_details': str(exception)
            }
        else:
            return {
                'error_type': 'system_exception',
                'error_category': 'unknown_error',
                'error_message': '未知系统异常',
                'technical_details': str(exception)
            }

    def extract_gift_params(self, redirect_url):
        """从重定向URL中提取礼品卡参数"""
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
        except Exception as e:
            print(f"参数提取失败: {e}")
            return None

    def call_gift_api(self, gift_params):
        """直接调用礼品卡API"""
        try:
            # 构造API请求数据
            api_data = {
                'd': gift_params['d'],
                'p': gift_params['p'],
                'userid': gift_params['userid'],
                'app_version': gift_params['app_version'],
                'dlt': gift_params['dlt'],
                'csrf_token': ''
            }

            # 加密参数
            encrypted_data = self.encryption.encrypt_params(json.dumps(api_data))

            # 发送API请求
            response = self.session.post(
                self.api_url,
                data=encrypted_data,
                timeout=10
            )

            if response.status_code == 200:
                try:
                    result = response.json()
                    return self.parse_api_response(result, gift_params)
                except json.JSONDecodeError as e:
                    return {
                        'status': 'api_exception',
                        'error_type': 'api_exception',
                        'error_category': 'json_decode_error',
                        'error_message': 'API响应格式错误',
                        'message': 'API响应格式错误',
                        'technical_details': str(e)
                    }
            elif response.status_code == 403:
                return {
                    'status': 'api_exception',
                    'error_type': 'api_exception',
                    'error_category': 'forbidden',
                    'error_message': 'API访问被拒绝(403)',
                    'message': 'API访问被拒绝',
                    'technical_details': f'HTTP {response.status_code}'
                }
            elif response.status_code == 429:
                return {
                    'status': 'api_exception',
                    'error_type': 'api_exception',
                    'error_category': 'rate_limit',
                    'error_message': '请求频率过高(429)',
                    'message': '请求频率过高',
                    'technical_details': f'HTTP {response.status_code}'
                }
            elif response.status_code >= 500:
                return {
                    'status': 'api_exception',
                    'error_type': 'api_exception',
                    'error_category': 'server_error',
                    'error_message': f'服务器错误({response.status_code})',
                    'message': f'服务器错误({response.status_code})',
                    'technical_details': f'HTTP {response.status_code}'
                }
            else:
                return {
                    'status': 'api_exception',
                    'error_type': 'api_exception',
                    'error_category': 'http_error',
                    'error_message': f'HTTP错误({response.status_code})',
                    'message': f'HTTP错误({response.status_code})',
                    'technical_details': f'HTTP {response.status_code}'
                }

        except (ConnectionError, Timeout, HTTPError, TooManyRedirects, SSLError, RequestException) as e:
            error_info = self.classify_exception(e)
            return {
                'status': 'api_exception',
                'message': error_info['error_message'],
                **error_info
            }
        except Exception as e:
            error_info = self.classify_exception(e)
            return {
                'status': 'system_exception',
                'message': f'系统异常: {str(e)}',
                **error_info
            }

    def parse_api_response(self, api_result, gift_params):
        """解析API响应"""
        try:
            # 检查API响应的基本结构
            if not api_result:
                return {
                    'status': 'api_exception',
                    'error_type': 'api_exception',
                    'error_category': 'empty_response',
                    'error_message': 'API返回空响应',
                    'message': 'API返回空响应'
                }

            # 检查API错误码
            if 'code' in api_result and api_result['code'] != 200:
                error_code = api_result['code']
                error_msg = api_result.get('message', '未知API错误')
                return {
                    'status': 'api_exception',
                    'error_type': 'api_exception',
                    'error_category': 'api_business_error',
                    'error_message': f'API业务错误({error_code}): {error_msg}',
                    'message': f'API业务错误: {error_msg}',
                    'api_code': error_code,
                    'technical_details': f'API Code: {error_code}, Message: {error_msg}'
                }

            # 检查是否有数据返回
            if 'data' not in api_result:
                return {
                    'status': 'api_exception',
                    'error_type': 'api_exception',
                    'error_category': 'missing_data',
                    'error_message': 'API响应缺少数据字段',
                    'message': 'API响应格式错误'
                }

            data = api_result['data']
            current_time = int(time.time() * 1000)  # 当前时间戳(毫秒)

            # 提取关键信息
            record = data.get('record', {})
            sku = data.get('sku', {})
            sender = data.get('sender', {})

            # 判断礼品卡状态
            expire_time = record.get('expireTime', 0)
            total_count = record.get('totalCount', 0)
            used_count = record.get('usedCount', 0)

            # 状态判断逻辑
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

            # 计算过期时间
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
                'is_expired': current_time > expire_time if expire_time > 0 else False,
                'api_response': data
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'响应解析失败: {str(e)}'
            }

    def analyze_gift_link(self, short_url):
        """分析单个礼品链接"""
        try:
            # 第一步：获取重定向链接
            resp = self.session.head(short_url, allow_redirects=False, timeout=10)

            if resp.status_code not in [301, 302]:
                if resp.status_code == 404:
                    return {
                        "status": "invalid",
                        "message": "链接不存在(404)",
                        "error_category": "not_found",
                        "short_url": short_url
                    }
                elif resp.status_code >= 500:
                    return {
                        "status": "api_exception",
                        "error_type": "api_exception",
                        "error_category": "server_error",
                        "error_message": f"短链接服务器错误({resp.status_code})",
                        "message": f"短链接服务器错误({resp.status_code})",
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

            # 第二步：提取礼品卡参数
            gift_params = self.extract_gift_params(redirect_url)
            if not gift_params:
                return {
                    "status": "error",
                    "message": "参数提取失败",
                    "short_url": short_url
                }

            # 第三步：调用API获取状态
            api_result = self.call_gift_api(gift_params)

            # 添加原始信息
            api_result['short_url'] = short_url
            api_result['redirect_url'] = redirect_url

            return api_result

        except (ConnectionError, Timeout, HTTPError, TooManyRedirects, SSLError, RequestException) as e:
            error_info = self.classify_exception(e)
            return {
                "status": "api_exception",
                "short_url": short_url,
                "message": error_info['error_message'],
                **error_info
            }
        except Exception as e:
            error_info = self.classify_exception(e)
            return {
                "status": "system_exception",
                "short_url": short_url,
                "message": f"系统异常: {str(e)}",
                **error_info
            } 