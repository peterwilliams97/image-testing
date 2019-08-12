# USAGE
# python image_diff.py
#     -o ~/extracted.images/restoration/adress-change/xx001.png
#     -s ~/extracted.images/restoration/adress-change/ricoh-c2004/scan_abigailn_2019-08-05-16-39-26_page1_img1.x.jpg
# import the necessary packages
from matplotlib import pyplot as plt
from skimage.measure import compare_ssim
import argparse
import imutils
import cv2
import numpy as np

# help(cv2.findTransformECC)
# help(cv2.warpAffine)

def match(orig, scan):
    h, w = orig.shape
    mx = w // 10
    my = h // 10
    orig = orig[my:h - my, x:w - mx]
    # All the 6 methods for comparison in a list
    methods = ['cv.TM_CCOEFF', 'cv.TM_CCOEFF_NORMED', 'cv.TM_CCORR',
               'cv.TM_CCORR_NORMED', 'cv.TM_SQDIFF', 'cv.TM_SQDIFF_NORMED']
    for meth in methods:
        img = scan.copy()
        method = eval(meth)
        # Apply template Matching
        res = cv2.matchTemplate(img, template, method)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
        # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
        if method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]:
            top_left = min_loc
        else:
            top_left = max_loc
        bottom_right = (top_left[0] + w, top_left[1] + h)
        cv.rectangle(img, top_left, bottom_right, 255, 2)
        plt.subplot(121), plt.imshow(res, cmap='gray')
        plt.title('Matching Result'), plt.xticks([]), plt.yticks([])
        plt.subplot(122), plt.imshow(img, cmap='gray')
        plt.title('Detected Point'), plt.xticks([]), plt.yticks([])
        plt.suptitle(meth)
        plt.show()


MIN_MATCH_COUNT = 10

def match2(orig, scan):
    img1 = orig          # queryImage
    img2 = scan  # trainImage

    # Initiate SIFT detector
    sift = cv2.SIFT()

    # find the keypoints and descriptors with SIFT
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)

    FLANN_INDEX_KDTREE = 0
    index_params = {algorithm: FLANN_INDEX_KDTREE, trees: 5}
    search_params = {checks: 50}

    flann = cv2.FlannBasedMatcher(index_params, search_params)

    matches = flann.knnMatch(des1, des2, k=2)

    # store all the good matches as per Lowe's ratio test.
    good = []
    for m, n in matches:
        if m.distance < 0.7*n.distance:
            good.append(m)

    if len(good) > MIN_MATCH_COUNT:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        matchesMask = mask.ravel().tolist()

        h, w = img1.shape
        pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, M)

        img2 = cv2.polylines(img2, [np.int32(dst)], True, 255, 3, cv2.LINE_AA)
    else:
        print("Not enough matches are found - %d/%d" % (len(good), MIN_MATCH_COUNT))
        matchesMask = None


def matchAffine(orig, scan):
  # Convert images to grayscale
    origGray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    scanGray = cv2.cvtColor(scan, cv2.COLOR_BGR2GRAY)

    # Find size of image1
    sz = origGray.shape

    # Define the motion model
    warp_mode = cv2.MOTION_AFFINE

    # Define 2x3 or 3x3 matrices and initialize the matrix to identity
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        warp_matrix = np.eye(3, 3, dtype=np.float32)
    else:
        warp_matrix = np.eye(2, 3, dtype=np.float32)

    # No correction
    # 0.7760207792936938

    # Specify the number of iterations.
    # number_of_iterations = 50
    # warp_matrix = [[9.8823208e-01 - 1.7501101e-03  1.5572790e+01]
    #                [1.3905101e-03  1.0049857e+00 - 1.5902575e+01]]
    # orig = [3300, 2550, 3]
    # scan = [3300, 2550, 3]
    # scan.aligne = [3300, 2550, 3]
    # SSIM: 0.7766886458956823

    # number_of_iterations = 500
    # warp_matrix = [[9.5359802e-01  9.3235094e-03  5.1035732e+01]
    #               [2.5977085e-03  1.0188251e+00 - 5.0118095e+01]]
    # orig = [3300, 2550, 3]
    # scan = [3300, 2550, 3]
    # scan.aligne = [3300, 2550, 3]
    # SSIM: 0.7687851662166546

    # number_of_iterations = 2500
    # warp_matrix = [[9.5508265e-01  9.1791162e-03  4.8501984e+01]
    #               [2.5657057e-03  1.0188868e+00 - 5.0192223e+01]]
    # orig = [3300, 2550, 3]
    # scan = [3300, 2550, 3]
    # scan.aligne = [3300, 2550, 3]
    # SSIM: 0.7687692735152462

    number_of_iterations = 1000
    # Specify the threshold of the increment
    # in the correlation coefficient between two iterations
    termination_eps = 1e-10

    # Define termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                number_of_iterations,  termination_eps)

    # Run the ECC algorithm. The results are stored in warp_matrix.
    print("before")
    cc, warp_matrix = cv2.findTransformECC(origGray, scanGray, warp_matrix, warp_mode, criteria,
                                           inputMask=None, gaussFiltSize=5)
    print("after")
    print("warp_matrix=%s" % warp_matrix)
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        # Use warpPerspective for Homography
        im2_aligned = cv2.warpPerspective(
            scan, warp_matrix, (sz[1], sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        assert False
    else:
        # Use warpAffine for Translation, Euclidean and Affine
        im2_aligned = cv2.warpAffine(
            scan, warp_matrix, (sz[1], sz[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)

    # Show final results
    # cv2.imshow("orig", orig)
    # cv2.imshow("scan", scan)
    # cv2.imshow("Aligned Scan", im2_aligned)
    # cv2.waitKey(0)
    cv2.imwrite("orig.png", orig)
    cv2.imwrite("scan.png", scan)
    cv2.imwrite("scan.aligned.png", im2_aligned)
    print("orig=%s" % list(orig.shape))
    print("scan=%s" % list(scan.shape))
    print("scan.aligned=%s" % list(im2_aligned.shape))
    return im2_aligned


def contract(image, frac):
    h, w = image.shape[:2]
    dx = int(w * frac)
    dy = int(h * frac)
    return image[dy:h-dy, dx:w-dx]


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--orig", required=True, help="original image")
ap.add_argument("-s", "--scan", required=True, help="scanned image")
args = vars(ap.parse_args())

# load the two input images
orig = cv2.imread(args["orig"])
scan = cv2.imread(args["scan"])
scan_aligned = matchAffine(orig, scan)
# scan_aligned = orig

# convert the images to grayscale
grayOrig = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
grayScan = cv2.cvtColor(scan_aligned, cv2.COLOR_BGR2GRAY)
grayOrig = contract(grayOrig, 0.05)
grayScan = contract(grayScan, 0.05)

# compute the Structural Similarity Index (SSIM) between the two
# images, ensuring that the difference image is returned
score, diff = compare_ssim(grayOrig, grayScan, full=True)
diff = (diff * 255).astype("uint8")

print("grayOrig=%s" % list(grayOrig.shape))
print("grayScan=%s" % list(grayScan.shape))
print("diff=%s" % list(diff.shape))
print("SSIM: %s" %score)

# threshold the difference image, followed by finding contours to
# obtain the regions of the two input images that differ
thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)

# loop over the contours
for c in cnts:
	# compute the bounding box of the contour and then draw the
	# bounding box on both input images to represent where the two
	# images differ
	(x, y, w, h) = cv2.boundingRect(c)
	cv2.rectangle(orig, (x, y), (x + w, y + h), (0, 0, 255), 2)
	cv2.rectangle(scan, (x, y), (x + w, y + h), (0, 0, 255), 2)

# show the output images
cv2.imshow("Diff", diff)
cv2.imshow("Thresh", thresh)
# cv2.waitKey(0)

cv2.imwrite("diff.png", diff)
