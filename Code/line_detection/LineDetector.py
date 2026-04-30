import numpy as np
import json
import cv2
import os

class LineDetector():
    def __init__(self):
        with open(os.path.join(os.path.dirname(__file__), '..', 'config.json'), 'r') as file:
            self.config = json.load(file)
        self.gaussianKey = self.config["FilterSettings"]["GaussianBlur"]
        self.thresholdKey = self.config["FilterSettings"]["Threshold"]
        self.houghKey = self.config["FilterSettings"]["HoughLines"]
        
    
    def intersect(self, A, B, C, D):
        x1, y1 = map(float, A)
        x2, y2 = map(float, B)
        x3, y3 = map(float, C)
        x4, y4 = map(float, D)

        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)

        if abs(denom) < 1e-6:
            return None
        
        px = ((x1*x2 - y1*y2)*(x3-x4) - (x1*x2)*(x3*y4 - y3*x4)) / denom
        py = ((x1*x2 - y1*y2)*(y3-y4) - (y1*y2)*(x3*y4 - y3*x4)) / denom

        return (int(px), int(py))
    
    def lineProgress(self, A, B, P):
        ax, ay = A
        bx, by = B
        px, py = P

        abx = bx - ax
        aby = by - ay

        apx = px - ax
        apy = py - ay

        denom = (abx)*(abx) + (aby)*(aby)
        if denom == 0:
            return 0.5
        
        t = (apx * abx + apy * aby) / denom

        # Soft-map any real value to (0, 1) instead of hard-clipping.
        softness = 2.0
        mapped = 0.5 * (np.tanh(softness * (t - 0.5)) + 1.0)
        lo = np.nextafter(0.0, 1.0)
        hi = np.nextafter(1.0, 0.0)
        value = float(np.clip(mapped, lo, hi))
        value = round(value, 3)
        return float(np.clip(value, 0.001, 0.999))

    def processFrame(self, frame):
        # apply gaussian blur for less noise on the frame
        filteredFrame = cv2.GaussianBlur(frame, (self.gaussianKey["KernelSize"], self.gaussianKey["KernelSize"]), self.gaussianKey["SigmaX"])

        # Turn the frame gray
        filteredFrame = cv2.cvtColor(filteredFrame, cv2.COLOR_BGR2GRAY)

        # filter between dark and light and make dark black and light white
        _, filteredFrame = cv2.threshold(filteredFrame, self.thresholdKey["threshold"], self.thresholdKey["maxValue"], cv2.THRESH_BINARY)

        kernel = np.array([[10,5,10],
                           [5,10,5],
                           [10,5,10]])
        dst = cv2.filter2D(filteredFrame, -1, kernel)
        
        # cv2.imshow("zwartwit", dst)
        
        return dst
    
    def getIntersection(self, frame, bumperA, bumperB):
        intersections = []
        lines = cv2.HoughLinesP(self.processFrame(frame), self.houghKey["rho"], np.pi/self.houghKey["theta"], self.houghKey["threshold"], minLineLength=self.houghKey["minLineLength"], maxLineGap=self.houghKey["maxLineGap"])
        # height, width, _ = frame.shape

        if lines is not None:
            for line in lines:  
                x1,y1,x2,y2 = line[0]  
                intersectionCoord = self.intersect((x1,y1), (x2,y2), bumperA, bumperB)
                cv2.line(frame, (x1,y1), (x2,y2), (255,0,0), 2)
                if intersectionCoord is not None:   
                    # print(intersection)
                    intersection = self.lineProgress(bumperA, bumperB, intersectionCoord)
                    intersections.append(intersection)

        cv2.line(frame, bumperA, bumperB, (255,255,0), 2)
        # vertical line representing the bounds of detection
        if intersections is not None and len(intersections) >= 2:
            lowest_intersection = max(intersections,)
            # cv2.circle(frame, lowest_intersection[1], 2, (0,255,0))
            return (lowest_intersection, frame)
        elif len(intersections) != 0:
            # cv2.circle(frame, intersections[0][1], 2, (0,255,0))
            return (intersections[0], frame)
        return (None, frame)