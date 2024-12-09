# app/obs/obs_client.py
import json
import threading
import time
from websocket import WebSocket, create_connection, WebSocketTimeoutException, WebSocketConnectionClosedException
from app.config.globals import shutdown_event

class ObsClient:
    def __init__(self):
        self.ws = None
        self.host = "ws://localhost:4455"
        self.listener_thread = None
        self.connection_thread = None
        self.lock = threading.Lock()
        self.connected = False
        self.ready = threading.Event()
        self.debug = True
        self.responses = {}  # Maps requestId -> response data from OBS
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

        self.on_ready_callback = None
        self.on_connection_failed_callback = None

    def log(self, message):
        if self.debug:
            print(f"[OBS Client] {message}")

    def start_connection(self):
        self.connection_thread = threading.Thread(target=self._connect_async, daemon=True)
        self.connection_thread.start()

    def _connect_async(self):
        try:
            self.log("Attempting to connect to OBS WebSocket...")
            self.ws = create_connection(self.host, timeout=10)

            hello_message = json.loads(self.ws.recv())
            self.log(f"Received hello message: {hello_message}")

            if hello_message.get('op') == 0:  # Hello
                identify_message = {
                    "op": 1,
                    "d": {
                        "rpcVersion": 1,
                        "eventSubscriptions": 33
                    }
                }
                self.log("Sending identify message...")
                self.ws.send(json.dumps(identify_message))

                identified_response = json.loads(self.ws.recv())
                self.log(f"Received identify response: {identified_response}")

                if identified_response.get('op') == 2:  # Identified
                    self.connected = True
                    self.reconnect_attempts = 0  # Reset reconnection attempts on successful connection
                    self.start_listener_thread()
                    return

            self.log("Failed to complete connection sequence")
            if self.on_connection_failed_callback:
                self.on_connection_failed_callback()

        except Exception as e:
            self.log(f"Error connecting to OBS WebSocket: {str(e)}")
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
                self.ws = None
            if self.on_connection_failed_callback:
                self.on_connection_failed_callback()

    def start_listener_thread(self):
        if self.listener_thread and self.listener_thread.is_alive():
            return
        
        self.listener_thread = threading.Thread(target=self.listen, daemon=True)
        self.listener_thread.start()
        self.log("Started listener thread")

    def listen(self):
        event_count = 0
        while not shutdown_event.is_set() and self.ws and self.connected:
            try:
                message = self.ws.recv()
                if not message:
                    continue
                
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    self.log(f"Error decoding message: {e}")
                    continue

                op = data.get('op')
                if op == 5:
                    event_count += 1
                    event_type = data.get('d', {}).get('eventType')
                    self.log(f"Received event: {event_type}")

                    if event_count >= 2 and not self.ready.is_set():
                        self.log("Detected active event stream, marking OBS as ready")
                        self.ready.set()
                        if self.on_ready_callback:
                            try:
                                self.on_ready_callback()
                            except Exception as callback_error:
                                self.log(f"Error in ready callback: {callback_error}")

                elif op == 7:
                    d = data.get('d', {})
                    request_id = d.get('requestId')
                    if request_id:
                        with self.lock:
                            self.responses[request_id] = d

            except WebSocketConnectionClosedException:
                self.log("WebSocket connection closed")
                self.connected = False
                self._attempt_reconnect()
                break
            except WebSocketTimeoutException:
                continue
            except Exception as e:
                self.log(f"Error in listener thread: {str(e)}")
                if isinstance(e, TypeError) and "'module' object is not callable" in str(e):
                    self.log("WebSocket error - attempting to reconnect...")
                    self._attempt_reconnect()
                else:
                    self.connected = False
                break

        self.log("Listener thread ending")

    def _attempt_reconnect(self):
        """Attempt to reconnect to the WebSocket server"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.log("Max reconnection attempts reached")
            if self.on_connection_failed_callback:
                self.on_connection_failed_callback()
            return

        try:
            self.reconnect_attempts += 1
            self.log(f"Attempting reconnection (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
            
            self.ws = None
            self.connected = False
            self.ready.clear()
            
            # Exponential backoff for reconnection attempts
            wait_time = min(30, 2 ** self.reconnect_attempts)  # Cap at 30 seconds
            time.sleep(wait_time)
            
            self._connect_async()
            
        except Exception as e:
            self.log(f"Reconnection attempt failed: {e}")

    def send_request(self, request_type, request_data=None, timeout=5):
        if threading.current_thread() is threading.main_thread():
            self.log("WARNING: send_request called from main thread!")
            return None

        if not self.ready.is_set():
            self.log("Cannot send request - OBS not ready yet")
            return None

        if not self.ws or not self.connected:
            self.log("Not connected to OBS WebSocket server")
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

            self.log(f"Sending request: {payload}")
            self.ws.send(json.dumps(payload))

            start_time = time.time()
            while time.time() - start_time < timeout:
                with self.lock:
                    if request_id in self.responses:
                        response = self.responses.pop(request_id)
                        request_status = response.get('requestStatus', {})

                        if not request_status.get('result', False):
                            self.log(f"Request failed: {request_status.get('comment', 'Unknown error')}")
                            return None

                        response_data = response.get('responseData')
                        if response_data is None:
                            return True
                        return response_data

                time.sleep(0.05)

            self.log(f"Request {request_type} timed out after {timeout} seconds.")
            return None

        except Exception as e:
            self.log(f"Error sending request: {e}")
            return None

    def get_version_async(self, callback):
        def version_thread():
            try:
                result = self.send_request("GetVersion")
                if callback:
                    callback(result)
            except Exception as e:
                self.log(f"Error in version thread: {e}")

        threading.Thread(target=version_thread, daemon=True).start()

    def start_virtual_camera_async(self, callback):
        def camera_thread():
            try:
                response = self.send_request("StartVirtualCam")
                if callback:
                    callback(response is True)
            except Exception as e:
                self.log(f"Error in camera thread: {e}")

        threading.Thread(target=camera_thread, daemon=True).start()

    def disconnect(self):
        self.log("Disconnecting from OBS...")
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.log(f"Error closing connection: {str(e)}")
            finally:
                self.ws = None
                self.connected = False
                self.ready.clear()
        self.log("Disconnected from OBS")