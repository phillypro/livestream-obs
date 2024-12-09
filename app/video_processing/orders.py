# app/video_processing/orders.py
import os
import re
import pytesseract
from app.config.globals import shutdown_event
from datetime import datetime

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
last_order = None

def read_from_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read()
    return ""

def add_activity(message, activity_type='order', broadcast=False, metric_type=None, metric_value=None):
    # Implement or import from the correct module
    # This function logs activity, possibly updates a file or sends a message to Discord, etc.
    pass

def fix_order_errors(extracted_text):
    extracted_text = extracted_text.replace("!", "l")
    extracted_text = extracted_text.replace("(W)", "")
    extracted_text = re.sub(r'(Put|Call)\s+100\s+', r'\1 ', extracted_text)
    extracted_text = extracted_text.replace("\n", " ").replace("\r", " ")
    extracted_text = re.sub(r'\bBy\b', 'Buy', extracted_text)
    extracted_text = re.sub(' +', ' ', extracted_text)
    return extracted_text

def find_nearest_order_line(existing_lines):
    for line in existing_lines:
        if line.startswith('{"activity_type":"order"'):
            return line
    return None

def process_orders(cropped_frame):
    global last_order
    if shutdown_event.is_set():
        print("Process orders terminated due to shutdown signal.")
        return

    try:
        extracted_text = pytesseract.image_to_string(cropped_frame, config='--psm 6').strip()
        pattern = re.compile(r"([A-Z]{1,4}) (\$\d+(\.\d+)?)")
        match = pattern.match(extracted_text)
        if not match:
            return

        extracted_text = fix_order_errors(extracted_text)
        existing_text = read_from_file(os.path.join(script_dir, 'logs', 'activity.txt')).strip()
        existing_lines = existing_text.split('\n') if existing_text else []

        should_add_activity = True

        if last_order is None:
            last_order = extracted_text

        if last_order == extracted_text:
            return

        nearest_order_line = find_nearest_order_line(existing_lines)
        if nearest_order_line is not None:
            # Attempt to parse the line
            if '}' in nearest_order_line:
                json_part, order_part = nearest_order_line.split('}', 1)
                json_part += '}'
                try:
                    # We assume json_part is valid JSON
                    # If it's not, handle gracefully
                    # nearest_order_data = json.loads(json_part)
                    pass
                except:
                    return

                # Check timestamps
                timestamp_pattern = r'\d{2}:\d{2}:\d{2} [A-Z]{3}'
                existing_timestamp = re.search(timestamp_pattern, order_part)
                extracted_timestamp = re.search(timestamp_pattern, extracted_text)
                if existing_timestamp and extracted_timestamp and existing_timestamp.group() == extracted_timestamp.group():
                    # If timestamps match, do not add activity
                    should_add_activity = False

        if should_add_activity:
            last_order = 'reset'
            add_activity(extracted_text, 'order')

    except (KeyboardInterrupt, pytesseract.pytesseract.TesseractError):
        shutdown_event.set()
        return
    except Exception as e:
        print(f"General error during Tesseract processing: {e}")
        return
