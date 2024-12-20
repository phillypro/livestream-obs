# app/services/tiktok_service.py
import os
import json
import random
import requests
import gzip
import platform
import glob
import re
import base64
import hashlib
import time
import uuid
import seleniumwire.undetected_chromedriver as uc
from urllib.parse import urlparse, parse_qs
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables if needed
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

class Stream:
    def __init__(self, token):
        self.s = requests.session()
        self.s.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) StreamlabsDesktop/1.16.7 Chrome/114.0.5735.289 Electron/25.9.3 Safari/537.36",
            "authorization": f"Bearer {token}"
        })

    def search(self, game):
        if not game:
            return []
        url = f"https://streamlabs.com/api/v5/slobs/tiktok/info?category={game}"
        info = self.s.get(url).json()
        info["categories"].append({"full_name": "Other", "game_mask_id": ""})
        return info["categories"]

    def start(self, title, category):
        url = "https://streamlabs.com/api/v5/slobs/tiktok/stream/start"
        files = (
            ('title', (None, title)),
            ('device_platform', (None, 'win32')),
            ('category', (None, category)),
        )
        response = self.s.post(url, files=files).json()
        try:
            self.id = response["id"]
            return response["rtmp"], response["key"]
        except KeyError:
            return None, None

    def end(self):
        url = f"https://streamlabs.com/api/v5/slobs/tiktok/stream/{self.id}/end"
        response = self.s.post(url).json()
        return response.get("success", False)

class TikTokStreamMixin:
    CLIENT_KEY = "awdjaq9ide8ofrtz"
    REDIRECT_URI = "https://streamlabs.com/tiktok/auth"
    STATE = ""
    SCOPE = "user.info.basic,live.room.info,live.room.manage,user.info.profile,user.info.stats"
    STREAMLABS_API_URL = "https://streamlabs.com/api/v5/auth/data"

    def __init__(self, cookies_file='cookies.json'):
        self.s = requests.session()
        self.cookies_file = cookies_file
        self.stream = None
        self.is_live = False

    def load_token(self):
        # Attempt to load token from Streamlabs local storage logs
        if platform.system() == 'Windows':
            path_pattern = os.path.expandvars(r'%appdata%\slobs-client\Local Storage\leveldb\*.log')
        elif platform.system() == 'Darwin':
            path_pattern = os.path.expanduser('~/Library/Application Support/slobs-client/Local Storage/leveldb/*.log')
        else:
            return None

        files = glob.glob(path_pattern)
        files.sort(key=os.path.getmtime, reverse=True)

        token_pattern = re.compile(r'"apiToken":"([a-f0-9]+)"', re.IGNORECASE)

        for file in files:
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    matches = token_pattern.findall(content)
                    if matches:
                        token = matches[-1]
                        return token
            except Exception:
                pass
        return None

    def retrieve_token(self):
        token = self.load_token()
        if token:
            self.setup_stream(token)
            return token
        else:
            # If no token found locally, implement retrieval logic if needed
            print("No token found. Implement token retrieval if necessary.")
            return None

    def setup_stream(self, token):
        self.s.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
            "authorization": f"Bearer {token}"
        })
        self.stream = Stream(token)

    def start_stream(self, stream_title):
        if not self.stream:
            token = self.retrieve_token()
            if not token:
                raise Exception("No token could be retrieved for TikTok stream.")
        # For simplicity, use "Other" as category
        return self.stream.start(stream_title, "Other")

    def end_stream(self):
        if self.is_live and self.stream:
            self.stream.end()
            self.is_live = False
        else:
            print("No active stream to end.")

    def updateStreamDetails(self, stream_key, stream_url, obs_client, index=1):
        try:
            obs_client.send_request("CallVendorRequest", {
                "vendorName": "aitum-vertical-canvas",
                "requestType": "update_stream_key",
                "requestData": {
                    "stream_key": stream_key,
                    "index": index
                }
            })
            print(f'Stream Key for index {index} updated successfully')

            obs_client.send_request("CallVendorRequest", {
                "vendorName": "aitum-vertical-canvas",
                "requestType": "update_stream_server",
                "requestData": {
                    "stream_server": stream_url,
                    "index": index
                }
            })
            print(f'Stream Server for index {index} updated successfully')
        except Exception as e:
            print(f"Error updating stream details for index {index}: {e}")

    def startStream(self, obs_client, index=1):
        try:
            obs_client.send_request("CallVendorRequest", {
                "vendorName": "aitum-vertical-canvas",
                "requestType": "start_streaming",
                "requestData": {
                    "index": index
                }
            })
            print(f'Live Stream started for index {index}')
        except Exception as e:
            print(f"Error starting stream for index {index}: {e}")

class TikTokStreamer(TikTokStreamMixin):
    def start_stream_with_title(self, title, obs_client):
        if self.is_live:
            print("Stream is already live.")
            return None, None
        else:
            try:
                stream_url, stream_key = self.start_stream(stream_title=title)
                if stream_url and stream_key:
                    self.updateStreamDetails(stream_key, stream_url, obs_client, index=1)
                    self.startStream(obs_client, index=1)
                    self.is_live = True
                    return stream_url, stream_key
                else:
                    print("Failed to retrieve TikTok stream credentials.")
                    return None, None
            except Exception as e:
                print(f"Failed to start TikTok stream: {e}")
                return None, None

    def end_stream(self):
        super().end_stream()
