import socket
import time
import platform
import subprocess
import logging

logger = logging.getLogger(__name__)

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

def kill_process_on_port(port):
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
