# app/utils/activity.py
from datetime import datetime
import json
import os
from app.services.discord_service import prepare_message

# Adjust paths as necessary:
# Assuming logs directory is still at project_root/logs
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(script_dir, 'logs')

def add_activity(message, activity_type, broadcast=True, awardType=None, value=None):
    activity_file = os.path.join(logs_dir, 'activity.txt')

    # Ensure the logs directory and activity.txt exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    if not os.path.exists(activity_file):
        # If activity.txt doesn't exist, create it
        with open(activity_file, 'w') as f:
            f.write("")

    with open(activity_file, 'r') as f:
        existing_lines = f.readlines()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    activity_object = {
        'activity_type': activity_type,
        'timestamp': timestamp
    }

    if awardType is not None:
        activity_object['awardType'] = awardType

    if value is not None:
        activity_object['value'] = value

    # Convert the dictionary to a JSON string and remove the spaces after the colons
    activity_json = json.dumps(activity_object, separators=(',', ':'))

    new_line = f"{activity_json} {message}\n"

    existing_lines.insert(0, new_line)

    with open(activity_file, 'w') as f:
        f.writelines(existing_lines)

    # Send a discord message
    if broadcast:
        prepare_message(message, activity_type)
