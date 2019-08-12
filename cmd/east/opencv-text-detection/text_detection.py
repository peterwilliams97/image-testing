# USAGE
# python text_detection.py --image images/lebron_james.jpg --east frozen_east_text_detection.pb

# import the necessary packages
from imutils.object_detection import non_max_suppression
import numpy as np
import argparse
import time
import cv2

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", type=str,
	help="path to input image")
ap.add_argument("-east", "--east", type=str,
	help="path to input EAST text detector")
ap.add_argument("-c", "--min-confidence", type=float, default=0.5,
	help="minimum probability required to inspect a region")
ap.add_argument("-w", "--width", type=int, default=320,
	help="resized image width (should be multiple of 32)")
ap.add_argument("-e", "--height", type=int, default=320,
	help="resized image height (should be multiple of 32)")
args = vars(ap.parse_args())

# load the input image and grab the image dimensions
filename = args["image"]
image = cv2.imread(filename)
assert image is not None, filename
orig = image.copy()
H, W = image.shape[:2]
print("shape=%s" % list(image.shape))
cv2.imwrite("out.png", orig)


# set the new width and height and then determine the ratio in change
# for both the width and height
newW, newH = (args["width"], args["height"])
newH = int(round(H * newW / W))
rW = W / float(newW)
rH = H / float(newH)

print("rW=%g rH=%g" % (rW, rH))

# resize the image and grab the new image dimensions
image = cv2.resize(image, (newW, newH))
H, W = image.shape[:2]
print("-shape=%s" % list(image.shape))
H2 = (H // 32) * 32
print("H=%d->%d" % (H, H2))
H = H2
image = image[:H, :]
H, W = image.shape[:2]
print("+shape=%s" % list(image.shape))

# define the two output layer names for the EAST detector model that we are interested -- the first
# is the output probabilities and the  second can be used to derive the bounding box coordinates of
#  text
layerNames = [
	"feature_fusion/Conv_7/Sigmoid",
	"feature_fusion/concat_3"]

# load the pre-trained EAST text detector
east_name = args["east"]
print("[INFO] loading EAST text detector...", east_name)
assert east_name is not None
net = cv2.dnn.readNet(east_name)

# construct a blob from the image and then perform a forward pass of
# the model to obtain the two output layer sets
blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
	(123.68, 116.78, 103.94), swapRB=True, crop=False)
start = time.time()
net.setInput(blob)
scores, geometry = net.forward(layerNames)
end = time.time()

# show timing information on text prediction
print("[INFO] text detection took {:.6f} seconds".format(end - start))

# grab the number of rows and columns from the scores volume, then
# initialize our set of bounding box rectangles and corresponding
# confidence scores
numRows, numCols = scores.shape[2:4]
rects = []
confidences = []

# loop over the number of rows
for y in range(numRows):
	# extract the scores (probabilities), followed by the geometrical
	# data used to derive potential bounding box coordinates that
	# surround text
	scoresData = scores[0, 0, y]
	xData0 = geometry[0, 0, y]
	xData1 = geometry[0, 1, y]
	xData2 = geometry[0, 2, y]
	xData3 = geometry[0, 3, y]
	anglesData = geometry[0, 4, y]

	# loop over the number of columns
	for x in range(numCols):
		# if our score does not have sufficient probability, ignore it
		if scoresData[x] < args["min_confidence"]:
			continue

		# compute the offset factor as our resulting feature maps will
		# be 4x smaller than the input image
		offsetX, offsetY = (x * 4.0, y * 4.0)

		# extract the rotation angle for the prediction and then
		# compute the sin and cosine
		angle = anglesData[x]
		cos = np.cos(angle)
		sin = np.sin(angle)

		# use the geometry volume to derive the width and height of the bounding box
		h = xData0[x] + xData2[x]
		w = xData1[x] + xData3[x]

		# compute both the starting and ending (x, y)-coordinates for
		# the text prediction bounding box
		endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
		endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
		startX = int(endX - w)
		startY = int(endY - h)

		# add the bounding box coordinates and probability score to our respective lists
		rects.append((startX, startY, endX, endY))
		confidences.append(scoresData[x])

# apply non-maxima suppression to suppress weak, overlapping bounding boxes
boxes = non_max_suppression(np.array(rects), probs=confidences)
# boxes = np.array(rects)
print("*** boxes=%s:%s" % (list(boxes.shape), boxes.dtype))
# loop over the bounding boxes
for startX, startY, endX, endY in boxes:
	# scale the bounding box coordinates based on the respective
	# ratios
	startX = int(startX * rW)
	startY = int(startY * rH)
	endX = int(endX * rW)
	endY = int(endY * rH)

	# draw the bounding box on the image
	cv2.rectangle(orig, (startX, startY), (endX, endY), (0, 255, 0), 2)

# # show the output image
# cv2.imshow("Text Detection", orig)
# cv2.waitKey(0)

cv2.imwrite("out.png", orig)
