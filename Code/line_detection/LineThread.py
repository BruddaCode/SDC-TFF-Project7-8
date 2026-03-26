import threading
import cv2
import time

class LineThread(threading.Thread):
    def __init__(self, cam, detector, roi1, roi2, outputQueue):
        threading.Thread.__init__(self)
        self.cam = cam
        self.detector = detector
        self.roi1 = roi1
        self.roi2 = roi2
        self.outputQueue = outputQueue
        self.latestFrame = None

    def run(self):
        while True:
            ret, frame = self.cam.read()
            if not ret:
                break
            frame = frame[self.roi1[0]:self.roi1[1], self.roi2[0]:self.roi2[1]]
            intersection, frame = self.detector.getIntersection(frame)
            self.latestFrame = frame
            time.sleep(1/30)
        self.cam.release()