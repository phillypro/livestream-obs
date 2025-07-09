import os
import pymiere
import subprocess
import time
from datetime import datetime

# This is the corrected and final version of the Premiere Pro automation service.

def launch_premiere_and_import(clips_folder, file_list):
    """
    Launches Adobe Premiere Pro, creates a new project, and imports a list of files.

    Args:
        clips_folder (str): The folder where the Premiere project will be saved.
        file_list (list): A list of full paths to the video and .ass files to import.
    """
    print("--- Starting Adobe Premiere Pro Automation (Pymiere) ---")

    try:
        # --- Step 1: Launch the Premiere Pro Application ---
        premiere_path = os.getenv("PREMIERE_PRO_PATH")
        if not premiere_path or not os.path.exists(premiere_path):
            print(f"Error: PREMIERE_PRO_PATH is not set correctly in .env or the file does not exist.")
            return
            
        print("  -> Launching Premiere Pro... (This may take a moment)")
        subprocess.Popen([premiere_path])
        
        # --- FIX: Reduced the wait time as requested ---
        # This waits for the application to load before we try to connect.
        # 30s was too long; 15s is a safer, faster default.
        print("  -> Waiting 15 seconds for application to load...")
        time.sleep(15)

        # --- Step 2: Create a Dynamic Project Path ---
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        project_name = f"Generated_Project_{timestamp}.prproj"
        project_path = os.path.join(clips_folder, project_name)
        
        print(f"  -> Creating new project at: {project_path}")
        pymiere.objects.app.newProject(project_path)

        # --- Step 3: Import Files with Correct Arguments ---
        print(f"  -> Importing {len(file_list)} files...")
        
        # --- FIX: Get the actual root bin object from the project ---
        root_bin = pymiere.objects.app.project.rootItem
        
        pymiere.objects.app.project.importFiles(
            file_list,
            suppressUI=True,
            targetBin=root_bin, # Pass the actual root bin object
            importAsNumberedStills=False
        )

        # --- Step 4: Organize Clips and Subtitles on the Timeline ---
        sequence = pymiere.objects.app.project.activeSequence
        if not sequence:
            print("Error: Could not find an active sequence in Premiere Pro.")
            pymiere.objects.app.project.newSequence(None, project_path)
            sequence = pymiere.objects.app.project.activeSequence
            if not sequence:
                 print("Fatal: Failed to create a new sequence.")
                 return

        video_files = sorted([f for f in file_list if f.lower().endswith('.mp4')])
        
        print(f"  -> Placing {len(video_files)} clips on the timeline...")
        for video_path in video_files:
            clip_name = os.path.basename(video_path)
            project_item = pymiere.objects.app.project.findItem(clip_name)
            
            if project_item:
                sequence.videoTracks[0].insertClip(project_item, sequence.end.seconds)
                
                ass_path = os.path.splitext(video_path)[0] + ".ass"
                if os.path.exists(ass_path):
                    subtitle_item = pymiere.objects.app.project.findItem(os.path.basename(ass_path))
                    if subtitle_item:
                        sequence.videoTracks[1].insertClip(subtitle_item, sequence.end.seconds - project_item.getOutPoint().seconds)

        print("--- Premiere Pro Automation Complete ---")
        
        # --- Step 5: Open (or Bring to Front) the Project ---
        pymiere.objects.app.openDocument(project_path)
        print("  -> Project is ready in Premiere Pro.")

    except Exception as e:
        print(f"An error occurred during Pymiere automation: {e}")