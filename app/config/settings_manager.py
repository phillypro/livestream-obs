# app/config/settings_manager.py
import threading

class SettingsManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._settings = {
            "alerts": False,
            "broadcastAlert": False,
            "multiplier": 1,
            "subtitles": True,
            "process": False,
            "upscale": False,
            "post_youtube": False,
            "post_instagram": False,
            "post_tiktok": False
        }

    def get_setting(self, key):
        with self._lock:
            return self._settings.get(key)

    def update_settings(self, settings_dict):
        with self._lock:
            self._settings.update(settings_dict)
            print("Updated settings:", self._settings)
