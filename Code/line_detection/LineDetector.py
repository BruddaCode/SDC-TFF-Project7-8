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
        
        # print(f"t before mapping: {t}")

        # Soft-map any real value to (0, 1) instead of hard-clipping.
        # softness = 2.0
        # mapped = 0.5 * (np.tanh(softness * (t - 0.5)) + 1.0)
        # lo = np.nextafter(0.0, 1.0)
        # hi = np.nextafter(1.0, 0.0)
        # value = float(np.clip(mapped, lo, hi))
        # value = round(value, 3)
        # return float(np.clip(value, 0.001, 0.999))
        return max(0.0, min(1.0, t))

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
        frame = cv2.filter2D(filteredFrame, -1, kernel)
        
        # cv2.imshow("zwartwit", dst)
        
        # hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        # h, l, s = cv2.split(hls)
        
        # l = cv2.createCLAHE(clipLimit=2, tileGridSize=(5, 5)).apply(l)
        
        # hls = cv2.merge((h, l, s))
        # frame = cv2.inRange(hls, (0, 180, 0), (255, 255, 180))
        # frame = cv2.bitwise_and(l, l, mask=frame)
        
        # frame = cv2.Canny(frame, 17, 122)
        
        # kernel = np.ones(4, np.uint8)
        # frame = cv2.dilate(frame, kernel, iterations=2)
        # frame = cv2.erode(frame, kernel, iterations=3)
        
        # frame = cv2.filter2D(frame, -1, np.array([[10, 5, 10],[5, 10, 5],[10, 5, 10]]))
        
        return frame
    
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
            lowest_intersection = max(intersections)
            # print(f"Lowest intersection: {lowest_intersection}")
            # cv2.circle(frame, (100,100), 20, (0,255,0), -1)
            return (lowest_intersection, frame)
        elif len(intersections) != 0:
            # cv2.circle(frame, intersections[0][1], 2, (0,255,0))
            return (intersections[0], frame)
        return (None, frame)