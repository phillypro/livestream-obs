# app/video_processing/save_clips.py
import os
import time
from datetime import datetime
from app.config.globals import shutdown_event, settings_manager
from app.obs.obs_client import ObsClient

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(script_dir, 'logs')
pending_file = os.path.join(logs_dir, 'videopending.txt')
root_folder = 'E:\\Episodes\\'  # Adjust path as needed

def ensure_pending_file():
    """Ensure the logs directory and videopending.txt exist"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            print(f"Created logs directory at: {logs_dir}")

        # Create videopending.txt if it doesn't exist
        if not os.path.exists(pending_file):
            with open(pending_file, 'w') as f:
                f.write("")
            print(f"Created videopending.txt at: {pending_file}")
        
        return True
    except Exception as e:
        print(f"Error creating videopending.txt: {e}")
        return False

def add_to_pending(filename):
    """Add filename to videopending.txt"""
    try:
        with open(pending_file, 'a') as f:
            f.write(filename + '\n')
        return True
    except Exception as e:
        print(f"Error writing to videopending.txt: {e}")
        return False

def save_replay(obs_client: ObsClient):
    relative_filename = datetime.now().strftime("%Y-%m-%d (%a)/%I-%M%p-vertical-replay")
    folder_path = os.path.dirname(relative_filename)
    full_folder_path = os.path.join(root_folder, folder_path)
    if not os.path.exists(full_folder_path):
        os.makedirs(full_folder_path)

    relative_filename_with_extension = relative_filename + '.mp4'
    full_filename = os.path.join(root_folder, relative_filename_with_extension)

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
    ensure_pending_file()  # Ensure the file exists before we try to use it
    
    filename = save_replay(obs_client)
    if filename is None:
        print("Failed to capture replay")
        return

    if settings_manager.get_setting('process'):
        if filename:
            # prepare_clip(filename, 'style1', settings_manager, port)
            # Implement prepare_clip as needed
            pass
        else:
            print("Failed to capture replay")
    else:
        if filename:
            if add_to_pending(filename):
                # update_streamdeck()  # If needed
                print(f"Successfully added to processing queue: {filename}")
            else:
                print(f"Failed to add to processing queue: {filename}")