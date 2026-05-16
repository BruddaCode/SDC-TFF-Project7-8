import numpy as np
import json
import cv2
import os
import time

class LineDetector():
    def __init__(self, lengthReferenceLine, bumperA, bumperB, side: bool):
        with open(os.path.join(os.path.dirname(__file__), '..', 'config.json'), 'r') as file:
            self.config = json.load(file)
        self.claheKey = self.config["FilterSettings"]["Clahe"]
        self.mergeRangeKey = self.config["FilterSettings"]["MergeRange"]
        self.gaussianKey = self.config["FilterSettings"]["GaussianBlur"]
        self.cannyKey = self.config["FilterSettings"]["Canny"]
        self.houghKey = self.config["FilterSettings"]["HoughLines"]
        self.lengthReferenceLine = lengthReferenceLine
        self.bumperA = bumperA
        self.bumperB = bumperB

        # side is true for left and false for right, this is used to determine which side of the line is the "detection" side, and which is the "non-detection" side. This is important for the lineProgress function, as it determines how the progress is calculated based on the position of the intersection relative to the line.
        self.side = side

    def intersect(self, A, B, C, D):
        x1, y1 = A
        x2, y2 = B
        x3, y3 = C
        x4, y4 = D

        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)

        if abs(denom) == 0:
            return None
        
        px = ((x1*y2 - y1*x2)*(x3-x4) - (x1-x2)*(x3*y4 - y3*x4)) / denom
        py = ((x1*y2 - y1*x2)*(y3-y4) - (y1-y2)*(x3*y4 - y3*x4)) / denom

        return (int(px), int(py))
    
    def lineProgress(self, intersection):
        if self.side:
            length = np.sqrt((self.bumperA[0] - intersection[0])**2 + (self.bumperA[1] - intersection[1])**2)
            # print(f"Left side - Length from bumperA to intersection: {length}, Reference line length: {self.lengthReferenceLine}, Progress before inversion: {length / self.lengthReferenceLine}")
            return length / self.lengthReferenceLine
        else:
            length = np.sqrt((self.bumperA[0] - intersection[0])**2 + (self.bumperA[1] - intersection[1])**2)
            # print(f"Right side - Length from bumperA to intersection: {length}, Reference line length: {self.lengthReferenceLine}, Progress before inversion: {1 - (length / self.lengthReferenceLine)}")
            return 1 - length / self.lengthReferenceLine


    def processFrame(self, frame):
                
        # convert to hls and apply CLAHE to the lightness channel
        hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        h, l, s = cv2.split(hls)
        l = cv2.createCLAHE(clipLimit=self.claheKey["clipLimit"], tileGridSize=(self.claheKey["tileGridSize"], self.claheKey["tileGridSize"])).apply(l)
        hls = cv2.merge((h, l, s))
        frame = cv2.inRange(hls, (self.mergeRangeKey["lower"][0], self.mergeRangeKey["lower"][1], self.mergeRangeKey["lower"][2]), (self.mergeRangeKey["upper"][0], self.mergeRangeKey["upper"][1], self.mergeRangeKey["upper"][2]))
        frame = cv2.bitwise_and(l, l, mask=frame)
        
        # apply gaussian blur to reduce noise
        frame = cv2.GaussianBlur(frame, (self.gaussianKey["KernelSize"], self.gaussianKey["KernelSize"]), self.gaussianKey["SigmaX"])
        
        # apply Canny edge detection
        frame = cv2.Canny(frame, self.cannyKey["threshold1"], self.cannyKey["threshold2"], self.cannyKey["apertureSize"])
        
        frame = cv2.filter2D(frame, -1, np.array([[10, 5, 10],[5, 10, 5],[10, 5, 10]]))
        
        return frame
    
    def getIntersection(self, frame, pointA, pointB):
        # collect (progress, (x, y)) pairs for each intersection
        intersections = []
        processed = self.processFrame(frame)
        lines = cv2.HoughLinesP(processed, self.houghKey["rho"], (np.pi/self.houghKey["theta"]), self.houghKey["threshold"], self.houghKey["lines"], self.houghKey["minLineLength"], self.houghKey["maxLineGap"])

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                intersectionCoord = self.intersect((x1, y1), (x2, y2), pointA, pointB)
                # intersections line
                cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 0), 2)
                if intersectionCoord is not None:
                    ix, iy = int(intersectionCoord[0]), int(intersectionCoord[1])
                    progress = self.lineProgress(intersectionCoord)
                    intersections.append((progress, (ix, iy)))

        # return the chosen intersection and draw only that one
        if len(intersections) >= 2:
            chosen = max(intersections, key=lambda x: x[0])
            prog, coord = chosen
            cv2.circle(frame, coord, 6, (0, 255, 0), -1)
            return (prog, frame)
        elif len(intersections) == 1:
            prog, coord = intersections[0]
            cv2.circle(frame, coord, 6, (0, 255, 0), -1)
            return (prog, frame)

        return (None, frame)