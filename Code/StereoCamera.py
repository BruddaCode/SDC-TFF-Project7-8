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
        ret, self.frame = self.cam.read()
        if not ret:
            print("Failed to grab frame")
            return None
        gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        # self.writer.write(self.frame)
        # Apply Gaussian Blur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 1.4)
    
        # Apply Canny Edge Detector
        edges = cv2.Canny(blur, threshold1=10, threshold2=150)

        self.getHoughLines(edges)

        cv2.imshow(f"{self.camPos} (Grayscale)", self.frame)

    def getHoughLines(self, edges):
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
        for line in lines:
            rho,theta = line[0]
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a*rho
            y0 = b*rho
            x1 = int(x0 + 1000*(-b))
            y1 = int(y0 + 1000*(a))
            x2 = int(x0 - 1000*(-b))
            y2 = int(y0 - 1000*(a))

            cv2.line(self.frame,(x1,y1),(x2,y2),(0,0,255),2)