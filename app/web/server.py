# app/web/server.py
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from threading import Thread, Event
from app.config.globals import shutdown_event
import socket
import time
import platform
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fallback_secret'
CORS(app)
socketio = None  # Initialize later to avoid potential circular import issues
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

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True
        except Exception as e:
            logger.error(f"Unexpected error checking port {port}: {e}")
            return True

def wait_for_port_release(port, timeout=30):
    """Wait for port to be released, up to timeout seconds."""
    logger.info(f"Waiting for port {port} to be released (timeout: {timeout}s)")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            logger.info(f"Port {port} is now available")
            return True
        time.sleep(1)
    logger.warning(f"Timeout waiting for port {port} to be released")
    return False

def kill_process_on_port(port=5000):
    """Attempt to find and kill the process occupying the given port."""
    logger.info(f"Attempting to kill process on port {port}")
    system = platform.system().lower()

    try:
        if system == 'windows':
            cmd_find = ['netstat', '-ano']
            result = subprocess.run(cmd_find, capture_output=True, text=True)
            lines = result.stdout.splitlines()
            pid_to_kill = None
            
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    pid_to_kill = parts[-1]
                    break
                    
            if pid_to_kill is not None:
                subprocess.run(['taskkill', '/PID', pid_to_kill, '/F'])
                logger.info(f"Killed process with PID {pid_to_kill} on port {port}")
                return True
            else:
                logger.warning(f"No process found listening on port {port}")
                return False

        else:  # Linux/macOS
            cmd_find = ['lsof', '-t', f'-i:{port}']
            result = subprocess.run(cmd_find, capture_output=True, text=True)
            pids = result.stdout.strip().splitlines()
            
            if pids:
                for pid in pids:
                    subprocess.run(['kill', '-9', pid])
                    logger.info(f"Killed process with PID {pid} on port {port}")
                return True
            else:
                logger.warning(f"No process found listening on port {port}")
                return False

    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
        return False

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

        # Import routes here to avoid circular imports
        try:
            from app.web.routes import initialize_routes
            initialize_routes(app, settings_manager, socketio)
            logger.info("Routes initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize routes: {e}")
            return False

        def run_server():
            try:
                socketio.run(app, host='127.0.0.1', port=port, use_reloader=False)
            except Exception as e:
                logger.error(f"Error in server thread: {e}")
                server_started.clear()

        # Start the flask app
        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
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