import cv2
import numpy as np
import json

class LineDetector():
    def __init__(self):
        with open('config.json', 'r') as file:
            self.config = json.load(file)

    def cross(self, a, b):
        return a[0]*b[1] - a[1]*b[0]
    
    def intersect(self, A, B, x, y):
        if A[0] <= x <= B[0] or A[0]>= x >= B[0]:
            if A[0] == B[0]:
                return None
            a = (B[1]-A[1])/(B[0]-A[0])
            b = A[1] - a*A[0]
            if 0 <= a*x + b <= y:
                return (x, int(a*x + b))
        return None

    def processFrame(self, frame):
        # apply gaussian blur for less noise on the frame
        filteredFrame = cv2.GaussianBlur(frame, (int(self.config["blur"].split(',')[0]), int(self.config["blur"].split(',')[1])), float(self.config["blur"].split(',')[2]))

        # Turn the frame gray
        filteredFrame = cv2.cvtColor(filteredFrame, cv2.COLOR_BGR2GRAY)

        # filter between dark and light and make dark black and light white
        _, filteredFrame = cv2.threshold(filteredFrame, int(self.config["threshold"].split(',')[0]), int(self.config["threshold"].split(',')[1]), cv2.THRESH_BINARY)

        kernel = np.array([[int(self.config["vector1"].split(',')[0]), int(self.config["vector1"].split(',')[1]), int(self.config["vector1"].split(',')[2])],
                           [int(self.config["vector2"].split(',')[0]), int(self.config["vector2"].split(',')[1]), int(self.config["vector2"].split(',')[2])],
                           [int(self.config["vector3"].split(',')[0]), int(self.config["vector3"].split(',')[1]), int(self.config["vector3"].split(',')[2])]])
        dst = cv2.filter2D(filteredFrame, -1, kernel)
        # cv2.imshow("zwartwit", dst)
        return dst
    
    def getIntersection(self, frame):
        intersections = []
        lines = cv2.HoughLinesP(self.processFrame(frame), 1, np.pi/180, int(self.config["hough"].split(',')[0]), minLineLength=int(self.config["hough"].split(',')[1]), maxLineGap=int(self.config["hough"].split(',')[2]))
        height, width, _ = frame.shape
        if lines is not None:
            for line in lines:  
                x1,y1,x2,y2 = line[0]  
                cv2.line(frame,(x1,y1),(x2,y2),(0,0,255),2)
                intersection = self.intersect((x1,y1), (x2,y2), int(width/2+100), height)
                if intersection is not None:    
                    intersections.append(intersection)

        cv2.line(frame,(int(width/2)+100,0),(int(width/2+100),height),(255,255,0),2)
        cv2.line(frame,(0,225),(639,225),(100,10,200),2)    
        if intersections is not None and len(intersections) >= 2:
            lowest_intersection = max(intersections,)
            cv2.circle(frame, lowest_intersection, 10, (255,0,0), -1)
            return (lowest_intersection, frame)
        elif len(intersections) != 0:
            cv2.circle(frame, intersections[0], 10, (255,0,0), -1)
            return (intersections[0], frame)
        return (None, frame)