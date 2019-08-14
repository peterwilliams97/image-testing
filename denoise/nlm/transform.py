from sys import argv
import cv2
import os
from skimage.measure import compare_ssim
import numpy as np
from collections import defaultdict
from time import time


def main():
    assert len(argv) > 1, (len(argv), argv)
    files = []
    resultsAll = []

    t0 = time()
    for i, origPath in enumerate(argv[1:]):
        print("@" * 90)
        orig = cv2.imread(origPath)
        if orig is None:
            print("%s not an image. skipping" % origPath)
        h, w = orig.shape[:2]
        print("%d: %s %d x %d" % (i, origPath, w, h))
        if h < 100 or w < 100:
            print("skipping")
            continue
        try:
            results = runTest(origPath, orig)
        except Exception as e:
            print("runTest failed", e)
            continue
        resultsAll.append(results)
        files.append(origPath)
        dt = time() - t0
        print("**** dt=%.2f n=%d" % (dt, len(resultsAll)))
        if dt > 3600 and len(resultsAll) >= 2:
            break
    n = len(resultsAll)
    assert n >=2, n

    resultsMap = defaultdict(list)
    for results in resultsAll:
        for i, r in enumerate(results):
            score, theta, gauss, numIters, m0, m = r
            key = tuple([theta, gauss, numIters])
            resultsMap[key].append(r)

    keys = sorted(resultsMap)
    results = []
    for k in keys:
        score = 0.0
        diff = 0.0
        rr = []
        for i in range(n):
            r = resultsMap[k][i]
            scoreI, theta, gauss, numIters, m0, m = r
            dm = m-m0
            v = np.sum(np.abs(dm))
            score += scoreI
            diff += v
            rr.append(r)
        results.append((score / n, diff / n, i, rr))

    results.sort(key=lambda x: (x[1], -x[0], x[2]))
    print("=" * 80)
    print("%d %s" % (len(files), files))
    for i, rlst in enumerate(results):
        score, diff, _, rr = rlst
        scoreI, theta, gauss, numIters, m0, m = rr[0]
        print("%d: %.3f %g %.2f %2d %d " % (i, score, diff, theta, gauss, numIters))
        for j, r in enumerate(rr):
            scoreI, theta, gauss, numIters, m0, m = r
            dm = m - m0
            v = np.sum(np.abs(dm))
            print("\t%d: %.3f %g %s" % (j, scoreI, v, files[j]))


def runTest(origPath, orig):
    h, w = orig.shape[:2]
    theta = 2 # degrees
    tx, ty = 0, 0
    M = cv2.getRotationMatrix2D((h/2, w/2), theta, 1)
    print("M=\n%s" % M)
    M += np.float32([[0, 0, tx], [0, 0, ty]])
    print("M=\n%s" % M)

    flags = cv2.INTER_LINEAR

    results = []
    for theta in (0.0, 0.5, 1.0, 2.0, 4.0)[3:4]:
        warped = cv2.warpAffine(orig, M, (w, h), flags=flags)
        warpPath = "warp_%.2f_%d_%d" % (theta, tx, ty)

        print("  orig=%s" % describe(orig))
        print("warped=%s" % describe(warped))
        cv2.imwrite(warpPath+".png", warped)

        for gauss in (5, 7):
            for numIters in (100, 200, 500):
                scanAligned, warp_matrix = matchAffine(orig, warped, gauss, numIters)

                alignedPath = "align%02d_%s.png" % (gauss, warpPath)
                diffPath = "diff%02d_%s.png" % (gauss, warpPath)
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
                # print("grayOrig=%s" % list(grayOrig.shape))
                # print("grayScan=%s" % list(grayScan.shape))
                # print("diff=%s" % list(diff.shape))
                print("SSIM: %s" % score)

                cv2.imwrite(diffPath, diff)

                results.append((score, theta, gauss, numIters, M, warp_matrix))

    return results



def matchAffine(orig, scan, gauss, numIters=100, warp_mode=cv2.MOTION_EUCLIDEAN):
    # Convert images to grayscale
    origGray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    scanGray = cv2.cvtColor(scan, cv2.COLOR_BGR2GRAY)

    # print("origGray=%s" % describe(origGray))
    # print("scanGray=%s" % describe(scanGray))

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
                numIters,  termination_eps)

    # Run the ECC algorithm. The results are stored in warp_matrix.
    # print("before")
    cc, warp_matrix = cv2.findTransformECC(origGray, scanGray, warp_matrix, motionType=warp_mode,
                                           criteria=criteria,
                                           inputMask=None, gaussFiltSize=gauss)
    # print("after")
    print("warp_matrix=\n%s" % warp_matrix)
    flags = cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        # Use warpPerspective for Homography
        scanAligned = cv2.warpPerspective(scan, warp_matrix, (w, h), flags=flags)
        assert False
    else:
        # Use warpAffine for Translation, Euclidean and Affine
        scanAligned = cv2.warpAffine(scan, warp_matrix, (w, h), flags=flags)

    # Show final results

    # print("orig=%s" % list(orig.shape))
    # print("scan=%s" % list(scan.shape))
    # print("scan.aligned=%s" % list(scanAligned.shape))
    return scanAligned, warp_matrix


def contract(image, frac):
    h, w = image.shape[:2]
    dx = int(w * frac)
    dy = int(h * frac)
    return image[dy:h-dy, dx:w-dx]


def imageName(name, templSize, searchSize):
    return '%s_%dx%d.png' % (name, templSize, searchSize)


def describe(m):
    return "%s:%s" % (list(m.shape), m.dtype)

main()
