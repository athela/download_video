import os
import sys
import traceback
from pathlib import Path
import yt_dlp
import json
from config import output_dir, bilibili_cookie_txt, bilibili_cookie_json, get_download_url_list, debug_print



class BiliBiliDownloaderWithLogin:
    """B站视频下载器（带二维码登录）"""
    quality_map = {
        '最佳可用': 'bestvideo+bestaudio',  # 加号，yt_dlp会将音频和视频分别下载后融合在一起; 试过可成功
        '1080p': 'best[height<=1080]',
        '720p': 'best[height<=720]',
        '480p': 'best[height<=480]',
        '仅音频': 'bestaudio',  # 试过可成功
        '仅视频': 'bestvideo[height<=1080]',  # 试过可成功
    }

    def __init__(self):
        self.download_dir = Path(output_dir)
        self.cookies_file = Path(bilibili_cookie_txt)
        self.cookies_json = Path(bilibili_cookie_json)

    def check_login_status(self):
        """检查登录状态"""
        debug_print("检查登录状态...")

        # 检查cookies文件是否存在
        if not self.cookies_file.exists():
            debug_print("❌ 未找到cookies文件，需要登录")
            return False

        # 验证cookies是否有效
        try:
            test_url = "https://api.bilibili.com/x/web-interface/nav"

            ydl_opts = {
                'cookiefile': str(self.cookies_file),
                'skip_download': True,
                'quiet': True,
                'extract_flat': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 尝试获取用户信息
                result = ydl.extract_info(test_url, download=False)

                if result:
                    debug_print("✅ Cookies有效", self.cookies_file)
                    return True
                else:
                    debug_print("❌ Cookies无效", self.cookies_file)
                    return False

        except Exception as e:
            debug_print(f"❌ 验证失败: {e}")
            return False

    def login(self, method="api"):
        """
        登录B站
        :param method: 登录方法，可选 "selenium" 或 "api"
        :return: 是否成功
        """
        debug_print(f"使用 {method} 方法登录...")

        if method == "api":
            # 使用API方法
            from bilibili_api_login import BiliBiliAPIQRLogin

            try:
                login_api = BiliBiliAPIQRLogin()
                success = login_api.login()

                if success:
                    return True
                else:
                    return False
            except Exception as e:
                debug_print(f"❌ API登录失败: {e}")
                return False

        else:
            debug_print(f"❌ 未知登录方法: {method}")
            return False

    def debug_video_info(self, info, url):
        if not info:
            return
        result = {
            'title': info.get('title', '未知标题'),
            'duration': info.get('duration', 0),
            'formats': [],
            'id': info.get('id', ''),
            'extractor': info.get('extractor', ''),
            'webpage_url': info.get('webpage_url', url),
        }

        # 获取格式信息
        if 'formats' in info:
            debug_print(f'available video format:')
            for fmt in info['formats']:
                if fmt.get('ext'):
                    result['formats'].append({
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext'),
                        'resolution': fmt.get('resolution', '未知'),
                        'format_note': fmt.get('format_note', ''),
                        'filesize': fmt.get('filesize'),
                        'vcodec': fmt.get('vcodec', '未知'),
                        'acodec': fmt.get('acodec', '未知'),
                    })
                    size = fmt.get('filesize', 0)
                    size_str = f"{size / 1024 / 1024:.1f}MB" if size else "未知大小"
                    debug_print(f"  - {fmt['format_id'], fmt['format'], fmt['resolution'], fmt['ext'], size_str}")
        return result


    def download_batch_video(self, url_list, quality='最佳可用'):
        if not self.check_login_status():
            debug_print("需要重新登录...")
            if not self.login():
                debug_print("❌ 登录失败，无法下载")
                return False
        for url_info in url_list:
            url, playlist_items = url_info
            self._download_one_video(url, quality, playlist_items)


    def download_video(self, url, quality='最佳可用', playlist_items=None):
        if not self.check_login_status():
            debug_print("需要重新登录...")
            if not self.login():
                debug_print("❌ 登录失败，无法下载")
                return False

        self._download_one_video(url, quality, playlist_items)

    def _download_one_video(self, url, quality, playlist_items):
        format_choice = self.quality_map.get(quality, 'bestvideo+bestaudio')
        # 下载配置
        ydl_opts = {
            'cookiefile': str(self.cookies_file),
            'outtmpl': str(self.download_dir/'%(title).100s.%(ext)s'),
            'format': format_choice,
            'merge_output_format': 'mp4',

            # 网络设置
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'socket_timeout': 30,

            # 进度显示
            'progress_hooks': [self._progress_hook],

            # B站特定设置
            'extractor_args': {
                'bilibili': {'format': 'bv*+ba/b'}
            },

            # 请求头
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://www.bilibili.com',
            },
        }
        if playlist_items and '_p' not in url and '?p=' not in url:
            ydl_opts['playlist_items'] = playlist_items

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(url, download=False)
                if info:
                    debug_print(f"📺 标题: {info.get('title', '未知')}")
                    debug_print(f"⏱️ 时长: {info.get('duration', 0)}秒, availability:{info.get('availability')}")

                    # 检查是否需要会员
                    if info.get('availability') == 'subscriber_only':
                        debug_print("🔒 会员视频，使用登录cookies下载")
                    self.debug_video_info(info, url)
                else:
                    debug_print('没有视频详细信息', format_choice)

                # 开始下载
                debug_print("开始下载", info.get('title', '未知'))
                ydl.download([url])

                debug_print("✅ 下载完成！", info.get('title', '未知'))
                return True

        except yt_dlp.utils.DownloadError as e:
            debug_print(f"❌ 下载错误: {e}")

            # 尝试备用方案
            debug_print("尝试备用方案...")
            return self._download_with_alternative(url)
        except Exception as e:
            debug_print(f"❌ 下载失败: {e}")
            debug_print(ydl_opts['format'])
            print(traceback.format_exc())
            return False

    def _progress_hook(self, d):
        """进度回调"""
        if d['status'] == 'downloading':
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)

            if total > 0:
                percent = (downloaded / total) * 100
                speed = d.get('speed')
                if not speed:
                    speed = 0

                if speed > 1024 * 1024:
                    speed_str = f"{speed / 1024 / 1024:.1f} MB/s"
                elif speed > 1024:
                    speed_str = f"{speed / 1024:.1f} KB/s"
                else:
                    speed_str = f"{speed:.0f} B/s"

                debug_print(f"\r进度: {percent:.1f}% | 速度: {speed_str}", end='', flush=True)

        elif d['status'] == 'finished':
            debug_print(f"\n✅ 下载完成，正在处理...")

    def _download_with_alternative(self, url):
        """备用下载方案"""
        try:
            # 尝试使用JSON格式的cookies
            if self.cookies_json.exists():
                with open(self.cookies_json, 'r') as f:
                    cookies_dict = json.load(f)

                # 转换为cookies字符串
                cookies_str = '; '.join([f"{k}={v}" for k, v in cookies_dict.items()])

                ydl_opts = {
                    'outtmpl': str(self.download_dir/ '%(title).100s.%(ext)s'),
                    'format': 'best[height<=1080]',
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Referer': 'https://www.bilibili.com',
                        'Cookie': cookies_str,
                    },
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                return True
        except Exception as e:
            debug_print(f"❌ 备用方案也失败: {e}")

        return False



if __name__ == "__main__":
    download_url_list = get_download_url_list()
    downloader = BiliBiliDownloaderWithLogin()
    # 批量下载
    downloader.download_batch_video(download_url_list)

    # 单个下载
    # url = download_url_list[2]
    # downloader.download_video(url)




