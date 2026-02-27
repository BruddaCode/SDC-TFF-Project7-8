import numpy as np
import cv2

class StereoCamera:
    def __init__(self, index, camPos):
        self.cam = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if not self.cam.isOpened():
            print(f"Camera {index} failed to open")
            return None
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'mp4v'))
        self.cam.set(cv2.CAP_PROP_FPS, 30)
        self.cam.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.camPos = camPos
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            f"{self.camPos}.mp4",
            fourcc,
            30,
            (640, 480)
        )
        print(f"Stereo Camera {index} initialized.")
        
    def get_frame(self):
        ret, frame = self.cam.read()
        if not ret:
            print("Failed to grab frame")
            return None
        cv2.imshow(f"{self.camPos}", frame)
        self.writer.write(frame)
        # return frame

class GrayStereoCamera(StereoCamera):
    def __init__(self, index, camPos):
        super().__init__(index, camPos)
        self.index = index
        
    def get_frame(self):
        ret, frame = self.cam.read()
        if not ret:
            print("Failed to grab frame")
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imshow(f"{self.camPos} (Grayscale)", gray)
        self.writer.write(gray)
