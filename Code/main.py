import cv2
import numpy as np

video = cv2.VideoCapture("code/right.mp4")
video.open("right.mp4")

def region_of_interest(img, vertices):
    mask = np.zeros_like(img)
    cv2.fillPoly(mask, vertices, 255)
    masked_image = cv2.bitwise_and(img, mask)
    return masked_image

def get_y(line, x_norm):
    x1, y1, x2, y2 = line
    if x1 == x2:  # vertical line
        return y1
    if (x1 - x_norm) * (x2 - x_norm) > 0:  # line does not cross x_norm
        return None

    m = (y2 - y1) / (x2 - x1)
    y = y1 + (x_norm - x1) * m
    return int(y)

while True:
	ret, frame = video.read()
	if not ret:
		break

	# linedetection.process_frame(frame, "RIGHT")
	# gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

	# # Apply Gaussian Blur to reduce noise
	# blur = cv2.GaussianBlur(gray, (5, 5), 1.4)

	# # Apply Canny Edge Detector
	# edges = cv2.Canny(blur, threshold1=10, threshold2=150)
	# lines = cv2.HoughLinesP(edges,1,np.pi/180,100,minLineLength=50,maxLineGap=300)

	# try:
	# 	if not lines.size == 0:
	# 		for line in lines:
	# 			x1,y1,x2,y2 = line[0]
	# 			cv2.line(frame,(x1,y1),(x2,y2),(0.255,0),2)
	# except:
	# 	print("kut zooi")
		

	

	# cv2.imshow("Houghlines", frame)



	# apply gaussian blur for less noise on the frame
	filteredFrame = cv2.GaussianBlur(frame, (5, 5), 0)

	# Turn the frame gray
	filteredFrame = cv2.cvtColor(filteredFrame, cv2.COLOR_BGR2GRAY)

	# filter between dark and light and make dark black and light white
	_, filteredFrame = cv2.threshold(filteredFrame, 200, 255, cv2.THRESH_BINARY)

	# apply canny edge detection to see adges of objects
	filteredFrame = cv2.Canny(filteredFrame, threshold1=70, threshold2=200)

	height, width = filteredFrame.shape
	y_norm = int(height * 0.2)


	x_norm = int(540/848 * width)

	roi_border_x = int(width / 8 * 3)
	region_vertices = [(roi_border_x, 0), (width, 0), (width, height), (roi_border_x, height)] # rechterkant

	roi = region_of_interest(filteredFrame, np.array([region_vertices], np.int32))

	# apply houghlines to visualize lines between points
	lines = cv2.HoughLinesP(roi, 1, np.pi / 180, 50, np.array([]), minLineLength=50, maxLineGap=300)
	y_at_target_values = []

	if lines is not None:
		for line in lines:
			x1, y1, x2, y2 = line[0]

			y_val = get_y([x1,y1,x2,y2], x_norm)
			if y_val is not None:
				y_at_target_values.append(y_val)

				x1,y1,x2,y2 = line[0]
				cv2.line(frame, (x1,y1),(x2,y2),(0,0,255),3)                

	cv2.imshow("white", filteredFrame)
	cv2.imshow("original", frame[0:319, 210:640])

	if cv2.waitKey(1) & 0xFF == ord('q'):
		break