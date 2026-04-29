import threading
import time
from line_detection.LineDetector import LineDetector

class LineThread(threading.Thread):
    def __init__(self, cam, controller, roi):
        threading.Thread.__init__(self)
        self.cam = cam
        self.detector = LineDetector()
        self.controller = controller
        self.latestFrame = None
        self.running = True
        self.roi = roi
        self.steerRoi = (roi[0][1]*0.4, roi[0][1]*0.9)
        self.latestIntersection = None

    def stop(self):
        self.running = False

    def sendMessage(self, percentage):
        if self.cam.camPos == "left":
            # self.controller.steer(percentage)
            print(f"steering right with percentage {percentage}")
            
        if self.cam.camPos == "right":
            # self.controller.steer(-percentage)
            print(f"steering left with percentage {percentage}")


    def run(self):
        while self.running:
            if self.controller is not None:
                self.controller.drive(40)
            frame = self.cam.getFrame()[self.roi[0][0]:self.roi[0][1], self.roi[1][0]:self.roi[1][1]]
            pos = self.cam.camPos
            intersection, frame = self.detector.getIntersection(frame, pos)
            self.latestFrame = frame
            self.latestIntersection = intersection
                
            time.sleep(1/30)
        self.cam.release()
        self.controller.turnOffBus()