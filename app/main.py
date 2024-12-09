# app/main.py
import os
import sys
import signal
import threading
import time

# Attempt to import OBS if available
obs_available = False
try:
    import obspython as obs
    obs_available = True
except ImportError:
    print("OBS Python bindings not available.")
    obs_available = False

from app.config.globals import shutdown_event
from app.config.settings_manager import SettingsManager
from app.obs.obs_client import ObsClient
from app.web.server import start_flask_app, stop_flask_app

obs_client = None
flask_thread = None
settings_manager = None

def handle_shutdown_signal(signum, frame):
    if obs_available:
        obs.script_log(obs.LOG_INFO, f"Received shutdown signal: {signum}")
    shutdown_event.set()
    graceful_shutdown()

def graceful_shutdown():
    global obs_client, flask_thread
    if obs_available:
        obs.script_log(obs.LOG_INFO, "Shutting down application gracefully...")
    
    # First stop the Flask app
    stop_flask_app()
    
    # Then disconnect OBS
    if obs_client:
        obs_client.disconnect()
    
    # Wait a moment to ensure everything is cleaned up
    time.sleep(1)
    
    if obs_available:
        obs.script_log(obs.LOG_INFO, "Shutdown complete.")

def main():
    global obs_client, flask_thread, settings_manager
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    settings_manager = SettingsManager()

    def on_obs_ready():
        """Callback when OBS is ready"""
        print("OBS is ready, starting Flask app...")
        
        def on_version_received(version_info):
            if version_info:
                print(f"OBS-WebSocket version info: {version_info}")
            else:
                print("Failed to retrieve OBS-WebSocket version info.")
        
        # Get version info asynchronously
        obs_client.get_version_async(on_version_received)
        
        # Start Flask app
        if not start_flask_app(settings_manager):
            print("Failed to start Flask application")
            graceful_shutdown()

    def on_connection_failed():
        """Callback when OBS connection fails"""
        print("Failed to connect to OBS")
        graceful_shutdown()

    # Initialize OBS client
    print("Initializing OBS client...")
    obs_client = ObsClient()
    obs_client.on_ready_callback = on_obs_ready
    obs_client.on_connection_failed_callback = on_connection_failed
    
    # Start connection process (non-blocking)
    obs_client.start_connection()

    print("Application initialization started...")

if __name__ == "__main__":
    main()