from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from threading import Thread, Event
from app.config.globals import shutdown_event
from app.utils.ports import is_port_in_use, wait_for_port_release, kill_process_on_port
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fallback_secret'
CORS(app)
socketio = None
server_thread = None
server_started = Event()

def initialize_socketio():
    global socketio
    if socketio is None:
        try:
            socketio = SocketIO(app, cors_allowed_origins="*")
            logger.info("SocketIO initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SocketIO: {e}")
            raise

def start_flask_app(settings_manager):
    global server_thread, socketio
    port = 5000

    try:
        # Initialize SocketIO first
        initialize_socketio()
        
        # Check if port is in use
        if is_port_in_use(port):
            logger.warning(f"Port {port} is currently in use")
            killed = kill_process_on_port(port)
            
            if killed:
                logger.info("Waiting for port to be fully released")
                time.sleep(2)
                if is_port_in_use(port):
                    logger.error(f"Port {port} still in use after killing process")
                    return False
            else:
                logger.info(f"Waiting for port {port} to be released naturally")
                if not wait_for_port_release(port):
                    logger.error(f"Timeout waiting for port {port}")
                    return False

        def run_server():
            try:
                socketio.run(app, host='127.0.0.1', port=port, use_reloader=False, allow_unsafe_werkzeug=True)
            except Exception as e:
                logger.error(f"Error in server thread: {e}")
                server_started.clear()

        # Start the flask app in a thread
        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait briefly to check if the server started
        time.sleep(1)
        if is_port_in_use(port):
            server_started.set()
            logger.info("Flask server started successfully")
            return socketio
        else:
            logger.error("Failed to verify server startup")
            return False
            
    except Exception as e:
        logger.error(f"Error starting Flask server: {e}")
        return False

def stop_flask_app():
    global server_thread, socketio
    
    if not server_started.is_set():
        logger.warning("Server was not successfully started")
        return

    logger.info("Stopping Flask-SocketIO server...")
    
    try:
        if socketio:
            socketio.stop()
            logger.info("SocketIO stopped")
    except Exception as e:
        logger.error(f"Error stopping SocketIO: {e}")

    if server_thread and server_thread.is_alive():
        try:
            server_thread.join(timeout=5)
            logger.info("Server thread joined successfully")
        except Exception as e:
            logger.error(f"Error joining server thread: {e}")

    # Additional cleanup
    if is_port_in_use(5000):
        logger.warning("Port 5000 still in use, attempting to force cleanup")
        kill_process_on_port(5000)

    if wait_for_port_release(5000, timeout=5):
        logger.info("Successfully released port 5000")
    else:
        logger.warning("Could not verify port 5000 was released")

    server_started.clear()
