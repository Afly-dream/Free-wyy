# -*- coding: utf-8 -*-
"""
网易云音乐加密工具类
"""
import random
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


class NetEaseEncryption:
    """网易云音乐加密工具类"""

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
        """生成随机字符串"""
        return ''.join(random.sample(self.character, length))

    def aes_encrypt(self, text, key):
        """AES加密"""
        text = pad(text.encode(), AES.block_size)
        key = key.encode()
        iv = self.iv.encode()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(text)
        return base64.b64encode(encrypted).decode()

    def rsa_encrypt(self, text, e, n):
        """RSA加密"""
        # 字符串反转后转十六进制
        text_hex = text[::-1].encode().hex()
        # RSA加密: C = M^e mod n
        encrypted = pow(int(text_hex, 16), int(e, 16), int(n, 16))
        return format(encrypted, 'x')

    def encrypt_params(self, data):
        """加密参数"""
        # 生成16位随机字符串
        random_str = self.create_random_string(16)

        # 第一次AES加密
        first_encrypt = self.aes_encrypt(data, self.nonce)

        # 第二次AES加密
        second_encrypt = self.aes_encrypt(first_encrypt, random_str)

        # RSA加密随机字符串
        rsa_encrypted = self.rsa_encrypt(random_str, self.public_key, self.modulus)

        return {
            'params': second_encrypt,
            'encSecKey': rsa_encrypted
        } 