# app/main.py
import os
import sys
import signal
import threading
import time
from dotenv import load_dotenv

try:
    import obspython as obs
    obs_available = True
except ImportError:
    print("OBS Python bindings not available.")
    obs_available = False

from app.config.settings_manager import SettingsManager
from app.obs.obs_client import ObsClient
from app.web.server import start_flask_app, stop_flask_app
from app.services.discord_bot import DiscordBot
from app.video_processing.capture import FrameCapturer
from app.video_processing.account_details import process_account
from app.video_processing.orders import process_orders
from app.video_processing.charts import process_chart
from app.video_processing.awards import profit_awards
from app.config.globals import shutdown_event, tiktok_streamer, instagram_streamer

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

obs_client = None
discord_bot = None
discord_thread = None
frame_capturer = None
loop_thread = None

def handle_shutdown_signal(signum, frame):
    if obs_available and hasattr(obs, 'script_log'):
        obs.script_log(obs.LOG_INFO, f"Received shutdown signal: {signum}")
    shutdown_event.set()
    graceful_shutdown()

def graceful_shutdown():
    global obs_client, discord_bot, frame_capturer
    if obs_available and hasattr(obs, 'script_log'):
        obs.script_log(obs.LOG_INFO, "Shutting down application gracefully...")

    # Stop Flask
    stop_flask_app()

    # Stop Discord bot
    if discord_bot:
        discord_bot.stop()

    # Disconnect OBS
    if obs_client:
        obs_client.disconnect()

    # Release camera
    if frame_capturer:
        frame_capturer.release()

    time.sleep(1)

    if obs_available and hasattr(obs, 'script_log'):
        obs.script_log(obs.LOG_INFO, "Shutdown complete.")

def loop_function():
    while not shutdown_event.is_set():
        cropped_frame = frame_capturer.capture_frame(600, 230, 1100, 1100)
        if cropped_frame is not None:
            process_account(cropped_frame)

        cropped_frame = frame_capturer.capture_frame(0, 100, 1920, 190)
        if cropped_frame is not None:
            process_orders(cropped_frame)

        cropped_frame = frame_capturer.capture_frame(0, 0, 1400, 100)
        if cropped_frame is not None:
            process_chart(cropped_frame)

        profit_awards()

        time.sleep(0.3)

def on_obs_ready():
    print("OBS is ready, starting Flask app...")

    def on_version_received(version_info):
        if version_info:
            print(f"OBS-WebSocket version info: {version_info}")
        else:
            print("Failed to retrieve OBS-WebSocket version info.")

    obs_client.get_version_async(on_version_received)

    from app.config import globals
    socketio_instance = start_flask_app(globals.settings_manager)
    if not socketio_instance:
        print("Failed to start Flask application")
        graceful_shutdown()
        return

    if DISCORD_BOT_TOKEN:
        discord_bot_instance = DiscordBot(token=DISCORD_BOT_TOKEN, socketio=socketio_instance)
        discord_thread_instance = threading.Thread(target=discord_bot_instance.run, name="DiscordBotThread", daemon=True)
        discord_thread_instance.start()

        globals()['discord_bot'] = discord_bot_instance
        globals()['discord_thread'] = discord_thread_instance
    else:
        print("DISCORD_BOT_TOKEN not provided, skipping Discord bot startup.")

    loop_thread_instance = threading.Thread(target=loop_function, name="LoopThread", daemon=True)
    loop_thread_instance.start()

def on_connection_failed():
    print("Failed to connect to OBS")
    graceful_shutdown()

def main():
    global obs_client, discord_bot, discord_thread, frame_capturer, loop_thread

    # Create settings_manager here
    from app.config.globals import settings_manager as global_settings_manager
    local_settings_manager = SettingsManager()
    from app.config import globals
    globals.settings_manager = local_settings_manager

    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    frame_capturer = FrameCapturer(camera_index=8, width=1920, height=1080)

    print("Initializing OBS client...")
    obs_client = ObsClient()
    obs_client.on_ready_callback = on_obs_ready
    obs_client.on_connection_failed_callback = on_connection_failed
    obs_client.start_connection()

    print("Application initialization started...")

    if obs_available and hasattr(obs, 'script_unload'):
        def script_unload():
            handle_shutdown_signal(None, None)
        obs.script_unload = script_unload

if __name__ == "__main__":
    main()
