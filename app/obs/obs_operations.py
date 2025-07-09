# app/obs/obs_operations.py
import logging
from app.obs.obs_client import ObsClient
from app.config import globals

logger = logging.getLogger(__name__)


def toggle_recording(start: bool, obs_client: ObsClient = None):
    """
    Starts or stops recording in OBS.
    
    :param start: True to start recording, False to stop recording.
    :param obs_client: An instance of ObsClient; if not provided, we'll grab the global one.
    """
    if obs_client is None:
        obs_client = globals.obs_client
    
    if not obs_client or not obs_client.connected:
        logger.warning("OBS not connected. Cannot toggle recording.")
        return
    
    if start:
        logger.info("Sending request to start recording...")
        obs_client.send_request("StartRecording")
    else:
        logger.info("Sending request to stop recording...")
        obs_client.send_request("StopRecording")


def toggle_streaming(start: bool, obs_client: ObsClient = None):
    """
    Starts or stops streaming in OBS.
    
    :param start: True to start streaming, False to stop streaming.
    :param obs_client: An instance of ObsClient; if not provided, we'll grab the global one.
    """
    if obs_client is None:
        obs_client = globals.obs_client
    
    if not obs_client or not obs_client.connected:
        logger.warning("OBS not connected. Cannot toggle streaming.")
        return
    
    if start:
        logger.info("Sending request to start streaming...")
        obs_client.send_request("StartStream")
    else:
        logger.info("Sending request to stop streaming...")
        obs_client.send_request("StopStream")


def toggle_virtual_camera(start: bool, obs_client: ObsClient = None):
    """
    Starts or stops the OBS Virtual Camera.
    
    :param start: True to start the virtual camera, False to stop it.
    :param obs_client: An instance of ObsClient; if not provided, we'll grab the global one.
    """
    if obs_client is None:
        obs_client = globals.obs_client
    
    if not obs_client or not obs_client.connected:
        logger.warning("OBS not connected. Cannot toggle virtual camera.")
        return
    
    if start:
        logger.info("Sending request to start virtual camera...")
        obs_client.send_request("StartVirtualCamera")
    else:
        logger.info("Sending request to stop virtual camera...")
        obs_client.send_request("StopVirtualCamera")


def start_replay_buffer(obs_client: ObsClient = None):
    """
    Starts the replay buffer in OBS using the aitum-vertical-canvas plugin.
    
    :param obs_client: An instance of ObsClient; if not provided, we'll grab the global one.
    """
    if obs_client is None:
        obs_client = globals.obs_client
    
    if not obs_client or not obs_client.connected:
        logger.warning("OBS not connected. Cannot start replay buffer.")
        return
    
    logger.info("Sending request to start replay buffer (backtrack)...")
    obs_client.send_request("CallVendorRequest", {
        "vendorName": "aitum-vertical-canvas",
        "requestType": "start_backtrack",
        "requestData": {}
    })


def get_recording_status(obs_client: ObsClient = None) -> dict:
    """
    Returns a dictionary with the current recording status from OBS.
    
    :param obs_client: An instance of ObsClient; if not provided, we'll grab the global one.
    :return: A dict with keys like 'isRecording', 'isRecordingPaused', etc., or empty if unavailable.
    """
    if obs_client is None:
        obs_client = globals.obs_client
    
    if not obs_client or not obs_client.connected:
        logger.warning("OBS not connected. Cannot get recording status.")
        return {}
    
    response = obs_client._send_request_internal("GetRecordStatus", {})
    if not response:
        logger.warning("Failed to retrieve recording status from OBS.")
        return {}
    return response


def get_streaming_status(obs_client: ObsClient = None) -> dict:
    """
    Returns a dictionary with the current streaming status from OBS.
    
    :param obs_client: An instance of ObsClient; if not provided, we'll grab the global one.
    :return: A dict with keys like 'isStreaming', 'isRecording', etc., or empty if unavailable.
    """
    if obs_client is None:
        obs_client = globals.obs_client
    
    if not obs_client or not obs_client.connected:
        logger.warning("OBS not connected. Cannot get streaming status.")
        return {}
    
    response = obs_client._send_request_internal("GetStreamStatus", {})
    if not response:
        logger.warning("Failed to retrieve streaming status from OBS.")
        return {}
    return response