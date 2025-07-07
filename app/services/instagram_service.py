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

# Assuming settings_manager is available globally
# If not, adjust the import according to your project's structure
from app.config.globals import settings_manager

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

# Credentials loading depending on test or not is assumed done outside
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
INSTAGRAM_USERNAME_TEST = os.getenv('INSTAGRAM_USERNAME_TEST')
INSTAGRAM_PASSWORD_TEST = os.getenv('INSTAGRAM_PASSWORD_TEST')
INSTAGRAM_SEED = os.getenv('INSTAGRAM_SEED')

class InstagramStreamer:
    def __init__(self, testing=False):
        """
        Initializes the InstagramStreamer.

        If testing=True, use test credentials.
        If testing=False, use production credentials.
        """
        if testing:
            self.INSTAGRAM_USERNAME = INSTAGRAM_USERNAME_TEST
            self.INSTAGRAM_PASSWORD = INSTAGRAM_PASSWORD_TEST
        else:
            self.INSTAGRAM_USERNAME = INSTAGRAM_USERNAME
            self.INSTAGRAM_PASSWORD = INSTAGRAM_PASSWORD

        self.INSTAGRAM_SEED = INSTAGRAM_SEED

        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.COOKIES_PATH = os.path.join(script_dir, 'tokens', 'instagram_live')
        os.makedirs(os.path.dirname(self.COOKIES_PATH), exist_ok=True)

        self.driver = None
        self.testing = testing

    def init_driver(self):
        options = webdriver.ChromeOptions()
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
                content = file.read().strip()
                if not content:
                    # Empty file
                    return False
                try:
                    cookies = json.loads(content)
                except json.JSONDecodeError:
                    # Not valid JSON
                    return False

                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                return True
        return False

    def login(self):
        # Go to Instagram homepage
        self.driver.get("https://www.instagram.com/")
        
        # If cookies are available and valid, just refresh and check if we're logged in
        if self.load_cookies():
            self.driver.refresh()
            if self.is_user_logged_in():
                self.handle_notification_popup()
                return
            else:
                # If not logged in despite cookies, clear them and do a fresh login
                self.driver.delete_all_cookies()

        # Do a fresh login
        self.driver.get("https://www.instagram.com/accounts/login/")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field = self.driver.find_element(By.NAME, "username")
        password_field = self.driver.find_element(By.NAME, "password")
        username_field.send_keys(self.INSTAGRAM_USERNAME)
        password_field.send_keys(self.INSTAGRAM_PASSWORD)
        password_field.send_keys(Keys.RETURN)

        # Attempt 2FA if needed
        try:
            verification_field = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.NAME, "verificationCode"))
            )
            verification_code = self.generate_2fa_code(self.INSTAGRAM_SEED)
            verification_field.send_keys(verification_code)
            verification_field.send_keys(Keys.RETURN)
        except:
            pass

        # Wait until we can see the "Create" button, which should mean the user is logged in successfully
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Create')]"))
        )

        self.handle_notification_popup()
        self.save_cookies()

    def is_user_logged_in(self):
        # Check if "Create" button is visible, which we assume means the user is logged in
        try:
            self.driver.find_element(By.XPATH, "//a[contains(., 'Create')]")
            return True
        except:
            return False

    def handle_notification_popup(self):
        # Some accounts will show a "Turn on Notifications" popup; let's skip it
        try:
            not_now_button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Not Now')]"))
            )
            not_now_button.click()
        except:
            pass

    def start_stream_with_title(self, title, obs_client):
        # Check if go_live is enabled before doing anything
        if not settings_manager.get_setting('go_live'):
            print("Go live is disabled. Not starting Instagram stream.")
            return None, None

        self.init_driver()
        self.login()

        print("Attempting to find 'Create' button...")
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Create')]"))
        ).click()

        print("Clicking 'Live video'...")
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Live video')]"))
        ).click()

        print("Entering title...")
        title_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "live-creation-modal-create-screen-title-input"))
        )
        title_field.send_keys(title)

        print("Setting audience to Public...")
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Audience')]"))
        ).click()

        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Public')]"))
        ).click()

        print("Clicking 'Next'...")
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Next')]"))
        ).click()

        print("Retrieving stream URL and key...")
        stream_url = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "live-creation-modal-start-pane-stream-url"))
        ).get_attribute('value')

        stream_key = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "live-creation-modal-start-pane-stream-key"))
        ).get_attribute('value')

        # we can safely update OBS with the stream details and start the OBS stream.
        self.updateStreamDetails(stream_key, stream_url, obs_client, index=0)
        self.startStream(obs_client, index=0)

        # IMPORTANT: We delay starting the OBS stream until we are actually on
        # the page waiting for the feed signal and 'Go live' button.
        print("Waiting for feed signal and 'Go live' button...")
        go_live_button = self.wait_for_feed_signal_and_go_live(return_button=True)


        # Finally, click 'Go live' on Instagram
        self.driver.execute_script("arguments[0].click();", go_live_button)

        self.close()
        print("Instagram Stream is live! Browser closed.")

        return stream_url, stream_key


    def wait_for_feed_signal_and_go_live(self, return_button=False):
        go_live_button = WebDriverWait(self.driver, 300).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//h4[contains(text(), 'Go live')]]"))
        )

        # If caller wants the button returned, return it instead of clicking here
        if return_button:
            return go_live_button

        self.driver.execute_script("arguments[0].click();", go_live_button)

    def updateStreamDetails(self, stream_key, stream_url, obs_client, index=0):
        try:
            obs_client.send_request("CallVendorRequest", {
                "vendorName": "aitum-vertical-canvas",
                "requestType": "update_stream_key",
                "requestData": {
                    "stream_key": stream_key,
                    "index": index
                }
            })
            print(f'Stream Key for index {index} updated successfully')

            obs_client.send_request("CallVendorRequest", {
                "vendorName": "aitum-vertical-canvas",
                "requestType": "update_stream_server",
                "requestData": {
                    "stream_server": stream_url,
                    "index": index
                }
            })
            print(f'Stream Server for index {index} updated successfully')

        except Exception as e:
            print(f"An error occurred while updating stream details for index {index}: {e}")

    def startStream(self, obs_client, index=0):
        try:
            obs_client.send_request("CallVendorRequest", {
                "vendorName": "aitum-vertical-canvas",
                "requestType": "start_streaming",
                "requestData": {}
            })
            print(f'Live Stream started for index {index}')
        except Exception as e:
            print(f"An error occurred while starting stream for index {index}: {e}")

    def close(self):
        if self.driver:
            self.driver.quit()
