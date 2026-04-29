import cv2
import numpy as np
import json

class LineDetector():
    def __init__(self):
        # with open('config.json', 'r') as file:
        #     self.config = json.load(file)
        pass
    
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

        return max(0.0, min(1.0, t))

    def processFrame(self, frame):
        # apply gaussian blur for less noise on the frame
        filteredFrame = cv2.GaussianBlur(frame, (9, 9), 1.4)

        # Turn the frame gray
        filteredFrame = cv2.cvtColor(filteredFrame, cv2.COLOR_BGR2GRAY)

        # filter between dark and light and make dark black and light white
        _, filteredFrame = cv2.threshold(filteredFrame, 200, 255, cv2.THRESH_BINARY)

        kernel = np.array([[10,5,10],
                           [5,10,5],
                           [10,5,10]])
        dst = cv2.filter2D(filteredFrame, -1, kernel)
        # cv2.imshow("zwartwit", dst)
        return dst
    
    def getIntersection(self, frame, pos):
        intersections = []
        lines = cv2.HoughLinesP(self.processFrame(frame), 1, np.pi/180, 120, minLineLength=120, maxLineGap=50)
        height, width, _ = frame.shape
        vertical_line = 225

        if pos == "left":
            bumperA = (0,0)
            bumperB = (width,height)
        if pos == "right":
            bumperA = (0,height)
            bumperB = (width,0)

        if lines is not None:
            for line in lines:  
                x1,y1,x2,y2 = line[0]  
                intersection = self.intersect((x1,y1), (x2,y2), bumperA, bumperB)
                if intersection is not None:   
                    # print(intersection)
                    intersection = self.lineProgress(bumperA, bumperB, intersection)
                    intersections.append(intersection)

        cv2.line(frame, bumperA, bumperB, (255,255,0), 2)
        # vertical line representing the bounds of detection
        
        if intersections is not None and len(intersections) >= 2:
            lowest_intersection = max(intersections,)
            return (lowest_intersection, frame)
        elif len(intersections) != 0:
            return (intersections[0], frame)
        return (None, frame)