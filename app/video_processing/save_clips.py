# app/video_processing/save_clips.py
import os
import time
from datetime import datetime
from app.config.globals import shutdown_event, settings_manager
from app.obs.obs_client import ObsClient
# from app.utils.streamdeck import update_streamdeck  # Implement or import if needed
# from app.video_processing.prepare_clips import prepare_clip # Implement or import if needed

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def save_replay(obs_client: ObsClient):
    relative_filename = datetime.now().strftime("%Y-%m-%d (%a)/%I-%M%p-vertical-replay")
    folder_path = os.path.dirname(relative_filename)
    root_folder = 'E:\\Episodes\\'  # Adjust path as needed
    full_folder_path = os.path.join(root_folder, folder_path)
    if not os.path.exists(full_folder_path):
        os.makedirs(full_folder_path)

    relative_filename_with_extension = relative_filename + '.mp4'
    full_filename = os.path.join(root_folder, relative_filename_with_extension)

    # The vendor request to save backtrack might differ in v5
    response = obs_client.send_request("CallVendorRequest", {
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

def capture_and_prepare(obs_client: ObsClient, port: int):
    filename = save_replay(obs_client)
    if settings_manager.get_setting('process'):
        if filename:
            # prepare_clip(filename, 'style1', settings_manager, port)
            # Implement prepare_clip as needed
            pass
        else:
            print("Failed to capture replay")
    else:
        if filename:
            with open(os.path.join(script_dir, 'logs', 'videopending.txt'), 'a') as file:
                file.write(filename + '\n')
            # update_streamdeck() # If needed
            print(f"Successfully added to processing queue: {filename}")
