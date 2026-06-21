from cv2_enumerate_cameras import enumerate_cameras
import numpy as np
import json
import cv2
import os

class StereoCamera():
    def __init__(self, index = None, videoPath = None, camPos = None):
        #? get general camera settings from config
        with open(os.path.join(os.path.dirname(__file__), '..', 'config.json'), 'r') as file:
            self.config = json.load(file)
            
        self.cameraKey = self.config["Camera"]
        
        # camPos is used to identify which camera is being used
        self.camPos = camPos.lower()
        # check if a video path is provided, if so, use the video instead of the camera
        if videoPath is not None:
            try:
                self.cam = cv2.VideoCapture(videoPath)
                print(f"Video {videoPath} initialized.")
            except Exception as e:
                print(f"Error opening video {videoPath}: {e}")
                return None
        else:
            try:
                self.cam = cv2.VideoCapture(index, cv2.CAP_V4L2)
                if not self.cam.isOpened():
                    print(f"Camera {index} failed to open")
                    return None
            except Exception as e:
                print(f"Error opening camera {index}: {e}")
                return None

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
    
    #? this cool little function gets the camera id based on the name of the camera. 
    #? so you dont have to guess which ids or whatever are the correct ones for the cameras
    @staticmethod
    def getCameraId(cameraName=None):
        if cameraName is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
            with open(config_path, 'r') as file:
                config = json.load(file)
            cameraName = config["Camera"]["cameraName"]
        
        cameraIDs = []
        
        for camera_info in enumerate_cameras():
            if cameraName.lower() in camera_info.name.lower():
                if int(str(camera_info.index)[-1]) not in cameraIDs:
                    cameraIDs.append(int(str(camera_info.index)[-1]))
            else:
                print(f"Camera '{camera_info.name}' does not match the specified name '{cameraName}'.")
        
        return cameraIDs
    
    def release(self):
        self.cam.release()