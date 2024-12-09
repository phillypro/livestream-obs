# app/video_processing/charts.py
import os
import re
import pytesseract
from app.config.globals import shutdown_event

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(script_dir, 'logs')
chart_file = os.path.join(logs_dir, 'chart.txt')

def ensure_files_exist():
    """Ensure the logs directory and chart.txt file exist"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            print(f"Created logs directory at: {logs_dir}")

        # Create chart.txt if it doesn't exist
        if not os.path.exists(chart_file):
            with open(chart_file, 'w') as f:
                f.write("")
            print(f"Created chart.txt at: {chart_file}")
    except Exception as e:
        print(f"Error creating necessary files: {e}")

def fix_chart_errors(extracted_text):
    extracted_text = re.sub('[^a-zA-Z0-9$./: &]', '', extracted_text)
    extracted_text = re.sub(r'\bSminutes\b', '5 minutes', extracted_text)
    return extracted_text

def read_from_file(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return f.read()
        return ""
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""

def write_to_file(file_path, content):
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")
        return False

def process_chart(cropped_frame):
    if shutdown_event.is_set():
        print("Process chart terminated due to shutdown signal.")
        return

    try:
        # Ensure necessary files exist before processing
        ensure_files_exist()

        extracted_text = pytesseract.image_to_string(cropped_frame)
        extracted_text = fix_chart_errors(extracted_text)

        match = re.search(r'([A-Za-z]+) (.+?) (\d+)', extracted_text)
        if match:
            ticker = match.group(1)
            company_name = match.group(2)
            formatted_text = f"{company_name} ( ${ticker} )"

            existing_text = read_from_file(chart_file)
            existing_match = re.search(r'\( \$([A-Z]+) \)', existing_text)
            existing_ticker = existing_match.group(1) if existing_match else ""

            if ticker != existing_ticker:
                if write_to_file(chart_file, f"{formatted_text}\n"):
                    print(f"Updated chart.txt with {formatted_text}")
                else:
                    print("Failed to update chart.txt")

    except (KeyboardInterrupt, pytesseract.pytesseract.TesseractError) as e:
        print(f"Tesseract error: {e}")
        shutdown_event.set()
        return
    except Exception as e:
        print(f"General error during Tesseract processing: {e}")
        return