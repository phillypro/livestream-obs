from flask import request, jsonify, render_template
from flask_socketio import emit
from app.config.globals import obs_client, discord_bot
import os
from datetime import datetime
import glob
import threading
from app.services.transcription_service import (
    save_audio_from_video,
    transcribe_audio,
    get_emphasized_transcript,
    create_ass_file,
)
from app.services.premiere_service import launch_premiere_and_import

def process_replays_for_premiere():
    """
    This function, running in a background thread, finds all clips from today,
    transcribes them, and prepares them for Adobe Premiere Pro.
    """
    print("\n--- Kicking off Premiere Pro Preparation ---")

    # Read the root folder path from environment variables for portability
    root_folder = os.getenv("EPISODES_FOLDER_PATH")
    if not root_folder:
        print("Error: EPISODES_FOLDER_PATH is not set in the .env file.")
        return

    today_folder_name = datetime.now().strftime("%Y-%m-%d (%a)")
    todays_clips_path = os.path.join(root_folder, today_folder_name)

    print(f"Searching for clips in: {todays_clips_path}")

    if not os.path.isdir(todays_clips_path):
        print(f"Error: Today's clip folder not found at '{todays_clips_path}'")
        return

    search_pattern = os.path.join(todays_clips_path, '*.mp4')
    clips_found = sorted(glob.glob(search_pattern), key=os.path.getmtime)

    if not clips_found:
        print("No clips found for today.")
        return

    print(f"Found {len(clips_found)} clips to process.")

    files_to_import = []
    for i, clip_path in enumerate(clips_found):
        print(f"\n--- Processing Clip {i+1}/{len(clips_found)}: {os.path.basename(clip_path)} ---")
        audio_path = save_audio_from_video(clip_path)
        if not audio_path: continue
        word_level_path = transcribe_audio(audio_path)
        if not word_level_path: continue
        emphasis_data = get_emphasized_transcript(word_level_path)
        if not emphasis_data: continue
        ass_path = create_ass_file(clip_path, emphasis_data)

        # Add the clip and its subtitle file to our import list
        files_to_import.append(clip_path)
        if ass_path:
            files_to_import.append(ass_path)

    print("\n--- All clips processed. ---")
    
    # --- FINAL STEP: Launch Premiere Pro ---
    if files_to_import:
        launch_premiere_and_import(todays_clips_path, files_to_import)


def initialize_routes(app, settings_manager, socketio):
    @app.route('/')
    def index():
        return "Hello from OBS Integration!"

    # --- NEW ROUTE FOR STREAM DECK ---
    @app.route('/api/v1/create_premiere_project', methods=['POST'])
    def create_premiere_project():
        """
        This endpoint is triggered by a Stream Deck button.
        It starts the process of transcribing clips and opening them in Adobe Premiere Pro.
        """
        # Start the lengthy process in a background thread
        processing_thread = threading.Thread(target=process_replays_for_premiere)
        processing_thread.start()

        # Immediately return a response so the Stream Deck doesn't hang
        return jsonify({"status": "processing_started"}), 200

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
                'go_live': 'go_live' in request.form,  # handle the new go_live setting
                'multiplier': int(request.form.get('multiplier', 1)),
                'alerts': 'alerts' in request.form,
                'broadcastAlert': 'broadcastAlert' in request.form,
                'subtitles': 'subtitles' in request.form,
                'process': 'process' in request.form,
                'upscale': 'upscale' in request.form,
                'post_youtube': 'post_youtube' in request.form,
                'post_instagram': 'post_instagram' in request.form,
                'post_tiktok': 'post_tiktok' in request.form,
            }
            settings_manager.update_settings(new_settings)
            return jsonify(new_settings)

        elif request.method == 'GET':
            current_settings = {
                'go_live': settings_manager.get_setting('go_live'),  # handle the new go_live setting
                'multiplier': int(request.form.get('multiplier', 1)),
                'alerts': settings_manager.get_setting('alerts'),
                'broadcastAlert': settings_manager.get_setting('broadcastAlert'),
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