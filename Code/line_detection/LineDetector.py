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
        self.laneWidth = 0.52

        self.clahe = cv2.createCLAHE(
            clipLimit=self.claheKey["clipLimit"],
            tileGridSize=(self.claheKey["tileGridSize"], self.claheKey["tileGridSize"]),
        )
        self.filterKernel = np.array([[10, 5, 10], [5, 10, 5], [10, 5, 10]])

        # side is true for left and false for right
        # this is used to correctly calculate progress along the line
        self.side = side

        # stale value tracking for line detection
        self.MAX_STALE_TIME = 0.4
        self.lastLeftHit  = None
        self.lastRightHit = None
        self.lastLeftTime  = 0.0
        self.lastRightTime = 0.0

    # calculates to see if the given lines intersect
    # A and B are a line and C and D are a line, both lines are finite
    # A, B, C and D should be the endpoints of your line and not just any random points on your line
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

        if not self.within_segment(px, py, A, B) or not self.within_segment(px, py, C, D):
            return None

        return (int(px), int(py))
    
    def within_segment(self, px, py, P, Q, epsilon=1.0):
        min_x = min(P[0], Q[0]) - epsilon
        max_x = max(P[0], Q[0]) + epsilon
        min_y = min(P[1], Q[1]) - epsilon
        max_y = max(P[1], Q[1]) + epsilon
        return min_x <= px <= max_x and min_y <= py <= max_y
    
    # this function calculates how far along the reference line the intersection is
    # for this we give the referenceline a length of 1
    # the closer to 1, the closer to the kart the intersection was
    # the calculation is just pythagoras, since we are calculating the length of diagonal lines
    def lineProgress(self, intersection):
        if self.side:
            length = np.sqrt((self.bumperA[0] - intersection[0])**2 + (self.bumperA[1] - intersection[1])**2)
            return length / self.lengthReferenceLine
        else:
            length = np.sqrt((self.bumperA[0] - intersection[0])**2 + (self.bumperA[1] - intersection[1])**2)
            return 1 - length / self.lengthReferenceLine

    # taking all the necesary steps to prepare the frame for the houghlines transform
    def processFrame(self, frame):
                
        # convert to hls and apply CLAHE to the lightness channel
        hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        h, l, s = cv2.split(hls)
        l = self.clahe.apply(l)
        hls = cv2.merge((h, l, s))
        frame = cv2.inRange(hls, (self.mergeRangeKey["lower"][0], self.mergeRangeKey["lower"][1], self.mergeRangeKey["lower"][2]), (self.mergeRangeKey["upper"][0], self.mergeRangeKey["upper"][1], self.mergeRangeKey["upper"][2]))
        frame = cv2.bitwise_and(l, l, mask=frame)
        
        # apply gaussian blur to reduce noise
        frame = cv2.GaussianBlur(frame, (self.gaussianKey["KernelSize"], self.gaussianKey["KernelSize"]), self.gaussianKey["SigmaX"])
        
        # apply Canny edge detection
        frame = cv2.Canny(frame, self.cannyKey["threshold1"], self.cannyKey["threshold2"], self.cannyKey["apertureSize"])
        
        frame = cv2.filter2D(frame, -1, self.filterKernel)

        return frame
    
    # main function of the LineDetector class, returns the intersection with the referenceline and how far along that line it is
    def getIntersection(self, frame, pointA, pointB):
        # collect (progress, (x, y)) pairs for each intersection
        intersections = []
        processed = self.processFrame(frame)
        lines = cv2.HoughLinesP(processed, self.houghKey["rho"], (np.pi/self.houghKey["theta"]), self.houghKey["threshold"], self.houghKey["lines"], self.houghKey["minLineLength"], self.houghKey["maxLineGap"])

        # take each line returned by the houghlines transform and calculate its intersection
        # if it intersects the reference line, calculate its progress along the reference line and add to the array
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
        # the chosen intersection is the on closest to the kart as this will most of the time be the inside part of the white line
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

    # function to check if either of the side cameras saw a line
    # this fucntion calculates where the centre of the kart currently is, calls this laneCentre and returs it for the PID to compute
    # also returns the mode of which side it saw a line
    # different modes being, both, single-left, single-right, or lost
    def checkForHit(self, leftHit, rightHit, currTime, prevCenter):
        # update stored values if we have fresh detections
        if leftHit is not None:
            self.lastLeftHit  = leftHit
            self.lastLeftTime = currTime
        if rightHit is not None:
            self.lastRightHit  = rightHit
            self.lastRightTime = currTime

        # check if stored values are still within the stale timeout
        leftValid  = self.lastLeftHit  is not None and (currTime - self.lastLeftTime)  < self.MAX_STALE_TIME
        rightValid = self.lastRightHit is not None and (currTime - self.lastRightTime) < self.MAX_STALE_TIME

        # check for which mode to return and calculate the to return laneCentre
        if leftValid and rightValid:
            width = self.lastLeftHit + self.lastRightHit
            if width > self.laneWidth:
                self.lastLeftHit = self.lastLeftHit + (width - self.laneWidth)
            mode = "both"
            laneCenter = self.lastLeftHit / (width)
        elif leftValid:
            mode = "single-left"
            laneCenter = self.lastLeftHit
        elif rightValid:
            mode = "single-right"
            laneCenter = 1 - self.lastRightHit
        else:
            mode = "lost"
            laneCenter = prevCenter  # hold last known center
        
        return mode, laneCenter