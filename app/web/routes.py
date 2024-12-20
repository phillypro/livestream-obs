from flask import request, jsonify, render_template
from flask_socketio import emit
from app.config.globals import obs_client, discord_bot

def initialize_routes(app, settings_manager, socketio):
    @app.route('/')
    def index():
        return "Hello from OBS Integration!"

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
    
    # Settings Routes
    @app.route('/settings', methods=['GET', 'POST'])
    def settings_page():
        if request.method == 'POST':
            # Handle updating settings
            new_settings = {
                'alerts': 'alerts' in request.form,
                'broadcastAlert': 'broadcastAlert' in request.form,
                'multiplier': int(request.form.get('multiplier', 1)),
                'subtitles': 'subtitles' in request.form,
                'process': 'process' in request.form,
                'upscale': 'upscale' in request.form,
                'post_youtube': 'post_youtube' in request.form,
                'post_instagram': 'post_instagram' in request.form,
                'post_tiktok': 'post_tiktok' in request.form
            }
            settings_manager.update_settings(new_settings)
            return jsonify(new_settings)

        elif request.method == 'GET':
            current_settings = {
                'alerts': settings_manager.get_setting('alerts'),
                'broadcastAlert': settings_manager.get_setting('broadcastAlert'),
                'multiplier': settings_manager.get_setting('multiplier'),
                'process': settings_manager.get_setting('process'),
                'upscale': settings_manager.get_setting('upscale'),
                'subtitles': settings_manager.get_setting('subtitles'),
                'post_youtube': settings_manager.get_setting('post_youtube'),
                'post_instagram': settings_manager.get_setting('post_instagram'),
                'post_tiktok': settings_manager.get_setting('post_tiktok')
            }
            return render_template('settings.html', **current_settings)
        
    # Highlight Routes
    @app.route('/highlight')
    def highlight():
        return render_template('highlight.html')
    
    @app.route('/hand_status')
    def hand_status():
        return render_template('hand_raise.html')

    @socketio.on('highlight_data')
    def handle_highlight(data):
        socketio.emit('highlight_data', data, namespace='/')

    @socketio.on('voice_state_update')
    def handle_voice_state_update(data):
        socketio.emit('voice_state_update', data, namespace='/')

    @app.route('/lastcomment', methods=['POST'])
    def last_comment():
        if discord_bot is None:
            return jsonify({"error": "Discord bot not initialized"}), 503
        last_comment_data = discord_bot.get_last_message_data()
        if last_comment_data:
            socketio.emit('highlight_data', last_comment_data, namespace='/')
            return jsonify({"message": "Last comment highlighted successfully"}), 200
        else:
            return jsonify({"message": "No data found"}), 404

    @app.route('/hidecomment', methods=['POST'])
    def hide_comment():
        socketio.emit('hide_comment', namespace='/')
        return jsonify({"message": "Comment hidden successfully"}), 200
