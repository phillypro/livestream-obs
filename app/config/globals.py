# app/config/globals.py
import os
from dotenv import load_dotenv
import threading

# Load environment variables
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

shutdown_event = threading.Event()

# We can put other global variables or singletons here if needed.
