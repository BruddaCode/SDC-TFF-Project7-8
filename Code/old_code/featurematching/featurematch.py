import numpy as np
import cv2
import matplotlib.pyplot as plt
import os

def bruteForceMatch(video, image):
    
    video = cv2.cvtColor(video, cv2.IMREAD_GRAYSCALE)
    image = cv2.cvtColor(image, cv2.IMREAD_GRAYSCALE)
    
    orb = cv2.ORB_create()
    kp1, des1 = orb.detectAndCompute(video, None)
    kp2, des2 = orb.detectAndCompute(image, None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key = lambda x:x.distance)
    nMatches = 10
    img3 = cv2.drawMatches(video, kp1, image, kp2, matches[:nMatches], None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    cv2.imshow("Matches", img3)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return
    
def knnMatch(video, image):
    
    video = cv2.cvtColor(video, cv2.IMREAD_GRAYSCALE)
    image = cv2.cvtColor(image, cv2.IMREAD_GRAYSCALE)
    
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(video, None)
    kp2, des2 = sift.detectAndCompute(image, None)
    bf = cv2.BFMatcher()
    nNeighbors = 2
    matches = bf.knnMatch(des1, des2, k=nNeighbors)
    good = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good.append(m)
    img3 = cv2.drawMatches(video, kp1, image, kp2, good, None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    cv2.imshow("Matches", img3)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return
    
def flann(video, image):
    
    video = cv2.cvtColor(video, cv2.IMREAD_GRAYSCALE)
    image = cv2.cvtColor(image, cv2.IMREAD_GRAYSCALE)
    
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(video, None)
    kp2, des2 = sift.detectAndCompute(image, None)
    
    FLANN_INDEX_KDTREE = 1
    nKDTrees = 5
    nLeafChecks = 50
    nNeighbors = 2
    indexParams = dict(algorithm=FLANN_INDEX_KDTREE, trees=nKDTrees)
    searchParams = dict(checks=nLeafChecks)
    flann = cv2.FlannBasedMatcher(indexParams, searchParams)
    matches = flann.knnMatch(des1, des2, k=nNeighbors)
    matchesMask = [[0, 0] for i in range(len(matches))]
    testRatio = 0.75
    for i, (m, n) in enumerate(matches):
        if m.distance < testRatio * n.distance:
            matchesMask[i] = [1, 0]
    drawParams = dict(matchColor=(0, 255, 0), singlePointColor=(255, 0, 0), matchesMask=matchesMask, flags=cv2.DrawMatchesFlags_DEFAULT)
    img3 = cv2.drawMatchesKnn(video, kp1, image, kp2, matches, None, **drawParams)
    cv2.imshow("Matches", img3)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return


if __name__ == "__main__":
    video = cv2.VideoCapture(os.path.join("middle.mp4"))
    image = cv2.imread(os.path.join("images", "vlcsnap-2026-04-21-12h08m21s964.png"))
    
    while True:
        processTimeStart = cv2.getTickCount()
        ret, frame = video.read()
        if not ret:
            break
        # bruteForceMatch(frame, image)
        # knnMatch(frame, image)
        flann(frame, image)    
        
        processTimeEnd = cv2.getTickCount()
        processTime = (processTimeEnd - processTimeStart) / cv2.getTickFrequency()
        print(f"Processing time: {processTime:.4f} seconds")