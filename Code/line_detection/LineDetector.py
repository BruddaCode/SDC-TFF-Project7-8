import numpy as np
import json
import cv2
import os
import time

class LineDetector():
    def __init__(self, lengthReferenceLine, bumperA, bumperB, side: bool):
        with open(os.path.join(os.path.dirname(__file__), '..', 'config.json'), 'r') as file:
            self.config = json.load(file)
        self.gaussianKey = self.config["FilterSettings"]["GaussianBlur"]
        self.thresholdKey = self.config["FilterSettings"]["Threshold"]
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
            print(f"Left side - Length from bumperA to intersection: {length}, Reference line length: {self.lengthReferenceLine}, Progress before inversion: {length / self.lengthReferenceLine}")
            return length / self.lengthReferenceLine
        else:
            length = np.sqrt((self.bumperA[0] - intersection[0])**2 + (self.bumperA[1] - intersection[1])**2)
            # print(f"Right side - Length from bumperA to intersection: {length}, Reference line length: {self.lengthReferenceLine}, Progress before inversion: {1 - (length / self.lengthReferenceLine)}")
            return 1 - length / self.lengthReferenceLine


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
    
    def getIntersection(self, frame, pointA, pointB):
        # collect (progress, (x, y)) pairs for each intersection
        intersections = []
        lines = cv2.HoughLinesP(self.processFrame(frame), self.houghKey["rho"], np.pi/self.houghKey["theta"], self.houghKey["threshold"], minLineLength=self.houghKey["minLineLength"], maxLineGap=self.houghKey["maxLineGap"])

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                intersectionCoord = self.intersect((x1, y1), (x2, y2), pointA, pointB)
                # intersections line
                cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                if intersectionCoord is not None:
                    ix, iy = int(intersectionCoord[0]), int(intersectionCoord[1])
                    progress = self.lineProgress(intersectionCoord)
                    intersections.append((progress, (ix, iy)))
        
        # pink
        cv2.line(frame, self.bumperA, self.bumperB, (255, 0, 255), 10)
        
        # yellow
        cv2.line(frame, pointA, pointB, (0, 255, 255), 10)

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