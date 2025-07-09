import json
import os
import re
import subprocess
from pydub import AudioSegment
from faster_whisper import WhisperModel
import google.generativeai as genai

# --- Globals for this service ---
whisper_model = None # Whisper model will be loaded on first use

def get_whisper_model():
    """Initializes and returns a reusable faster_whisper model instance."""
    global whisper_model
    if whisper_model is None:
        print("Loading faster-whisper model...")
        # Using "large-v2" as specified in your old project
        whisper_model = WhisperModel("large-v2", device="cuda", compute_type="float16")
        print("Whisper model loaded.")
    return whisper_model

def save_audio_from_video(video_path):
    """Extracts audio from a video file and saves it as an MP3."""
    directory, filename = os.path.split(video_path)
    base_filename = os.path.splitext(filename)[0]
    audio_path = os.path.join(directory, f"{base_filename}.mp3")

    if os.path.exists(audio_path):
        print(f"  -> Audio file already exists for {filename}. Skipping extraction.")
        return audio_path

    try:
        video = AudioSegment.from_file(video_path, format="mp4")
        video.export(audio_path, format="mp3")
        print(f"  -> Successfully extracted audio for {filename}.")
        return audio_path
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None

def transcribe_audio(audio_path):
    """Transcribes audio using Whisper and returns the path to the word-level transcript."""
    txt_filename = os.path.splitext(audio_path)[0] + "_wordlevel.txt"
    if os.path.exists(txt_filename):
        print(f"  -> Word-level transcript already exists. Loading from file.")
        return txt_filename
    
    model = get_whisper_model()
    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    
    wordlevel_info = []
    for segment in segments:
        for word in segment.words:
            wordlevel_info.append({'word': word.word, 'start': word.start, 'end': word.end})
    
    with open(txt_filename, "w", encoding="utf-8") as f:
        json.dump(wordlevel_info, f, indent=4)
        
    print(f"  -> Successfully transcribed audio.")
    return txt_filename

def get_emphasized_transcript(word_level_path):
    """Uses the Gemini API to add emphasis to the transcript."""
    emphasis_path = word_level_path.replace('_wordlevel.txt', '_emphasis.txt')
    if os.path.exists(emphasis_path):
        print(f"  -> Emphasis transcript already exists. Loading from file.")
        with open(emphasis_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # --- Gemini API Implementation ---
    try:
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        genai.configure(api_key=gemini_api_key)
        # Using the model name you specified.
        model = genai.GenerativeModel('gemini-2.5-flash')

    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        return []

    with open(word_level_path, 'r', encoding='utf-8') as f:
        transcript_data = f.read()

    # Create the prompt for Gemini
    prompt = (
        "You are a creative assistant for video subtitles. Below is a JSON array representing words from a transcript. "
        "Your task is to identify the single most exciting or impactful word in each sentence and add '\"emphasis\": true' to that word's JSON object. "
        "Return ONLY the complete, modified JSON object and nothing else. The output must be a valid JSON object starting with `{\"subtitles\": [` and ending with `]}`.\n\n"
        f"Here is the data:\n{transcript_data}"
    )

    response = model.generate_content(prompt)
    content = response.text

    try:
        # --- ROBUST FIX ---
        # Use regex to find the JSON block, which might be wrapped in markdown.
        # re.DOTALL allows '.' to match newlines.
        match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        
        if match:
            # If we found a markdown block, extract the JSON from it.
            json_string = match.group(1)
        else:
            # Otherwise, assume the whole response is the JSON.
            json_string = content
            
        parsed_content = json.loads(json_string)
        emphasized_data = parsed_content.get('subtitles', [])
        
        with open(emphasis_path, 'w', encoding='utf-8') as f:
            json.dump(emphasized_data, f, indent=4)
            
        print("  -> Successfully added emphasis with Gemini.")
        return emphasized_data
    
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Received content was: {content}") 
        return []

def create_ass_file(video_path, emphasis_data, style_name='style1'):
    """Creates a styled .ass subtitle file."""
    base_path = os.path.splitext(video_path)[0]
    ass_path = base_path + ".ass"

    if os.path.exists(ass_path):
        print(f"  -> ASS file already exists. Skipping creation.")
        return ass_path
        
    styles = {
        'style1': {
            'Default': {'font_name': 'Bangers', 'font_size': 120, 'color': '&H00FFFFFF', 'stroke_width': 5, 'marginv': 9},
            'Emphasis': {'font_name': 'Bangers', 'font_size': 150, 'color': '&H0000EB32', 'stroke_width': 5, 'marginv': 9}
        }
    }

    def format_ass_timestamp(seconds):
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        cs = int((s % 1) * 100)
        return f"{int(h):01d}:{int(m):02d}:{int(s):02d}.{cs:02d}"

    with open(ass_path, "w", encoding='utf-8') as f:
        # Write ASS header and styles
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
        f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        
        default_style = styles[style_name]['Default']
        emphasis_style = styles[style_name]['Emphasis']

        f.write(f"Style: Default,{default_style['font_name']},{default_style['font_size']},{default_style['color']},&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,{default_style['stroke_width']},2,5,10,10,{default_style['marginv']},1\n")
        f.write(f"Style: Emphasis,{emphasis_style['font_name']},{emphasis_style['font_size']},{emphasis_style['color']},&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,{emphasis_style['stroke_width']},2,5,10,10,{emphasis_style['marginv']},1\n\n")

        # Write Events
        f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for word_info in emphasis_data:
            start = format_ass_timestamp(word_info['start'])
            end = format_ass_timestamp(word_info['end'])
            style = "Emphasis" if word_info.get('emphasis') else "Default"
            text = word_info.get('word', '').strip().replace(",", "")
            f.write(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}\n")

    print(f"  -> Successfully created styled .ass file.")
    return ass_path