# app/services/authentications.py
import os
import pickle
import time
import requests
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from tiktok_uploader.upload import upload_video
from dotenv import load_dotenv
from instagrapi import Client

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
INSTAGRAM_2FA = os.getenv('INSTAGRAM_SEED')

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
token_dir = os.path.join(script_dir, 'tokens')
os.makedirs(token_dir, exist_ok=True)

class YouTubeClient:
    _instance = None

    @staticmethod
    def get_instance():
        if YouTubeClient._instance is None:
            YouTubeClient()
        return YouTubeClient._instance

    def __init__(self):
        if YouTubeClient._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            YouTubeClient._instance = self
            self.authenticate_youtube()

    def authenticate_youtube(self):
        credentials = None
        token_file = os.path.join(token_dir, 'token.pickle')
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                credentials = pickle.load(token)

        if not credentials or not credentials.valid or credentials.expired:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception:
                    credentials = None
            if not credentials:
                secrets_file = os.path.join(token_dir, 'client_secrets.json')
                flow = InstalledAppFlow.from_client_secrets_file(
                    secrets_file,
                    scopes=['https://www.googleapis.com/auth/youtube.upload',
                            'https://www.googleapis.com/auth/youtube.readonly',
                            'https://www.googleapis.com/auth/youtube.force-ssl']
                )
                credentials = flow.run_local_server(port=0)
                with open(token_file, 'wb') as token:
                    pickle.dump(credentials, token)
        self.youtube = build('youtube', 'v3', credentials=credentials)

    def get_current_livestream_url(self, retry_interval=2, timeout=20):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                request = self.youtube.liveBroadcasts().list(
                    part="snippet,contentDetails,status",
                    broadcastStatus="active",
                    broadcastType="all"
                )
                response = request.execute()
                if response and 'items' in response and len(response['items']) > 0:
                    video_id = response['items'][0]['id']
                    return f"https://www.youtube.com/watch?v={video_id}"
            except Exception:
                time.sleep(retry_interval)
        return "No active live stream found or timed out."

class InstagramClient:
    _instance = None

    @staticmethod
    def get_instance():
        if InstagramClient._instance is None:
            InstagramClient()
        return InstagramClient._instance

    def __init__(self):
        if InstagramClient._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            InstagramClient._instance = self
            self.authenticate_instagram()

    def authenticate_instagram(self):
        self.cl = Client()
        verification_code = None
        if INSTAGRAM_2FA:
            verification_code = self.cl.totp_generate_code(INSTAGRAM_2FA)

        session_file = os.path.join(token_dir, 'instagram_session.json')
        try:
            if os.path.exists(session_file):
                session = self.cl.load_settings(session_file)
                if session:
                    self.cl.set_settings(session)

            if verification_code:
                self.cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, verification_code=verification_code)
            else:
                self.cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)

            # Test login
            self.cl.user_info_by_username(INSTAGRAM_USERNAME)
            print("Successfully logged into Instagram.")
            self.cl.dump_settings(session_file)
        except Exception as e:
            print(f"Instagram authentication error: {e}")

    def reauthenticate(self):
        self.authenticate_instagram()
        print("Re-authentication completed.")

class TikTokClient:
    def __init__(self):
        pass

    def upload_video(self, filename, caption, headless=True):
        cookie_path = os.path.join(token_dir, 'tiktokcookies.txt')
        upload_video(filename, caption, cookie_path, headless)
