# app/config/settings_manager.py

class SettingsManager:
    def __init__(self):
        # Placeholder: We'll store default values or load from a file
        # For now, just hardcode or store in memory
        self.settings = {
            'alerts': True,
            'broadcastAlert': True,
            'multiplier': 3,
            'subtitles': True,
            'process': True,
            'upscale': True,
            'post_youtube': True,
            'post_instagram': True,
            'post_tiktok': True
        }

    def get_setting(self, key):
        return self.settings.get(key)

    def update_settings(self, new_settings):
        self.settings.update(new_settings)
