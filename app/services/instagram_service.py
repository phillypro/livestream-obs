# app/services/instagram_service.py
import os
import json
import time
import pyotp
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

INSTAGRAM_USERNAME_TEST = os.getenv('INSTAGRAM_USERNAME_TEST')
INSTAGRAM_PASSWORD_TEST = os.getenv('INSTAGRAM_PASSWORD_TEST')
INSTAGRAM_SEED = os.getenv('INSTAGRAM_SEED')

class InstagramStreamer:
    def __init__(self, testing=False):
        self.INSTAGRAM_USERNAME = INSTAGRAM_USERNAME_TEST
        self.INSTAGRAM_PASSWORD = INSTAGRAM_PASSWORD_TEST
        self.INSTAGRAM_SEED = INSTAGRAM_SEED
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.COOKIES_PATH = os.path.join(script_dir, 'tokens', 'instagram_live')
        os.makedirs(os.path.dirname(self.COOKIES_PATH), exist_ok=True)
        self.driver = None
        self.testing = testing

    def init_driver(self):
        options = webdriver.ChromeOptions()
        if not self.testing:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)

    def generate_2fa_code(self, seed):
        totp = pyotp.TOTP(seed)
        return totp.now()

    def save_cookies(self):
        os.makedirs(os.path.dirname(self.COOKIES_PATH), exist_ok=True)
        with open(self.COOKIES_PATH, 'w') as file:
            json.dump(self.driver.get_cookies(), file)

    def load_cookies(self):
        if os.path.exists(self.COOKIES_PATH):
            with open(self.COOKIES_PATH, 'r') as file:
                cookies = json.load(file)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            return True
        return False

    def login(self):
        self.driver.get("https://www.instagram.com/")
        if not self.load_cookies():
            self.driver.get("https://www.instagram.com/accounts/login/")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            username_field.send_keys(self.INSTAGRAM_USERNAME)
            password_field.send_keys(self.INSTAGRAM_PASSWORD)
            password_field.send_keys(Keys.RETURN)

            # Try 2FA
            try:
                verification_field = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.NAME, "verificationCode"))
                )
                verification_code = self.generate_2fa_code(self.INSTAGRAM_SEED)
                verification_field.send_keys(verification_code)
                verification_field.send_keys(Keys.RETURN)
            except:
                pass

            self.handle_notification_popup()
            self.save_cookies()
        else:
            self.driver.refresh()
            self.handle_notification_popup()

    def handle_notification_popup(self):
        try:
            not_now_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Not Now')]"))
            )
            not_now_button.click()
        except:
            pass

    def start_stream_with_title(self, title, ws):
        self.init_driver()
        self.login()

        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Create')]"))
        ).click()

        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Live video')]"))
        ).click()

        title_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "live-creation-modal-create-screen-title-input"))
        )
        title_field.send_keys(title)

        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Audience')]"))
        ).click()

        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Public')]"))
        ).click()

        # Next
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Next')]"))
        ).click()

        stream_url = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "live-creation-modal-start-pane-stream-url"))
        ).get_attribute('value')

        stream_key = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "live-creation-modal-start-pane-stream-key"))
        ).get_attribute('value')

        self.updateStreamDetails(stream_key, stream_url, ws, index=0)
        self.startStream(ws, index=0)

        self.wait_for_feed_signal_and_go_live()
        self.close()
        print("Instagram Stream is live! Browser closed.")

        return stream_url, stream_key

    def wait_for_feed_signal_and_go_live(self):
        go_live_button = WebDriverWait(self.driver, 300).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//h4[contains(text(), 'Go live')]]"))
        )
        self.driver.execute_script("arguments[0].click();", go_live_button)

    def updateStreamDetails(self, stream_key, stream_url, ws, index=0):
        update_stream_key = {
            "op": 6,
            "d": {
                "requestType": "CallVendorRequest",
                "requestId": f"update_Stream_Key_command_{index}",
                "requestData": {
                    "vendorName": "aitum-vertical-canvas",
                    "requestType": "update_stream_key",
                    "requestData": {
                        "stream_key": stream_key,
                        "index": index
                    },
                },
            },
        }

        update_stream_server = {
            "op": 6,
            "d": {
                "requestType": "CallVendorRequest",
                "requestId": f"update_Stream_Server_command_{index}",
                "requestData": {
                    "vendorName": "aitum-vertical-canvas",
                    "requestType": "update_stream_server",
                    "requestData": {
                        "stream_server": stream_url,
                        "index": index
                    },
                },
            },
        }

        ws.send(json.dumps(update_stream_key))
        print(f'Stream Key for index {index} updated successfully')

        ws.send(json.dumps(update_stream_server))
        print(f'Stream Server for index {index} updated successfully')

    def startStream(self, ws, index=0):
        start_streaming = {
            "op": 6,
            "d": {
                "requestType": "CallVendorRequest",
                "requestId": f"start_streaming_command_{index}",
                "requestData": {
                    "vendorName": "aitum-vertical-canvas",
                    "requestType": "start_streaming"
                },
            },
        }
        ws.send(json.dumps(start_streaming))
        print(f'Live Stream started for index {index}')

    def close(self):
        if self.driver:
            self.driver.quit()
