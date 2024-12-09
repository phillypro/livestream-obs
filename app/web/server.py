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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fallback_secret'  # Will override with env or from settings if needed
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

server_thread = None
server_started = Event()


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True

def wait_for_port_release(port, timeout=30):
    """Wait for port to be released, up to timeout seconds."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            return True
        time.sleep(1)
    return False

def kill_process_on_port(port=5000):
    """Attempt to find and kill the process occupying the given port."""
    system = platform.system().lower()

    if system == 'windows':
        # netstat -ano | findstr :5000
        cmd_find = ['netstat', '-ano']
        result = subprocess.run(cmd_find, capture_output=True, text=True)
        lines = result.stdout.splitlines()
        pid_to_kill = None
        for line in lines:
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                # On Windows, PID is usually the last part
                pid_to_kill = parts[-1]
                break
        if pid_to_kill is not None:
            subprocess.run(['taskkill', '/PID', pid_to_kill, '/F'])
            print(f"Killed process with PID {pid_to_kill} that was using port {port}.")
            return True
        else:
            return False

    else:
        # Linux/macOS approach using lsof
        cmd_find = ['lsof', '-t', f'-i:{port}']
        result = subprocess.run(cmd_find, capture_output=True, text=True)
        pids = result.stdout.strip().splitlines()
        if pids:
            for pid in pids:
                subprocess.run(['kill', '-9', pid])
                print(f"Killed process with PID {pid} that was using port {port}.")
            return True
        else:
            return False

def start_flask_app(settings_manager):
    global server_thread
    port = 5000

    # Check if port is in use
    if is_port_in_use(port):
        print(f"Port {port} is currently in use. Attempting to free it...")
        killed = kill_process_on_port(port)
        if killed:
            # Wait a moment for the OS to release the port
            time.sleep(2)
            if is_port_in_use(port):
                print(f"Port {port} is still in use after killing process.")
                return False
        else:
            print(f"Could not kill any process on port {port}, waiting for release...")
            if not wait_for_port_release(port):
                print(f"Timeout waiting for port {port} to be released")
                return False

    # Import routes here to avoid circular imports
    from app.web.routes import initialize_routes
    initialize_routes(app, settings_manager, socketio)

    try:
        # Start the flask app
        server_thread = Thread(
            target=lambda: socketio.run(
                app, 
                host='127.0.0.1', 
                port=port, 
                use_reloader=False
            ),
            daemon=True
        )
        server_thread.start()
        
        # Wait briefly to ensure server starts
        time.sleep(1)
        if is_port_in_use(port):
            server_started.set()
            return True
        else:
            print("Failed to verify server startup")
            return False
            
    except Exception as e:
        print(f"Error starting Flask server: {e}")
        return False

def stop_flask_app():
    global server_thread
    
    if not server_started.is_set():
        print("Server was not successfully started")
        return

    print("Stopping Flask-SocketIO server...")
    
    try:
        # Stop SocketIO first
        socketio.stop()
    except Exception as e:
        print(f"Error stopping SocketIO: {e}")

    # Wait for the server thread to complete
    if server_thread and server_thread.is_alive():
        try:
            server_thread.join(timeout=5)
        except Exception as e:
            print(f"Error joining server thread: {e}")

    # Verify port cleanup
    if wait_for_port_release(5000, timeout=5):
        print("Successfully released port 5000")
    else:
        print("Warning: Could not verify port 5000 was released")

    server_started.clear()
