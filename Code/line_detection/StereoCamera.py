import numpy as np
import json
import cv2
import os

class StereoCamera():
    def __init__(self, index = None, videoPath = None, camPos = None):
        with open(os.path.join(os.path.dirname(__file__), '..', 'config.json'), 'r') as file:
            self.config = json.load(file)
            
        self.cameraKey = self.config["Camera"]
        
        # camPos is used to identify which camera is being used
        self.camPos = camPos.lower()
        # check if a video path is provided, if so, use the video instead of the camera
        if videoPath is not None:
            self.cam = cv2.VideoCapture(videoPath)
            print(f"Video {videoPath} initialized.")
        else:
            self.cam = cv2.VideoCapture(index, cv2.CAP_V4L2)
            if not self.cam.isOpened():
                print(f"Camera {index} failed to open")
                return None
            print(self.cameraKey["width"])

            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.cameraKey["width"])
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cameraKey["height"])
            self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            self.cam.set(cv2.CAP_PROP_FPS, self.cameraKey["fps"])
            self.cam.set(cv2.CAP_PROP_AUTOFOCUS, self.cameraKey["autoFocus"])
            print(f"Stereo Camera {index} initialized.")
        
    def getFrame(self):
        ret, frame = self.cam.read()
        if not ret:
            print("Failed to grab frame")
            return None
        return frame
    
    def release(self):
        self.cam.release()