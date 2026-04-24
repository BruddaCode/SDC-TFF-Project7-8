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
            
            # if there is no intersection, keep driving straight
            if intersection is None:
                continue
            
            # if there is an intersection, steer based on the position of the intersection
            if self.steerRoi[0] <= intersection[1] <= self.steerRoi[1]:
                percentage = int(100 * ((intersection[1] - self.steerRoi[0]) / (self.steerRoi[1] - self.steerRoi[0])))
                self.sendMessage(percentage)
            # if the intersection is above the steerRoi, steer with 100%
            elif intersection[1] > self.steerRoi[1]:
                percentage = 100
                self.sendMessage(percentage)
            # if the intersection is below the steerRoi, steer with 0%
                
            time.sleep(1/30)
        self.cam.release()
        self.controller.turnOffBus()