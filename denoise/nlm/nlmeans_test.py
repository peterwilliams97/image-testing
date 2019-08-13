from sys import argv
import cv2
import os
from skimage.measure import compare_ssim
import numpy as np

def main():
    assert len(argv) == 3, (len(argv), argv)
    origPath = argv[1]
    scanPath = argv[2]
    orig = cv2.imread(origPath)
    scan_ = cv2.imread(scanPath)
    cv2.imwrite("orig.png", orig)
    cv2.imwrite("scan.png", scan_)
    print("origPath=%s" % origPath)
    print("scanPath=%s" % scanPath)

    denoisedScans = nlmeans(scanPath, origPath)
    results = []
    for denoisedPath, templSize, searchSize in denoisedScans:
        print("-" * 80)
        print(denoisedPath, templSize, searchSize)
        denoised = cv2.imread(denoisedPath)
        for gauss in (3, 5, 15, 25, 35):
            scanAligned = matchAffine(orig, denoised, gauss, number_of_iterations=1000)

            alignedPath = imageName("align%02d" % gauss, templSize, searchSize)
            diffPath = imageName("diff%02d" % gauss, templSize, searchSize)
            cv2.imwrite(alignedPath, scanAligned)

            # convert the images to grayscale
            grayOrig = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
            grayScan = cv2.cvtColor(scanAligned, cv2.COLOR_BGR2GRAY)
            grayOrig = contract(grayOrig, 0.05)
            grayScan = contract(grayScan, 0.05)

            # compute the Structural Similarity Index (SSIM) between the two
            # images, ensuring that the difference image is returned
            score, diff = compare_ssim(grayOrig, grayScan, full=True)
            diff = (diff * 255).astype("uint8")

            print("gauss=%d" % gauss)
            print("grayOrig=%s" % list(grayOrig.shape))
            print("grayScan=%s" % list(grayScan.shape))
            print("diff=%s" % list(diff.shape))
            print("SSIM: %s" % score)

            cv2.imwrite(diffPath, diff)

            results.append((score, gauss, templSize, searchSize, denoisedPath))

    results.sort(key=lambda x: (-x[0], x[1], x[2]))
    print("=" * 80)
    for i, r in enumerate(results):
        score, gauss, templSize, searchSize, denoisedPath= r
        print("%d: %.3f [%2d] %2d x %2d %s" %
              (i, score, gauss, templSize, searchSize, denoisedPath))


def nlmeans(scanPath, origPath):
    name = os.path.basename(scanPath)
    name, _ = os.path.splitext(name)
    # color_path = '%s_scan_color.png' % name
    # gray_path = '%s_scan_gray.png' % name

    image = cv2.imread(scanPath, cv2.IMREAD_COLOR)
    # print(type(image))
    print("%s:%s" % (image.shape, image.dtype))
    # assert image, inPath
    # source_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # cv2.imwrite(color_path, image)
    # cv2.imwrite(gray_path, source_gray)

    results = [(scanPath, 0, 0), (origPath, -1, -1)]

    # for templSize in (7, 9, 13, 15):
    #     for searchSize in (11, 13, 21, 27):
    # for templSize in reversed([29, 33]):
    #     for searchSize in reversed([105]):
    for templSize in reversed([7]):
        for searchSize in reversed([21]):
            denoisedPath = imageName('%s_denoised' % name, templSize, searchSize)
            print("nlMeans", scanPath, templSize, searchSize, denoisedPath)
            denoised = nlmeansParams(name, image, templSize, searchSize)
            cv2.imwrite(denoisedPath, denoised)
            results.append((denoisedPath, templSize, searchSize))
    return results


def nlmeansParams(name, image, templSize, searchSize):
    # denoised_gray_path = '%s_denoised_gray_%dx%d.png' % (
    #     name, templSize, searchSize)
    # denoised_gray = cv2.fastNlMeansDenoising(source_gray, None,
    #                                 templateWindowSize=templSize,
    #                                 searchWindowSize=searchSize)
    # cv2.imwrite(denoised_gray_path, denoised_gray)

    denoised = cv2.fastNlMeansDenoisingColored(image, None,
                                                templateWindowSize=templSize,
                                                searchWindowSize=searchSize)
    return denoised


def matchAffine(orig, scan, gauss, number_of_iterations=100, warp_mode=cv2.MOTION_EUCLIDEAN):
    # Convert images to grayscale
    origGray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    scanGray = cv2.cvtColor(scan, cv2.COLOR_BGR2GRAY)

    # Find size of image1
    h, w = origGray.shape[:2]

    # Define 2x3 or 3x3 matrices and initialize the matrix to identity
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        warp_matrix = np.eye(3, 3, dtype=np.float32)
    else:
        warp_matrix = np.eye(2, 3, dtype=np.float32)

    # Specify the threshold of the increment
    # in the correlation coefficient between two iterations
    termination_eps = 1e-10

    # Define termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                number_of_iterations,  termination_eps)

    # Run the ECC algorithm. The results are stored in warp_matrix.
    # print("before")
    cc, warp_matrix = cv2.findTransformECC(origGray, scanGray, warp_matrix, motionType=warp_mode,
                                           criteria=criteria,
                                           inputMask=None, gaussFiltSize=gauss)
    # print("after")
    print("warp_matrix=%s" % warp_matrix)
    flags = cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        # Use warpPerspective for Homography
        scanAligned = cv2.warpPerspective(scan, warp_matrix, (w, h), flags=flags)
        assert False
    else:
        # Use warpAffine for Translation, Euclidean and Affine
        scanAligned = cv2.warpAffine(scan, warp_matrix, (w, h), flags=flags)

    # Show final results

    print("orig=%s" % list(orig.shape))
    print("scan=%s" % list(scan.shape))
    print("scan.aligned=%s" % list(scanAligned.shape))
    return scanAligned


def contract(image, frac):
    h, w = image.shape[:2]
    dx = int(w * frac)
    dy = int(h * frac)
    return image[dy:h-dy, dx:w-dx]


def imageName(name, templSize, searchSize):
    return '%s_%dx%d.png' % (name, templSize, searchSize)


main()
