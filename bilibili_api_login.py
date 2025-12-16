#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站二维码登录API方案
"""

import requests
import time
import json
import qrcode
from PIL import Image
import os
import subprocess
from config import output_dir, cookies_dir, bilibili_cookie_txt, debug_print

class BiliBiliAPIQRLogin:
    """使用B站API进行二维码登录"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
            'Origin': 'https://www.bilibili.com',
        })

        self.qrcode_key = None
        self.cookies = {}

        # API端点
        self.api_qrcode_generate = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        self.api_qrcode_poll = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
        self.api_cookie_info = "https://api.bilibili.com/x/web-interface/nav"

    def generate_qrcode(self):
        """
        生成登录二维码
        :return: (qrcode_url, qrcode_key)
        """
        debug_print("正在生成登录二维码...")

        try:
            response = self.session.get(self.api_qrcode_generate)
            response.raise_for_status()

            data = response.json()

            if data.get('code') == 0:
                qrcode_url = data['data']['url']
                self.qrcode_key = data['data']['qrcode_key']

                debug_print(f"✅ 二维码生成成功")
                debug_print(f"🔑 密钥: {self.qrcode_key}")

                return qrcode_url, self.qrcode_key
            else:
                debug_print(f"❌ API返回错误: {data}")
                return None, None

        except Exception as e:
            debug_print(f"❌ 生成二维码失败: {e}")
            return None, None

    def display_qrcode_image(self, qrcode_url):
        """
        显示二维码图片
        """
        if not qrcode_url:
            return

        debug_print("\n" + "=" * 60)
        debug_print("请使用B站App扫描二维码登录")
        debug_print("=" * 60)

        # 方法1: 使用qrcode库生成二维码
        debug_print("\n📱 生成二维码中...")

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qrcode_url)
            qr.make(fit=True)

            # 创建二维码图片
            img = qr.make_image(fill_color="black", back_color="white")

            # 保存到文件
            qr_path = os.path.expanduser(os.path.join(cookies_dir, 'bilibili_login_qr.png'))
            img.save(qr_path)

            debug_print(f"💾 二维码已保存到桌面: {qr_path}")

            # 尝试打开图片
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(qr_path)
                elif os.uname().sysname == 'Darwin':  # macOS
                    subprocess.run(['open', qr_path])
                else:  # Linux
                    subprocess.run(['xdg-open', qr_path])
            except:
                debug_print("⚠️  无法自动打开图片，请手动打开")

            # 在终端显示文本二维码
            debug_print("\n📋 文本二维码（备用）:")
            img_small = img.resize((50, 50))
            self._print_text_qr(img_small)

        except Exception as e:
            debug_print(f"⚠️  生成二维码图片失败: {e}")
            debug_print(f"\n🔗 请手动访问以下链接:")
            debug_print(qrcode_url)

    def _print_text_qr(self, image):
        """在终端打印文本二维码"""
        img_gray = image.convert('L')
        pixels = img_gray.load()
        width, height = img_gray.size

        for y in range(height):
            line = ""
            for x in range(width):
                if pixels[x, y] < 128:
                    line += "██"
                else:
                    line += "  "
            debug_print(line)

    def poll_login_status(self, timeout=120):
        """
        轮询登录状态
        :param timeout: 超时时间（秒）
        :return: 是否登录成功
        """
        if not self.qrcode_key:
            debug_print("❌ 没有二维码密钥")
            return False

        debug_print("\n⏳ 等待扫码登录...")
        debug_print("请在B站App中确认登录")

        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            try:
                # 轮询登录状态
                params = {
                    'qrcode_key': self.qrcode_key
                }

                response = self.session.get(self.api_qrcode_poll, params=params)
                response.raise_for_status()

                data = response.json()

                if data.get('code') == 0:
                    status = data['data'].get('code')
                    message = data['data'].get('message', '')

                    # 显示状态变化
                    debug_print(f"status:{status}, last_status:{last_status}, {data}")
                    if status != last_status:
                        if status == 0 and 'url' not in data['data']:
                            debug_print("✅ 二维码未过期，等待扫描...")
                        elif status == 86038:
                            debug_print("❌ 二维码已过期，请重新生成")
                            return False
                        elif status == 86090:
                            debug_print("📱 二维码已扫描，等待确认...", data)
                        elif status == 0 and 'url' in data['data']:
                            # 登录成功
                            login_url = data['data']['url']
                            debug_print(f"✅ 登录成功！")

                            # 从重定向URL中提取cookies
                            self._extract_cookies_from_url(login_url)
                            return True

                        last_status = status

                time.sleep(2)  # 每2秒轮询一次

            except Exception as e:
                debug_print(f"❌ 轮询出错: {e}")
                time.sleep(3)

        debug_print("❌ 登录超时")
        return False

    def _extract_cookies_from_url(self, url):
        """从URL中提取cookies"""
        try:
            # 从URL中提取参数
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # 提取关键cookies
            if 'SESSDATA' in query_params:
                self.cookies['SESSDATA'] = query_params['SESSDATA'][0]
            if 'bili_jct' in query_params:
                self.cookies['bili_jct'] = query_params['bili_jct'][0]
            if 'DedeUserID' in query_params:
                self.cookies['DedeUserID'] = query_params['DedeUserID'][0]

            debug_print(f"✅ 提取到 {len(self.cookies)} 个cookies")

        except Exception as e:
            debug_print(f"⚠️  从URL提取cookies失败: {e}")

    def verify_login(self):
        """验证登录状态"""
        debug_print("正在验证登录状态...")

        try:
            # 添加cookies到session
            for name, value in self.cookies.items():
                self.session.cookies.set(name, value)

            # 调用API验证
            response = self.session.get(self.api_cookie_info)
            response.raise_for_status()

            data = response.json()

            if data.get('code') == 0 and data['data'].get('isLogin'):
                debug_print("✅ 登录验证成功！")
                debug_print(f"👤 用户名: {data['data'].get('uname', '未知')}")
                debug_print(f"🆔 用户ID: {data['data'].get('mid', '未知')}")
                return True
            else:
                debug_print("❌ 登录验证失败")
                return False

        except Exception as e:
            debug_print(f"❌ 验证失败: {e}")
            return False

    def save_cookies(self):
        """保存cookies到文件"""
        try:
            # Netscape格式
            lines = [
                "# Netscape HTTP Cookie File",
                "# Generated by BiliBiliAPIQRLogin",
                "# https://www.bilibili.com",
                ""
            ]

            for name, value in self.cookies.items():
                line = f".bilibili.com\tTRUE\t/\tTRUE\t0\t{name}\t{value}"
                lines.append(line)

            with open(bilibili_cookie_txt, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            debug_print(f"✅ Cookies已保存: {bilibili_cookie_txt}")

            # 同时保存JSON格式
            json_file = bilibili_cookie_txt.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.cookies, f, ensure_ascii=False, indent=2)

            debug_print(f"✅ JSON格式已保存: {json_file}")

            return True

        except Exception as e:
            debug_print(f"❌ 保存cookies失败: {e}")
            return False

    def login(self, timeout=120):
        """
        完整登录流程
        :param timeout: 超时时间
        :return: 是否成功
        """
        try:
            # 1. 生成二维码
            qrcode_url, qrcode_key = self.generate_qrcode()
            if not qrcode_url:
                return False

            # 2. 显示二维码
            self.display_qrcode_image(qrcode_url)

            # 3. 轮询登录状态
            if not self.poll_login_status(timeout):
                return False

            # 4. 验证登录
            if not self.verify_login():
                return False

            # 5. 保存cookies
            success = self.save_cookies()

            if success:
                debug_print("\n🎉 登录成功！")
                return True
            else:
                debug_print("\n⚠️  登录成功但保存cookies失败")
                return False

        except KeyboardInterrupt:
            debug_print("\n\n👋 用户中断")
            return False
        except Exception as e:
            debug_print(f"\n❌ 登录流程出错: {e}")
            return False


# 使用示例
if __name__ == "__main__":
    debug_print("B站API二维码登录工具")
    debug_print("=" * 60)

    login_api = BiliBiliAPIQRLogin()

    if login_api.login():
        debug_print("\n现在可以使用以下命令下载视频:")
        debug_print("yt-dlp --cookies bilibili_cookies_api.txt '视频链接'")

        # 测试下载（可选）
        test_download = input("\n是否测试下载？(y/n): ").lower()
        if test_download == 'y':
            import yt_dlp

            url = input("请输入测试视频链接: ").strip()
            if url:
                ydl_opts = {
                    'cookies': bilibili_cookie_txt,
                    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                    'format': 'best[height<=1080]',
                    'quiet': False,
                }

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                except Exception as e:
                    debug_print(f"❌ 测试下载失败: {e}")
    else:
        debug_print("\n❌ 登录失败，请重试")