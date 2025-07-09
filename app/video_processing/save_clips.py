# app/video_processing/save_clips.py
import os
import time
from datetime import datetime
from app.config.globals import shutdown_event, settings_manager
from app.obs.obs_client import ObsClient

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(script_dir, 'logs')
root_folder = os.getenv("EPISODES_FOLDER_PATH", 'E:\\Episodes\\')



def save_replay(obs_client: ObsClient):
    relative_filename = datetime.now().strftime("%Y-%m-%d (%a)/%I-%M%p-vertical-replay")
    folder_path = os.path.dirname(relative_filename)
    full_folder_path = os.path.join(root_folder, folder_path)
    if not os.path.exists(full_folder_path):
        os.makedirs(full_folder_path)

    relative_filename_with_extension = relative_filename + '.mp4'
    full_filename = os.path.join(root_folder, relative_filename_with_extension)

    # --- FIX: Use the synchronous _send_request_internal to wait for a response ---
    response = obs_client._send_request_internal("CallVendorRequest", {
        "vendorName": "aitum-vertical-canvas",
        "requestType": "save_backtrack",
        "requestData": {"filename": relative_filename}
    })

    if response is None:
        print("Replay save request failed")
        return None

    timeout = 60
    start_time = time.time()
    while not os.path.exists(full_filename):
        time.sleep(1)
        if time.time() - start_time > timeout:
            print("Timeout reached. File not found.")
            return None

    print('Replay saved successfully')
    return full_filename