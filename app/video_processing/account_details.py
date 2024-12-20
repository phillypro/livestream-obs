# video_processing/account_details.py

import os
import re
import json
import pytesseract
from datetime import datetime
from app.config.globals import shutdown_event, tiktok_streamer, instagram_streamer, settings_manager, obs_ready
from app.obs.obs_client import ObsClient
from app.services.stream_manager import StreamManager


# File paths
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logs_dir = os.path.join(script_dir, 'logs')
required_files = [
    'daysPL.txt',
    'openPL.txt',
    'optionsBP.txt',
    'buyingPower.txt',
    'marketValue.txt',
    'totalAccountValue.txt',
    'error_log.txt'
]

global_account_details = {
    'daysPL': {'amount': "0.00", 'percentage': "0.00%"},
    'openPL': {'amount': "0.00", 'percentage': "0.00%", 'awards': []},
    'optionsBP': 0.00,
    'buyingPower': 0.00,
    'marketValue': 0.00,
    'totalAccountValue': 0.00
}
global_profit_mode = False
stream_manager = StreamManager()


def ensure_files_exist():
    """Ensure the logs directory and all required files exist"""
    try:
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        for filename in required_files:
            file_path = os.path.join(logs_dir, filename)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    if filename == 'error_log.txt':
                        f.write(f"Error log created on {datetime.now()}\n")
                    else:
                        f.write("0.00\n")
    except Exception as e:
        log_error(f"File creation error: {e}")

def log_error(error_message):
    """Log error messages to error_log.txt"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(logs_dir, 'error_log.txt'), 'a') as f:
            f.write(f"[{current_time}] {error_message}\n")
    except Exception as e:
        print(f"Error writing to error log: {e}")

def set_source_color(color, inputName, obs_client: ObsClient):
    try:
        obs_client.send_request("SetInputSettings", {
            "inputName": inputName,
            "inputSettings": {
                "color": color
            }
        })
    except Exception as e:
        log_error(f"Error setting source color: {e}")

def toggle_profit_mode(profit_mode: bool, obs_client: ObsClient):
    global global_profit_mode
    if not obs_ready.is_set():
        log_error("Cannot toggle profit mode - OBS not ready")
        return

    if obs_client is None:
        from app.main import obs_client as main_obs_client
        obs_client = main_obs_client
        if obs_client is None:
            log_error("Cannot toggle profit mode - OBS client not initialized")
            return

    # Only proceed if there's an actual change
    if global_profit_mode == profit_mode:
        return

    profit_mode_filter = 'profit on' if profit_mode else 'profit off'
    try:
        obs_client.send_request("CallVendorRequest", {
            "vendorName": "AdvancedSceneSwitcher",
            "requestType": "AdvancedSceneSwitcherMessage",
            "requestData": {
                "message": profit_mode_filter
            }
        })
        global_profit_mode = profit_mode

        # Start streams asynchronously when entering profit mode
        if profit_mode:
            stream_title = 'Live Stock Options Trading $$$'
            stream_manager.initialize_streams(stream_title, obs_client)
            
    except Exception as e:
        log_error(f"Error toggling profit mode: {e}")

def correct_ocr_errors(line):
    return re.sub(r'(\d),00(\D|$)', r'\1.00\2', line)

def format_percentage_line(line):
    if '-' in line:
        pattern = r'- (\d+(\.\d+)?%)'
        formatted_line = re.sub(pattern, r'-\1', line)
    else:
        pattern = r' (\d+(\.\d+)?%)'
        formatted_line = re.sub(pattern, r'\1', line)
    return formatted_line

def write_to_file(file_path, content):
    """Write content to file with error handling"""
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        log_error(f"Error writing to {file_path}: {e}")
        return False

def process_pl(amount, percentage, file_name, overlay_name, data_key, obs_client: ObsClient):
    global global_account_details
    try:
        cleaned_money = float(amount.replace(",", "").replace("+", ""))
        multiplier = settings_manager.get_setting('multiplier')

        if cleaned_money == 0.0:
            content = f"{amount} {percentage}\n"
            if write_to_file(file_name, content):
                set_source_color(4291936183, overlay_name, obs_client)
                global_account_details[data_key]['amount'] = amount
                global_account_details[data_key]['percentage'] = percentage
        else:
            modified_money = cleaned_money * multiplier
            modified_money_str = f"{modified_money:+,.2f}"
            content = f"{modified_money_str} {percentage}\n"
            
            if write_to_file(file_name, content):
                global_account_details[data_key]['amount'] = modified_money_str
                global_account_details[data_key]['percentage'] = percentage

                color = 4280423350 if cleaned_money < 0 else 4288463367
                set_source_color(color, overlay_name, obs_client)
    except Exception as e:
        log_error(f"Error processing PL for {data_key}: {e}")

def process_account(cropped_frame, obs_client: ObsClient = None):
    global global_account_details
    
    if shutdown_event.is_set():
        return

    try:
        ensure_files_exist()

        # Add this check for OBS readiness
        if not obs_ready.is_set():
            log_error("Cannot process account - OBS not ready")
            return

        if obs_client is None:
            from app.main import obs_client as main_obs_client
            obs_client = main_obs_client
            if obs_client is None:
                log_error("Cannot process account - OBS client not initialized")
                return

        extracted_text = pytesseract.image_to_string(cropped_frame)
        lines = [line for line in extracted_text.split('\n') if line.strip()]

        data_order = [
            'totalAccountValue',
            'marketValue',
            'buyingPower',
            'optionsBP',
            'openPL',
            'daysPL'
        ]
        
        lines = lines[:len(data_order)]
        pattern = r'[$]?([+-]?[\d,]+\.\d{2})\s*([$]?[+-]?\d+\.\d+%)?'

        for i, line in enumerate(lines):
            try:
                data_type = data_order[i]
                if data_type == 'openPL':
                    line = correct_ocr_errors(line)
                    line = format_percentage_line(line)
                
                line = re.sub(r"\b[a-zA-Z]+\b", "", line)
                match = re.findall(pattern, line)

                if match:
                    amount, percentage = match[0]
                    if data_type in ['openPL', 'daysPL']:
                        file_path = os.path.join(logs_dir, f'{data_type}.txt')
                        overlay_name = "Profit Overlay" if data_type == 'openPL' else "Daily Profit Overlay"
                        process_pl(amount, percentage, file_path, overlay_name, data_type, obs_client)
                    else:
                        amount_value = float(amount.replace(',', ''))
                        modified_value = amount_value * settings_manager.get_setting('multiplier')
                        global_account_details[data_type] = f"{modified_value:.2f}"
                        file_path = os.path.join(logs_dir, f'{data_type}.txt')
                        write_to_file(file_path, f"${modified_value:,.2f}")
            except Exception as e:
                log_error(f"Error processing line {i} ({data_type}): {e}")

        # Check for awards reset condition
        if float(global_account_details['marketValue']) == 0:
            if "profit_mode_active" in global_account_details['openPL']['awards']:
                toggle_profit_mode(False, obs_client)
            global_account_details['openPL']['awards'] = []

    except KeyboardInterrupt:
        shutdown_event.set()
    except pytesseract.pytesseract.TesseractError as e:
        log_error(f"Tesseract Error: {e}")
        shutdown_event.set()
    except Exception as e:
        log_error(f"General error in process_account: {e}")
