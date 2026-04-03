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
        self.steerRoi = (roi[0][1]*0.3, roi[0][1]*0.8)

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            self.controller.drive(50)
            frame = self.cam.getFrame()[self.roi[0][0]:self.roi[0][1], self.roi[1][0]:self.roi[1][1]]
            intersection, frame = self.detector.getIntersection(frame)
            self.latestFrame = frame
            
            # if there is no intersection, keep driving straight
            if intersection is None:
                continue
            
            # if there is an intersection, steer based on the position of the intersection
            if self.steerRoi[0] <= intersection[1] <= self.steerRoi[1]:
                percentage = int(100 * ((intersection[1] - self.steerRoi[0]) / (self.steerRoi[1] - self.steerRoi[0])))
            # if the intersection is above the steerRoi, steer with 100%
            elif intersection[1] > self.steerRoi[1]:
                percentage = 100
            # if the intersection is below the steerRoi, steer with 0%
            else: # met bij testen kijken hoe de kart zich hiermee gedraagt
                percentage = 0
            
            # check which camera is being used and steer in the opposite direction of the intersection
            if self.cam.camPos == "left":
                self.controller.steer(percentage, "right")
                print(f"steering right with percentage {percentage}")
            
            if self.cam.camPos == "right":
                self.controller.steer(percentage, "left")
                print(f"steering left with percentage {percentage}")
                
            time.sleep(1/30)
        self.cam.release()