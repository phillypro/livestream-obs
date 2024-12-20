import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure the project root directory is in the PATH so that imports work correctly.
# Adjust the relative path as needed depending on your project structure.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)

# Now we can import the InstagramStreamer class from the app.services module
from app.services.instagram_service import InstagramStreamer

class MockOBSClient:
    """
    A mock OBS client to simulate sending requests to OBS.
    This class will simply print out the requests it receives.
    """

    def send_request(self, request_type, request_data):
        """
        Simulate sending a request to the OBS client.
        request_type: str - The OBS request type (e.g., "CallVendorRequest").
        request_data: dict - The data to send along with the request.
        
        For testing purposes, we just print it out.
        """
        print(f"[MockOBSClient] Received request: {request_type}")
        print(f"[MockOBSClient] Data: {request_data}")


class TestInstagramService(unittest.TestCase):
    """
    Integration test for InstagramStreamer. This test will:
    - Initialize the InstagramStreamer.
    - Attempt to login to Instagram with the credentials from .env.
    - Attempt to navigate through the "Start Stream" flow on Instagram.
    - Utilize a mock OBS client to simulate integration with OBS.
    """

    def setUp(self):
        """
        Set up the test environment.
        Initialize the InstagramStreamer and MockOBSClient.
        
        Setting testing=True to make the browser visible and not headless for debugging.
        If you prefer headless mode (no visible browser), set testing=False.
        """
        self.mock_obs_client = MockOBSClient()
        self.streamer = InstagramStreamer(testing=True)

    def test_start_stream_with_title(self):
        """
        Test the `start_stream_with_title` method of the InstagramStreamer.
        This will:
        - Initialize the driver and login to Instagram.
        - Navigate through the "Create -> Live video" flow.
        - Input a test title.
        - Attempt to retrieve the stream key and URL.
        - Mock the OBS client calls to verify the integration steps.
        
        NOTE: This test will actually open a Chrome window and attempt a real login.
        Ensure your environment variables are correct and that you have ChromeDriver installed.
        """
        test_title = "Automated Test Stream"
        
        # Attempt to start the stream with the given title
        # This should run through all the steps: login, create live, set title, get stream key/url, etc.
        try:
            stream_url, stream_key = self.streamer.start_stream_with_title(test_title, self.mock_obs_client)
            print("Test completed successfully.")
            print(f"Stream URL retrieved: {stream_url}")
            print(f"Stream Key retrieved: {stream_key}")
            
            # Optionally, add assertions if you want to check the format or existence of the URL/key
            self.assertIsNotNone(stream_url, "Stream URL should not be None after starting the stream.")
            self.assertIsNotNone(stream_key, "Stream Key should not be None after starting the stream.")
            self.assertTrue("rtmp" in stream_url.lower(), "Stream URL should contain 'rtmp' as it should be an RTMP endpoint.")
        except Exception as e:
            self.fail(f"Test failed due to an unexpected exception: {e}")

    def tearDown(self):
        """
        Tear down the test environment.
        Close the Selenium driver if it is still open.
        """
        self.streamer.close()


if __name__ == "__main__":
    # Run the tests
    unittest.main()
