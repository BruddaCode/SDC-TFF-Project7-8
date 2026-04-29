from line_detection.LineDetector import LineDetector
import threading
import time
import json
import os

class LineThread(threading.Thread):
    def __init__(self, cam):
        threading.Thread.__init__(self)
        with open(os.path.join(os.path.dirname(__file__), '..', 'config.json'), 'r') as file:
            self.config = json.load(file)
        
        self.cam = cam
        self.camPos = cam.camPos.lower()
        
        self.roiKey = self.config[f"{self.camPos}Roi"]
        self.lineKey = self.config[f"{self.camPos}DiagonalLine"]
        
        self.running = True
        
        self.detector = LineDetector()
        self.latestFrame = None
        self.latestIntersection = None
        self.A = self.toRoi((self.lineKey["A"]["x"], self.lineKey["A"]["y"]), ((self.roiKey["x1"], self.roiKey["y1"]), (self.roiKey["x2"], self.roiKey["y2"])))
        self.B = self.toRoi((self.lineKey["B"]["x"], self.lineKey["B"]["y"]), ((self.roiKey["x1"], self.roiKey["y1"]), (self.roiKey["x2"], self.roiKey["y2"])))

    # dont try to simplify this, it just breaks somehow, and i have no idea why
    def toRoi(self, point, roi):
        y0, _ = roi[0]
        x0, _ = roi[1]

        x, y = point
                
        return (x - x0, y - y0)

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            frame = self.cam.getFrame()[self.roiKey["x1"]:self.roiKey["y1"], self.roiKey["x2"]:self.roiKey["y2"]]
            intersection, frame = self.detector.getIntersection(frame, self.A, self.B)
            self.latestFrame = frame
            self.latestIntersection = intersection
            time.sleep(1/30)
        self.cam.release()