# app/video_processing/orders.py
import os
import re
import json
import pytesseract
from app.config.globals import shutdown_event
from datetime import datetime

# File paths
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(script_dir, 'logs')
activity_file = os.path.join(logs_dir, 'activity.txt')

last_order = None

def ensure_files_exist():
    """Ensure the logs directory and activity.txt file exist"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            print(f"Created logs directory at: {logs_dir}")

        # Create activity.txt if it doesn't exist
        if not os.path.exists(activity_file):
            with open(activity_file, 'w') as f:
                f.write("")
            print(f"Created activity.txt at: {activity_file}")
    except Exception as e:
        print(f"Error creating necessary files: {e}")
        log_error(f"File creation error: {e}")

def log_error(error_message):
    """Log error messages to error_log.txt"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_log_path = os.path.join(logs_dir, 'error_log.txt')
        
        # Create error log if it doesn't exist
        if not os.path.exists(error_log_path):
            with open(error_log_path, 'w') as f:
                f.write(f"Error log created on {datetime.now()}\n")

        with open(error_log_path, 'a') as f:
            f.write(f"[{current_time}] {error_message}\n")
    except Exception as e:
        print(f"Error writing to error log: {e}")

def read_from_file(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return f.read()
        return ""
    except Exception as e:
        log_error(f"Error reading from {file_path}: {e}")
        return ""

def write_to_file(file_path, content, mode='w'):
    """Write content to file with error handling"""
    try:
        with open(file_path, mode) as f:
            f.write(content)
        return True
    except Exception as e:
        log_error(f"Error writing to {file_path}: {e}")
        return False

def add_activity(message, activity_type='order', broadcast=False, metric_type=None, metric_value=None):
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        activity_data = {
            "activity_type": activity_type,
            "timestamp": current_time,
            "broadcast": broadcast
        }
        
        if metric_type and metric_value:
            activity_data["metric_type"] = metric_type
            activity_data["metric_value"] = metric_value

        activity_line = f"{json.dumps(activity_data)} {message}\n"
        return write_to_file(activity_file, activity_line, mode='a')
    except Exception as e:
        log_error(f"Error adding activity: {e}")
        return False

def fix_order_errors(extracted_text):
    try:
        extracted_text = extracted_text.replace("!", "l")
        extracted_text = extracted_text.replace("(W)", "")
        extracted_text = re.sub(r'(Put|Call)\s+100\s+', r'\1 ', extracted_text)
        extracted_text = extracted_text.replace("\n", " ").replace("\r", " ")
        extracted_text = re.sub(r'\bBy\b', 'Buy', extracted_text)
        extracted_text = re.sub(' +', ' ', extracted_text)
        return extracted_text
    except Exception as e:
        log_error(f"Error fixing order text: {e}")
        return extracted_text

def find_nearest_order_line(existing_lines):
    try:
        for line in existing_lines:
            if line.startswith('{"activity_type":"order"'):
                return line
        return None
    except Exception as e:
        log_error(f"Error finding nearest order line: {e}")
        return None

def process_orders(cropped_frame):
    global last_order
    if shutdown_event.is_set():
        print("Process orders terminated due to shutdown signal.")
        return

    try:
        # Ensure necessary files exist
        ensure_files_exist()

        # Process the image
        extracted_text = pytesseract.image_to_string(cropped_frame, config='--psm 6').strip()
        
        # Validate the extracted text
        pattern = re.compile(r"([A-Z]{1,4}) (\$\d+(\.\d+)?)")
        match = pattern.match(extracted_text)
        if not match:
            return

        # Clean and process the text
        extracted_text = fix_order_errors(extracted_text)
        existing_text = read_from_file(activity_file).strip()
        existing_lines = existing_text.split('\n') if existing_text else []

        should_add_activity = True

        # Handle last order comparison
        if last_order is None:
            last_order = extracted_text
        elif last_order == extracted_text:
            return

        # Check for duplicates
        nearest_order_line = find_nearest_order_line(existing_lines)
        if nearest_order_line is not None:
            try:
                if '}' in nearest_order_line:
                    json_part, order_part = nearest_order_line.split('}', 1)
                    json_part += '}'

                    # Timestamp comparison
                    timestamp_pattern = r'\d{2}:\d{2}:\d{2} [A-Z]{3}'
                    existing_timestamp = re.search(timestamp_pattern, order_part)
                    extracted_timestamp = re.search(timestamp_pattern, extracted_text)
                    
                    if existing_timestamp and extracted_timestamp and existing_timestamp.group() == extracted_timestamp.group():
                        should_add_activity = False
            except Exception as e:
                log_error(f"Error processing order line: {e}")
                return

        # Add new activity if needed
        if should_add_activity:
            last_order = 'reset'
            if not add_activity(extracted_text, 'order'):
                log_error("Failed to add activity")

    except KeyboardInterrupt:
        print("Keyboard Interrupt in process_orders.")
        shutdown_event.set()
    except pytesseract.pytesseract.TesseractError as e:
        log_error(f"Tesseract Error: {e}")
        shutdown_event.set()
    except Exception as e:
        log_error(f"General error in process_orders: {e}")