import cv2
import numpy as np

videoL = cv2.VideoCapture("Test-Videos-12-03/test3-720/left.mp4")
videoR = cv2.VideoCapture("Test-Videos-12-03/test3-720/right.mp4")

roiHeigth = 449
roiWidth = 639

def cross(a,b):
	return a[0]*b[1] - a[1]*b[0]

def intersect (A, B, C, D):
	r = (B[0]-A[0], B[1]-A[1])
	s = (D[0]-C[0], D[1],C[1])
	CA = (C[0]-A[0], C[1]-A[1])

	denom = cross(r, s)
	if denom == 0:
		return None
	
	t = cross(CA, s) / denom
	u = cross(CA, r) / denom

	if 0 <= t <= 1 and 0  <= u <= 1:
		return (int(A[0] + t*r[0]), int(A[1] + t*r[1]))
	return None

while True:
	ret, frameL = videoL.read()
	if not ret:
		break

	ret, frameR = videoR.read()
	if not ret:
		break

	kernel = np.array([[100, 5, 100],[5, 100, 5],[100, 5, 100]])

	# Left camera roi
	filteredFrameL = frameL[0:roiHeigth, 0:roiWidth]

	filteredFrameR = frameR[0:roiHeigth, roiWidth:int(roiWidth*2+1)]

	# apply gaussian blur for less noise on the frame
	filteredFrameL = cv2.GaussianBlur(filteredFrameL, (15, 15), 1.4)
	filteredFrameR = cv2.GaussianBlur(filteredFrameR, (15, 15), 1.4)

	# Turn the frame gray
	filteredFrameL = cv2.cvtColor(filteredFrameL, cv2.COLOR_BGR2GRAY)
	filteredFrameR = cv2.cvtColor(filteredFrameR, cv2.COLOR_BGR2GRAY)
	
	filteredFrameL = cv2.inRange(filteredFrameL, 195, 255)
	filteredFrameR = cv2.inRange(filteredFrameR, 195, 255)

	# filter between dark and light and make dark black and light white
	_, filteredFrameL = cv2.threshold(filteredFrameL, 200, 255, cv2.THRESH_BINARY)
	_, filteredFrameR = cv2.threshold(filteredFrameR, 200, 255, cv2.THRESH_BINARY)

	dstL = cv2.filter2D(filteredFrameL, -1, kernel)
	dstR = cv2.filter2D(filteredFrameR, -1, kernel)

	# apply canny edge detection to see edges of objects
	filteredFrameL = cv2.Canny(filteredFrameL, threshold1=100, threshold2=150)
	filteredFrameR = cv2.Canny(filteredFrameR, threshold1=100, threshold2=150)

	kernel = np.ones((2,2), np.uint8)

	filteredFrameL = cv2.morphologyEx(filteredFrameL,cv2.MORPH_DILATE, kernel)
	filteredFrameR = cv2.morphologyEx(filteredFrameR,cv2.MORPH_DILATE, kernel)

	intersectionsL = []
	intersectionsR = []

	linesL = cv2.HoughLinesP(filteredFrameL,1,np.pi/180,120,minLineLength=80,maxLineGap=50)
	if linesL is not None:
		for line in linesL:
			x1,y1,x2,y2 = line[0]
			cv2.line(frameL,(x1,y1),(x2,y2),(0,0,255),2)  
			intersection = intersect((x1,y1), (x2,y2), (int(roiWidth/2),0), (int(roiWidth/2),roiHeigth))
			if intersection is not None:				
				intersectionsL.append(intersection)

	if intersectionsL is not None and len(intersectionsL) >= 2:
		lowest_intersectionL = max(intersectionsL)
		cv2.circle(frameL, lowest_intersectionL, 10, (255,0,0), -1)
	elif len(intersectionsL) is not 0:
		cv2.circle(frameL, intersectionsL[0], 10, (255,0,0), -1)
	
	linesR = cv2.HoughLinesP(filteredFrameR,1,np.pi/180,120,minLineLength=80,maxLineGap=50)
	if linesR is not None:
		for line in linesR:
			x1,y1,x2,y2 = line[0]
			cv2.line(frameR,(roiWidth+x1,y1),(roiWidth+x2,y2),(0,0,255),2)  
			intersection = intersect((x1,y1), (x2,y2), (int(roiWidth/2),0), (int(roiWidth/2),roiHeigth))
			if intersection is not None:			
				intersectionsR.append(intersection)

	if intersectionsR is not None and len(intersectionsR) >= 2:
		lowest_intersectionR = max(intersectionsR)	
		cv2.circle(frameR, (roiWidth+lowest_intersectionR[0], lowest_intersectionR[1]), 10, (255,0,0), -1)
	elif len(intersectionsR) is not 0:
		cv2.circle(frameR, (roiWidth+intersectionsR[0][0],intersectionsR[0][1]), 10, (255,0,0), -1)

	cv2.line(frameL,(int(roiWidth/2),0),(int(roiWidth/2),roiHeigth),(255,255,0),2)
	cv2.line(frameR,(int((roiWidth+roiWidth*2+1)/2),0),(int((roiWidth+roiWidth*2+1)/2),roiHeigth),(255,255,0),2)

	# cv2.imshow("idono", dstL)
	cv2.imshow("framel", frameL)
	cv2.imshow("frameR", frameR)
	# cv2.imshow("original", frameL[0:449, 0:639])

	if cv2.waitKey(33) & 0xFF == ord('q'):
		break