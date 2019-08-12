from sys import argv
import cv2
import os
from skimage.measure import compare_ssim
import numpy as np

def main():
    assert len(argv) == 3, (len(argv), argv)
    origPath = argv[1]
    scanBase = argv[2]
    orig = cv2.imread(origPath)

    denoisedScans = nlmeans(scanBase)
    results = []
    for denoisedPath, templSize, searchSize in denoisedScans:
        print("-" * 80)
        print(denoisedPath, templSize, searchSize)
        scan = cv2.imread(denoisedPath)
        scanAligned = matchAffine(orig, scan)

        # convert the images to grayscale
        grayOrig = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
        grayScan = cv2.cvtColor(scanAligned, cv2.COLOR_BGR2GRAY)
        grayOrig = contract(grayOrig, 0.05)
        grayScan = contract(grayScan, 0.05)

        # compute the Structural Similarity Index (SSIM) between the two
        # images, ensuring that the difference image is returned
        score, diff = compare_ssim(grayOrig, grayScan, full=True)
        diff = (diff * 255).astype("uint8")

        print("grayOrig=%s" % list(grayOrig.shape))
        print("grayScan=%s" % list(grayScan.shape))
        print("diff=%s" % list(diff.shape))
        print("SSIM: %s" % score)

        results.append((score, templSize, searchSize, denoisedPath))

    results.sort(key=lambda x: (-x[0], x[1], x[2]))
    print("=" * 80)
    for i, r in enumerate(results):
        score, templSize, searchSize, denoisedPath= r
        print("%d: %.3f %2d x %2d %s" % (i,  score, templSize, searchSize, denoisedPath))


def nlmeans(inPath):
    name = os.path.basename(inPath)
    name, _ = os.path.splitext(name)
    color_path = '%s_color.png' % name
    gray_path = '%s_gray.png' % name

    image = cv2.imread(inPath, cv2.IMREAD_COLOR)
    print(type(image))
    print("%s:%s" % (image.shape, image.dtype))
    # assert image, inPath
    source_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(color_path, image)
    cv2.imwrite(gray_path, source_gray)

    results = [(inPath, 0, 0)]

    # for templSize in (7, 9, 13, 15):
    #     for searchSize in (11, 13, 21, 27):
    for templSize in reversed([25, 27, 29, 26]):
        for searchSize in reversed([105]):
            print("nlMeans", inPath, templSize, searchSize)
            denoisedPath = nlmeansParams(name, image, templSize, searchSize)
            results.append((denoisedPath, templSize, searchSize))
    return results


def nlmeansParams(name, image, templSize, searchSize):
    denoisedPath = '%s_denoised_%dx%d.png' % (name, templSize, searchSize)
    # denoised_gray_path = '%s_denoised_gray_%dx%d.png' % (
    #     name, templSize, searchSize)
    # denoised_gray = cv2.fastNlMeansDenoising(source_gray, None,
    #                                 templateWindowSize=templSize,
    #                                 searchWindowSize=searchSize)
    # cv2.imwrite(denoised_gray_path, denoised_gray)

    denoised = cv2.fastNlMeansDenoisingColored(image, None,
                                                templateWindowSize=templSize,
                                                searchWindowSize=searchSize)
    cv2.imwrite(denoisedPath, denoised)
    return denoisedPath


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

    number_of_iterations = 100
    # Specify the threshold of the increment
    # in the correlation coefficient between two iterations
    termination_eps = 1e-10

    # Define termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                number_of_iterations,  termination_eps)

    # Run the ECC algorithm. The results are stored in warp_matrix.
    # print("before")
    cc, warp_matrix = cv2.findTransformECC(origGray, scanGray, warp_matrix, warp_mode, criteria,
                                           inputMask=None, gaussFiltSize=5)
    # print("after")
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


main()
