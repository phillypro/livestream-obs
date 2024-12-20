# app/services/stream_manager.py
import threading
from app.config.globals import tiktok_streamer, instagram_streamer

class StreamManager:
    def __init__(self):
        self.stream_thread = None
        
    def initialize_streams(self, stream_title, obs_client):
        """Start streams asynchronously in a separate thread"""
        if self.stream_thread and self.stream_thread.is_alive():
            return  # Already initializing streams
            
        self.stream_thread = threading.Thread(
            target=self._init_streams_thread,
            args=(stream_title, obs_client),
            daemon=True
        )
        self.stream_thread.start()
    
    def _init_streams_thread(self, stream_title, obs_client):
        """Thread function to initialize streams"""
        try:
            # Start TikTok stream
            tiktok_thread = threading.Thread(
                target=tiktok_streamer.start_stream_with_title,
                args=(stream_title, obs_client),
                daemon=True
            )
            tiktok_thread.start()
            
            # Start Instagram stream
            instagram_thread = threading.Thread(
                target=instagram_streamer.start_stream_with_title,
                args=(stream_title, obs_client),
                daemon=True
            )
            instagram_thread.start()
            
            # Optionally wait for completion if needed
            tiktok_thread.join()
            instagram_thread.join()
            
        except Exception as e:
            print(f"Error initializing streams: {e}")