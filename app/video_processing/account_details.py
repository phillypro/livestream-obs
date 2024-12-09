# app/video_processing/account_details.py
import os
import re
import json
import pytesseract
from datetime import datetime
from app.config.globals import shutdown_event, tiktok_streamer, instagram_streamer, settings_manager
from app.obs.obs_client import ObsClient
# We assume obs_client is accessible when calling these functions. 
# If needed, you can import obs_client from main or pass it as a parameter.
# from app.main import obs_client # If needed, or pass it in as an argument.

script_dir = os.path.dirname(os.path.abspath(__file__))

global_account_details = {
    'daysPL': {'amount': "0.00", 'percentage': "0.00%"},
    'openPL': {'amount': "0.00", 'percentage': "0.00%", 'awards': []},
    'optionsBP': 0.00,
    'buyingPower': 0.00,
    'marketValue': 0.00,
    'totalAccountValue': 0.00
}
global_profit_mode = False

def set_source_color(color, inputName, obs_client: ObsClient):
    # Send request to OBS to set input color
    response = obs_client.send_request("SetInputSettings", {
        "inputName": inputName,
        "inputSettings": {
            "color": color
        }
    })
    # Logging response if needed
    # print(response)

def toggle_profit_mode(profit_mode: bool, obs_client: ObsClient):
    global global_profit_mode
    if global_profit_mode == profit_mode:
        return

    profit_mode_filter = 'profit on' if profit_mode else 'profit off'
    response = obs_client.send_request("CallVendorRequest", {
        "vendorName": "AdvancedSceneSwitcher",
        "requestType": "AdvancedSceneSwitcherMessage",
        "requestData": {
            "message": profit_mode_filter
        }
    })
    global_profit_mode = profit_mode

    stream_title = 'Live Stock Options Trading $$$'
    tiktok_streamer.start_stream_with_title(stream_title, obs_client)
    instagram_streamer.start_stream_with_title(stream_title, obs_client)

def correct_ocr_errors(line):
    return re.sub(r'(\d),00(\D|$)', r'\1.00\2', line)

def process_pl(amount, percentage, file_name, overlay_name, data_key, obs_client: ObsClient):
    global global_account_details
    cleaned_money = float(amount.replace(",", "").replace("+", ""))

    with open(file_name, 'w') as f:
        if cleaned_money == 0.0:
            f.write(f"{amount} {percentage}\n")
            set_source_color(4291936183, overlay_name, obs_client)
            global_account_details[data_key]['amount'] = amount
            global_account_details[data_key]['percentage'] = percentage
        else:
            modified_money = cleaned_money * settings_manager.get_setting('multiplier')
            modified_money_str = f"{modified_money:+,.2f}"
            f.write(f"{modified_money_str} {percentage}\n")
            global_account_details[data_key]['amount'] = modified_money_str
            global_account_details[data_key]['percentage'] = percentage

            if cleaned_money < 0:
                set_source_color(4280423350, overlay_name, obs_client)  # Red
            else:
                set_source_color(4288463367, overlay_name, obs_client)  # Green

def format_percentage_line(line):
    if '-' in line:
        pattern = r'- (\d+(\.\d+)?%)'
        formatted_line = re.sub(pattern, r'-\1', line)
    else:
        pattern = r' (\d+(\.\d+)?%)'
        formatted_line = re.sub(pattern, r'\1', line)
    return formatted_line

def process_account(cropped_frame, obs_client: ObsClient = None):
    global global_account_details
    # Ensure obs_client is passed in or accessible. If main loop calls process_account,
    # it should provide obs_client as a parameter or you have a global obs_client accessible.
    if obs_client is None:
        # If obs_client is not provided, import it or handle error
        from app.main import obs_client as main_obs_client
        obs_client = main_obs_client

    if shutdown_event.is_set():
        print("Process account terminated due to shutdown signal.")
        return

    try:
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
            data_type = data_order[i]
            if data_type == 'openPL':
                line = correct_ocr_errors(line)
                line = format_percentage_line(line)
            line = re.sub(r"\b[a-zA-Z]+\b", "", line)
            match = re.findall(pattern, line)

            if match:
                amount, percentage = match[0]
                if data_type in ['openPL', 'daysPL']:
                    file_path = os.path.join(script_dir, 'logs', f'{data_type}.txt')
                    overlay_name = "Profit Overlay" if data_type == 'openPL' else "Daily Profit Overlay"
                    process_pl(amount, percentage, file_path, overlay_name, data_type, obs_client)
                else:
                    amount_value = float(amount.replace(',', ''))
                    modified_value = amount_value * settings_manager.get_setting('multiplier')
                    global_account_details[data_type] = f"{modified_value:.2f}"
                    file_path = os.path.join(script_dir, 'logs', f'{data_type}.txt')
                    with open(file_path, 'w') as f:
                        f.write(f"${modified_value:,.2f}")
            else:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(os.path.join(script_dir, 'logs', 'error_log.txt'), 'a') as f:
                    f.write(f"[{current_time}] No match found error: {lines}\n")

        # Check for awards reset condition.
        if float(global_account_details['marketValue']) == 0:
            if "profit_mode_active" in global_account_details['openPL']['awards']:
                toggle_profit_mode(False, obs_client)
            global_account_details['openPL']['awards'] = []
    except KeyboardInterrupt:
        print("Keyboard Interrupt in process_account.")
        shutdown_event.set()
    except pytesseract.pytesseract.TesseractError:
        shutdown_event.set()
    except Exception as e:
        # Handle or log the error
        pass
