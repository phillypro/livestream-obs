# app/services/stream_manager.py
import threading
from app.config.globals import tiktok_streamer, instagram_streamer

class StreamManager:
    def __init__(self):
        self.stream_thread = None

    def initialize_streams(self, stream_title, obs_client):
        """Start streams in sequence: Instagram first, then TikTok."""
        if self.stream_thread and self.stream_thread.is_alive():
            return  # Already initializing

        self.stream_thread = threading.Thread(
            target=self._init_streams_thread,
            args=(stream_title, obs_client),
            daemon=True
        )
        self.stream_thread.start()

    def _init_streams_thread(self, stream_title, obs_client):
        """Thread function to initialize streams in sequence."""
        try:
            # Start Instagram stream first
            print("Starting Instagram stream...")
            insta_url, insta_key = instagram_streamer.start_stream_with_title(stream_title, obs_client)
            if insta_url and insta_key:
                print("Instagram stream is live. Now starting TikTok stream...")
                # Now start TikTok
                tiktok_url, tiktok_key = tiktok_streamer.start_stream_with_title(stream_title, obs_client)
                if tiktok_url and tiktok_key:
                    print("TikTok stream started successfully.")
                else:
                    print("Failed to start TikTok stream.")
            else:
                print("Failed to start Instagram stream. Not starting TikTok stream.")
        except Exception as e:
            print(f"Error initializing streams: {e}")
