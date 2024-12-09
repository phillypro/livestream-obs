# app/video_processing/charts.py
import os
import re
import pytesseract
from app.config.globals import shutdown_event

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fix_chart_errors(extracted_text):
    extracted_text = re.sub('[^a-zA-Z0-9$./: &]', '', extracted_text)
    extracted_text = re.sub(r'\bSminutes\b', '5 minutes', extracted_text)
    return extracted_text

def read_from_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read()
    return ""

def process_chart(cropped_frame):
    if shutdown_event.is_set():
        print("Process chart terminated due to shutdown signal.")
        return

    try:
        extracted_text = pytesseract.image_to_string(cropped_frame)
        extracted_text = fix_chart_errors(extracted_text)

        match = re.search(r'([A-Za-z]+) (.+?) (\d+)', extracted_text)
        if match:
            ticker = match.group(1)
            company_name = match.group(2)
            formatted_text = f"{company_name} ( ${ticker} )"

            existing_text = read_from_file(os.path.join(script_dir, 'logs', 'chart.txt'))
            existing_match = re.search(r'\( \$([A-Z]+) \)', existing_text)
            existing_ticker = existing_match.group(1) if existing_match else ""

            if ticker != existing_ticker:
                with open(os.path.join(script_dir, 'logs', 'chart.txt'), 'w') as f:
                    f.write(f"{formatted_text}\n")
                    print(f"Updated chart.txt with {formatted_text}")
    except (KeyboardInterrupt, pytesseract.pytesseract.TesseractError):
        shutdown_event.set()
        return
    except Exception as e:
        print(f"General error during Tesseract processing: {e}")
        return
