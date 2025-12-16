import json
import os
import time
from pathlib import Path

cur_file_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(cur_file_dir, "output")
cookies_dir = os.path.join(cur_file_dir, "cookies")
bilibili_cookie_txt = os.path.join(cookies_dir, 'bilibili_cookies_api.txt')
bilibili_cookie_json = os.path.join(cookies_dir, 'bilibili_cookies_api.json')

Path(output_dir).mkdir(parents=True, exist_ok=True)
Path(cookies_dir).mkdir(parents=True, exist_ok=True)

def get_download_url_list():
    with open(os.path.join(cur_file_dir, "download_list.json"), 'r') as f:
        json_data = json.load(f)
        return json_data['download_list']

def debug_print(msg, *args, **kwargs):
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), msg, *args)

