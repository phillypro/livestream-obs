# app/obs/obs_client.py
import json
import threading
import time
import queue
from websocket import create_connection, WebSocketTimeoutException, WebSocketConnectionClosedException
from app.config.globals import shutdown_event

class ObsClient:
    def __init__(self):
        self.ws = None
        self.host = "ws://localhost:4455"
        self.listener_thread = None
        self.connection_thread = None
        self.request_thread = None
        self.lock = threading.Lock()
        self.connected = False
        self.ready = threading.Event()
        self.debug = False
        self.responses = {}
        self.request_queue = queue.Queue()
        self.on_ready_callback = None
        self.on_connection_failed_callback = None
        self.retry_attempts = 3
        self.current_retry = 0
        
        # Start request processing thread
        self.request_thread = threading.Thread(target=self._process_requests, daemon=True)
        self.request_thread.start()

    def log(self, message):
        if self.debug:
            print(f"OBS Client: {message}")

    def start_connection(self):
        """Initialize connection in separate thread"""
        self.connection_thread = threading.Thread(target=self._connect_async, daemon=True)
        self.connection_thread.start()

    def _connect_async(self):
        """Attempt to establish connection to OBS WebSocket"""
        while self.current_retry < self.retry_attempts:
            try:
                self.ws = create_connection(self.host, timeout=10)
                hello_message = json.loads(self.ws.recv())

                if hello_message.get('op') == 0:  # Hello
                    identify_message = {
                        "op": 1,
                        "d": {
                            "rpcVersion": 1,
                            "eventSubscriptions": 33
                        }
                    }
                    self.ws.send(json.dumps(identify_message))

                    identified_response = json.loads(self.ws.recv())

                    if identified_response.get('op') == 2:  # Identified
                        self.connected = True
                        self.start_listener_thread()
                        return

                self._handle_connection_failure()

            except Exception as e:
                self.log(f"Connection error: {e}")
                if self.ws:
                    try:
                        self.ws.close()
                    except:
                        pass
                    self.ws = None
                self.current_retry += 1
                time.sleep(2)  # Backoff before retrying

        if self.on_connection_failed_callback:
            self.on_connection_failed_callback()

    def _handle_connection_failure(self):
        """Handle failed connection attempts"""
        self.current_retry += 1
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
        time.sleep(2)  # Backoff before retrying

    def start_listener_thread(self):
        """Start the WebSocket listener thread if not already running"""
        if self.listener_thread and self.listener_thread.is_alive():
            return
        
        self.listener_thread = threading.Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

    def listen(self):
        """Listen for WebSocket messages"""
        while not shutdown_event.is_set() and self.ws and self.connected:
            try:
                message = self.ws.recv()
                if not message:
                    continue
                
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                op = data.get('op')
                if op == 5:  # Event
                    if not self.ready.is_set():
                        self.ready.set()
                        if self.on_ready_callback:
                            try:
                                self.on_ready_callback()
                            except Exception as e:
                                self.log(f"Ready callback error: {e}")

                elif op == 7:  # Request Response
                    d = data.get('d', {})
                    request_id = d.get('requestId')
                    if request_id:
                        with self.lock:
                            self.responses[request_id] = d

            except WebSocketConnectionClosedException:
                self.log("WebSocket connection closed")
                self.connected = False
                break
            except WebSocketTimeoutException:
                continue
            except Exception as e:
                self.log(f"Listener error: {e}")
                self.connected = False
                break

        self.log("Listener thread exiting")

    def _process_requests(self):
        """Process OBS requests asynchronously"""
        while not shutdown_event.is_set():
            try:
                # Get request from queue with timeout to allow checking shutdown
                request = self.request_queue.get(timeout=0.5)
                if request:
                    request_type, request_data, callback = request
                    response = self._send_request_internal(request_type, request_data)
                    if callback:
                        try:
                            callback(response)
                        except Exception as e:
                            self.log(f"Callback error: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.log(f"Request processing error: {e}")

    def send_request(self, request_type, request_data=None, callback=None):
        """Queue request for async processing"""
        self.request_queue.put((request_type, request_data, callback))
        
    def _send_request_internal(self, request_type, request_data=None, timeout=5):
        """Internal method to actually send the request"""
        if not self.ready.is_set() or not self.ws or not self.connected:
            return None

        if request_data is None:
            request_data = {}

        request_id = f"req_{request_type}_{int(time.time())}"
        payload = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": request_id,
                "requestData": request_data
            }
        }

        try:
            with self.lock:
                if request_id in self.responses:
                    del self.responses[request_id]

            self.ws.send(json.dumps(payload))

            start_time = time.time()
            while time.time() - start_time < timeout:
                with self.lock:
                    if request_id in self.responses:
                        response = self.responses.pop(request_id)
                        request_status = response.get('requestStatus', {})
                        if not request_status.get('result', False):
                            return None
                        return response.get('responseData') or True

                time.sleep(0.05)

            return None

        except Exception as e:
            self.log(f"Send request error: {e}")
            return None

    def get_version_async(self, callback=None):
        """Get OBS version information asynchronously"""
        self.send_request("GetVersion", callback=callback)

    def disconnect(self):
        """Disconnect from OBS WebSocket"""
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.log(f"Disconnect error: {e}")
            finally:
                self.ws = None
                self.connected = False
                self.ready.clear()