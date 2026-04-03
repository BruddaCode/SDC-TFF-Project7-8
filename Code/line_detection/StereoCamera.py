import numpy as np
import cv2

class StereoCamera():
    def __init__(self, index = None, videoPath = None, camPos = None):
        # camPos is used to identify which camera is being used
        self.camPos = camPos
        # check if a video path is provided, if so, use the video instead of the camera
        if videoPath is not None:
            self.cam = cv2.VideoCapture(videoPath)
            print(f"Video {videoPath} initialized.")
        else:
            self.cam = cv2.VideoCapture(index, cv2.CAP_V4L2)
            if not self.cam.isOpened():
                print(f"Camera {index} failed to open")
                return None
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'mp4v'))
            self.cam.set(cv2.CAP_PROP_FPS, 30)
            self.cam.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            print(f"Stereo Camera {index} initialized.")
        
        # ik denk dat dit wel weg kan
        # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # self.writer = cv2.VideoWriter(
        # 	f"{self.camPos}.mp4",
        # 	fourcc,
        # 	30,
        # 	(1280, 720)
        # )
  
        
    def getFrame(self):
        ret, frame = self.cam.read()
        if not ret:
            print("Failed to grab frame")
            return None
        return frame