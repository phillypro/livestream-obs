# app/config/globals.py
import os
import threading
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

shutdown_event = threading.Event()

# Initially, just placeholders; main.py will populate these after initialization
settings_manager = None

# Import services that need to be globally accessible
from app.services.tiktok_service import TikTokStreamer
from app.services.instagram_service import InstagramStreamer

tiktok_streamer = TikTokStreamer(cookies_file='cookies.json')
instagram_streamer = InstagramStreamer(testing=True)
