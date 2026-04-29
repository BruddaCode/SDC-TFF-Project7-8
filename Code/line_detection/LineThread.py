import threading
import time
from line_detection.LineDetector import LineDetector

class LineThread(threading.Thread):
    def __init__(self, cam, roi, A, B):
        threading.Thread.__init__(self)
        self.cam = cam
        self.detector = LineDetector()
        self.latestFrame = None
        self.running = True
        self.roi = roi
        self.latestIntersection = None
        self.A = self.toRoi(A, self.roi)
        self.B = self.toRoi(B, self.roi)

    def stop(self):
        self.running = False

    def sendMessage(self, percentage):
        if self.cam.camPos == "left":
            # self.controller.steer(percentage)
            print(f"steering right with percentage {percentage}")
            
        if self.cam.camPos == "right":
            # self.controller.steer(-percentage)
            print(f"steering left with percentage {percentage}")

    def toRoi(self, point, roi):
        y0, _ = roi[0]
        x0, _ = roi[1]

        x, y = point
        return (x - x0, y - y0)

    def run(self):
        while self.running:
            frame = self.cam.getFrame()[self.roi[0][0]:self.roi[0][1], self.roi[1][0]:self.roi[1][1]]
            pos = self.cam.camPos
            intersection, frame = self.detector.getIntersection(frame, pos, self.A, self.B)
            self.latestFrame = frame
            self.latestIntersection = intersection
                
            time.sleep(1/30)
        self.cam.release()