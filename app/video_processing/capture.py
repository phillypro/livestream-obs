# app/video_processing/capture.py
import cv2

class FrameCapturer:
    def __init__(self, camera_index=8, width=1920, height=1080):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def capture_frame(self, x1, y1, x2, y2):
        ret, frame = self.cap.read()
        if ret and frame is not None:
            cropped_frame = frame[y1:y2, x1:x2]
            return cropped_frame
        return None

    def release(self):
        if self.cap.isOpened():
            self.cap.release()
