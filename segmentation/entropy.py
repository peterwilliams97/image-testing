#!/usr/bin/env python

from PIL import Image, ImageDraw
import random as pyrandom
import sys
import os.path
import shutil
import re
import subprocess
import numpy as np
from glob import glob
import argparse
from skimage.filters.rank import entropy
from skimage.morphology import disk
from skimage.io import imread, imsave
from skimage.util import img_as_ubyte
import cv2
import json
from pprint import pprint
"""
    Find high entropy regions in a PDF
"""

# All files are saved in outPdfRoot.
outPdfRoot = os.path.abspath("pdf.output")

# Entropy is measured over the entropyKernel.
entropyKernel = disk(25)

# Entropy threshold. Regions with entropy above (below) this are considered natural (synthetic).
entropyThreshold = 2.0

# Outline of high-entropy region is morphologically closed with this kernel
outlineKernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (125, 125))

# We only save high-entropy rectangles at leas this many pixels of larger.
# minArea = 10000  # 100 x 100 pixels = 1/3 x 1/3 inch
minArea = 90000  # 300 x 300 pixels = 1 x 1 inch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start", default=-1, type=int,
                        help="first page in PDF")
    parser.add_argument("-e", "--end", default=-1, type=int,
                        help="last page in PDF")
    parser.add_argument("-n", "--needed", default=1, type=int,
                        help="min number of pages required")
    parser.add_argument("files", nargs="+",
                        help="input files; glob and @ expansion performed")
    parser.add_argument("-o", "--force", action="store_true",
                        help="force processing of PDF file")

    args = parser.parse_args()
    os.makedirs(outPdfRoot, exist_ok=True)
    pdfFiles = args.files
    pdfFiles = [fn for fn in pdfFiles if not derived(fn)]
    pdfFiles.sort(key=lambda fn: (os.path.getsize(fn), fn))
    for i, fn in enumerate(pdfFiles):
        print("%3d: %4.2f MB %s" % (i, os.path.getsize(fn)/1e6, fn))
    # assert False
    processedFiles = []
    for i, inFile in enumerate(pdfFiles):
        print("*" * 80)
        print("** %3d: %s" % (i, inFile))
        if not processPdfFile(inFile, args.start, args.end, args.needed, args.force):
            continue
        processedFiles.append(inFile)
        print("Processed %d (%d of %d): %s" % (len(processedFiles), i + 1, len(pdfFiles), inFile))
    print("=" * 80)
    print("Processed %d files %s" % (len(processedFiles), processedFiles))


def derived(filename):
    name = os.path.basename(filename)
    return name.count(".") > 1


def processPdfFile(pdfFile, start, end, needed, force):
    assert needed >= 0, needed
    baseName = os.path.basename(pdfFile)
    baseBase, _ = os.path.splitext(baseName)
    outPdfFile = os.path.join(outPdfRoot, baseName)
    outJsonFile = os.path.join(outPdfRoot, "%s.json" % baseBase)
    # with open(outJsonFile, "w") as f:
    #     print("outJsonFile=%s" % outJsonFile)
    #     print("EMPTY", file=f)
    outRoot = os.path.join(outPdfRoot, baseBase)

    if not force and os.path.exists(outJsonFile):
        print("%s exists. skipping" % outPdfFile)
        return False

    if not os.path.exists(outRoot):
        os.makedirs(outRoot, exist_ok=True)
        retval = runGhostscript(pdfFile, outRoot)
        assert retval == 0
    fileList = glob(os.path.join(outRoot, "doc-*.png"))

    print("fileList=%d %s" % (len(fileList), fileList))
    numPages = 0
    pageRects = {}
    for fileNum, origFile in enumerate(fileList):
        page, ok = pageNum(origFile)
        print("#### page=%s ok=%s" % (page, ok))
        if ok:
            if start >= 0 and page < start:
                print("@1", [start, end])
                continue
            if end >= 0 and page > end:
                if not (needed >= 0 and numPages < needed):
                    print("@2", [start, end], [numPages, needed])
                    continue
        print("@31", start, end)
        rects = processPngFile(outRoot, origFile, fileNum)
        pageRects[origFile] = rects
        # if rects:
        numPages += 1
    # assert numPages > 0, pageRects

    shutil.copyfile(pdfFile, outPdfFile)
    print("=" * 80)
    pprint(pageRects)
    print("outJsonFile=%s" % outJsonFile)
    with open(outJsonFile, "w") as f:
        print(json.dumps(pageRects, indent=4, sort_keys=True), file=f)

    if numPages == 0:
        print("~~ No pages processed")
        return False
    runSegment(outJsonFile)
    return True


def processPngFile(outRoot, origFile, fileNum):

    baseName = os.path.basename(origFile)
    baseBase, _ = os.path.splitext(baseName)
    outDir = os.path.join(outRoot, "%s.%03d" % (baseBase, fileNum))
    inFile = os.path.join(outDir, baseName)

    outRoot2, outDir2 = os.path.split(outRoot)
    outFile2 = os.path.join(outRoot2, "%s.entropy" % outDir2, "%s.thresh.png" % baseBase)
    outFile2Gray = os.path.join(outRoot2, "%s.entropy" % outDir2, "%s.levels.png" % baseBase)
    print("outFile2=%s" % outFile2)
    # assert False

    imageColor = imread(origFile, as_gray=False)
    imageColor = img_as_ubyte(imageColor)

    image = imread(origFile, as_gray=True)
    image = img_as_ubyte(image)
    print("  image=%s" % desc(image))
    print("+" * 80)
    entImageGray = entropy(image, entropyKernel)
    print("entImageGray=%s" % desc(entImageGray))

    # entImageClipped is for display only
    entImageClipped = 0.5 * entImageGray / entropyThreshold  # !@#$
    entImageClipped = np.clip(entImageClipped, 0.0, 1.0)

    # entImage is the thresholded image we use for detecting natural images
    entImage = normalize(entImageGray)
    print("entImage=%s" % desc(entImage))
    entImage = img_as_ubyte(entImage)
    print("entImage=%s" % desc(entImage))

    outDir2 = os.path.dirname(outFile2)
    os.makedirs(outDir2, exist_ok=True)
    # imsave(outFile2Gray, entImageClipped)
    imsave(outFile2, entImage)

    edged = cv2.Canny(entImage, 30, 200)
    # edgedD = cv2.dilate(edged, outlineKernel)
    edgedD = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, outlineKernel)

    edgeName = outFile2 + ".edges.png"
    dilatedName = outFile2 + ".dilated.png"
    imsave(edgeName, edged)
    imsave(dilatedName, edgedD)

    contours, _ = cv2.findContours(edgedD.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print("%d contours %s" % (len(contours), type(contours)))
    # print("%d contours %s:%s" % (len(contours), list(contours.shape), contours.dtype))
    contours.sort(key=cv2.contourArea, reverse=True)
    # contours = contours[:5]  # get largest five contour area
    rects = []
    cIm = None
    cImLevel = None
    cImE = None
    cImEFull = None
    for i, c in enumerate(contours):
        area = cv2.contourArea(c)
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        x, y, w, h = cv2.boundingRect(approx)
        print("## %d: area=%g peri=%g p/a=%g %s %s" % (i, area, peri, peri*peri/area, [x, y], [w, h]))
        if area < minArea:
            continue

        rect = {"X0": x, "Y0": y, "X1": x+w, "Y1": y+h}
        rects.append(rect)

        if cIm is None:
            cIm = imageColor.copy()
        cIm = cv2.rectangle(cIm, (x, y),  (x+w, y+h), color=(255, 0, 0), thickness=20)
        cIm = cv2.rectangle(cIm, (x, y),  (x+w, y+h), color=(0, 0, 255), thickness=10)

        for r in rects[:-1]:
            if overlaps:
                print("@@@@ \n%s overlaps\n%s\n%s" % (rect, r, rects[:-1]))
                # return []
            # assert not overlaps(rect, r), "\n%s overlaps\n%s\n%s" % (rect, r, rects[:-1])

        if cImEFull is None:
            cImEFull = imageColor.copy()
        cImEFull = cv2.rectangle(cImEFull, (x, y), (x+w, y+h), color=(255, 0, 0), thickness=20)
        cImEFull = cv2.rectangle(cImEFull, (x, y), (x+w, y+h), color=(0, 0, 255), thickness=8)
        cImEFull = cv2.rectangle(cImEFull, (x, y), (x+w, y+h), color=(255, 255, 255), thickness=1)

        if cImE is None:
            cImE = edged.copy()
            cImE = cv2.cvtColor(cImE, cv2.COLOR_GRAY2RGB)
        cImE = cv2.rectangle(cImE, (x, y), (x+w, y+h), color=(255, 0, 0), thickness=10)

        if cImLevel is None:
            cImLevel = entImageClipped.copy()
            cImLevel = img_as_ubyte(cImLevel)
            cImLevel = cv2.cvtColor(cImLevel, cv2.COLOR_GRAY2RGB)
        cImLevel = cv2.rectangle(cImLevel, (x, y), (x+w, y+h), color=(255, 0, 0), thickness=10)

    if cIm is not None:
        cName = outFile2 + ".cnt.col.png"
        imsave(cName, cIm)
        print("~~~Saved %s" % cName)
    if cImLevel is not None:
        levelFile = outFile2 + ".level.png"
        imsave(levelFile, cImLevel)
        print("~#~Saved %s" % levelFile)
    if cImE is not None:
        cNameE = outFile2 + ".cnt.edge.png"
        imsave(cNameE, cImE)
        print("~#~Saved %s" % cNameE)
    if cImEFull is not None:
        cNameEFull = outFile2 + ".cnt.edge.full.png"
        imsave(cNameEFull, cImEFull)
        print("~$~Saved %s" % cNameEFull)
    # assert False
    return rects


verbose = False


def overlaps(rect1Dict, rect2Dict):
    rect1 = expandRect(rect1Dict)
    rect2 = expandRect(rect2Dict)
    bad = containsRect(rect1, rect2) or containsRect(rect1, rect2)
    if bad:
        print("    overlaps: bad=%s rect1=%s rect2=%s" % (bad, rect1, rect2))
    return bad


def containsRect(rect, rectIn):
    x0, y0, x1, y1 = rectIn
    corners = [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]
    bad = any(containsPt(rect, pt) for pt in corners)
    if bad:
        print("containsRect: bad=%s rect=%s rectIn=%s" % (bad, rect, rectIn))
    return bad


def containsPt(rect, pt):
    x0, y0, x1, y1 = rect
    x, y = pt
    bad = x0 <= x <= x1 and y0 <= y <= y1
    if bad:
        print("  containsPt: bad=%s rect=%s pt=%s" % (bad, rect, pt))
    return bad


def expandRect(rect):
    x0, y0, x1, y1 = (rect[k] for k in ("X0", "Y0", "X1", "Y1"))
    return x0, y0, x1, y1


def normalize(a):
    mn = np.amin(a)
    mx = np.amax(a)
    print("normalize: %s" % desc(a))
    a = np.array(a > entropyThreshold, dtype=a.dtype)
    print("        2: %s" % desc(a))
    return a


gsImageFormat = "doc-%03d.png"
gsImagePattern = r"^doc\-(\d+).png$"
gsImageRegex = re.compile(gsImagePattern)


def pageNum(pngPath):
    name = os.path.basename(pngPath)
    m = gsImageRegex.search(name)
    print("pageNum:", pngPath, name, m)
    if m is None:
        return 0, False
    return int(m.group(1)), True


def runGhostscript(pdf, outputDir):
    """runGhostscript runs Ghostscript on file `pdf` to create file one png file per page in
        directory `outputDir`.
    """
    print("runGhostscript: pdf=%s outputDir=%s" % (pdf, outputDir))
    outputPath = os.path.join(outputDir, gsImageFormat)
    output = "-sOutputFile=%s" % outputPath
    cmd = ["gs",
           "-dSAFER",
           "-dBATCH",
           "-dNOPAUSE",
           "-r300",
           "-sDEVICE=png16m",
           "-dTextAlphaBits=1",
           "-dGraphicsAlphaBits=1",
           "-dLastPage=20",
           output,
           pdf]

    print("runGhostscript: cmd=%s" % cmd)
    print("%s" % ' '.join(cmd))
    os.makedirs(outputDir, exist_ok=True)
    p = subprocess.Popen(cmd, shell=False)

    retval = p.wait()
    print("retval=%d" % retval)
    print("%s" % ' '.join(cmd))
    print(" outputDir=%s" % outputDir)
    print("outputPath=%s" % outputPath)
    assert os.path.exists(outputDir)

    return retval


def runSegment(outJsonFile):
    """runSegment runs segment on file `outJsonFile` to create `outSegmentFle`.
    """
    name, _ = os.path.splitext(outJsonFile)
    outSegmentFile = "%s.masked.pdf" % name

    cmd = ["./segment", outJsonFile]
    print("runSegment: cmd=%s -> %s" % (cmd, outSegmentFile))
    p = subprocess.Popen(cmd, shell=False)
    retval = p.wait()
    print("retval=%d" % retval)
    print("runSegment: cmd=%s -> %s" % (cmd, outSegmentFile))
    assert os.path.exists(outSegmentFile)

    return retval


def desc(a):
    """desc returns a descripiton on numpy array `a`
    """
    r = a.ravel()
    tr = [0.0, 0.1, 1.0, 10.0, 25.0]
    tr = tr + [50.0] + [100.0 - t for t in reversed(tr)]
    percentiles = [(t, np.percentile(r, t)) for t in tr]
    percentiles = [(t, int(round(r*1e5))/1e5) for t, r in percentiles]

    med = np.median(r)
    s = "%s:%s min=%.3f median=%g=%e mean=%3f max=%.3f\n    %s" % (
        list(a.shape), a.dtype,
        np.min(r), med, med, np.mean(r), np.max(r),
        percentiles)

    d = np.percentile(r, 50.0) - med
    assert abs(d) <= 1.e-5, "d=%g s=%s" % (d, s)
    return s


main()
