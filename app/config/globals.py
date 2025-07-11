import os
import threading
from dotenv import load_dotenv
from app.config.settings_manager import SettingsManager

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

shutdown_event = threading.Event()

# Initialize settings_manager right away
settings_manager = SettingsManager()

obs_ready = threading.Event()

# Import services that need to be globally accessible
from app.services.tiktok_service import TikTokStreamer
from app.services.instagram_service import InstagramStreamer

tiktok_streamer = TikTokStreamer(cookies_file='cookies.json')
instagram_streamer = InstagramStreamer(testing=True)

# Define obs_client and discord_bot here as None initially.
obs_client = None
discord_bot = None
