# app/web/routes.py
from flask import request, jsonify
from app.main import obs_client

def initialize_routes(app, settings_manager, socketio):

    @app.route('/')
    def index():
        return "Hello from OBS Integration!"

    @app.route('/settings', methods=['GET'])
    def get_settings():
        return jsonify({
            'alerts': settings_manager.get_setting('alerts'),
            'broadcastAlert': settings_manager.get_setting('broadcastAlert'),
            'multiplier': settings_manager.get_setting('multiplier')
        })

    @app.route('/trigger_virtual_camera', methods=['GET'])
    def trigger_virtual_camera():
        if obs_client and obs_client.connected and obs_client.ready.is_set():
            def camera_callback(success):
                if success:
                    print("[Web Route] Virtual camera started successfully.")
                else:
                    print("[Web Route] Failed to start virtual camera.")

            obs_client.start_virtual_camera_async(camera_callback)
            return jsonify({"message": "Attempting to start virtual camera"}), 200
        else:
            return jsonify({"error": "OBS not ready"}), 503
