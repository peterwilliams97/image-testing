#!/usr/bin/env python
"""
   Compare directories of PDF files compressed by entropy.py
   Ranking is by (test PDF file size) / (reference file size)

   e.g. python weigh.py pdf.output.ccitt pdf.output
"""
import os
from glob import glob
import argparse
import time
import sys


# All files are saved in outPdfRoot.
outPdfRoot = "pdf.output"
suffixMasked = "masked.pdf"
suffixPng = "unmasked.png.pdf"
suffixJpg = "unmasked.jpg.pdf"
suffixBgd = "bgd.pdf"

usage = """Usage: python weigh.py <test directory> <reference directory>
    Compare size of *.masked.pdf files in <test directory> to those in <reference directory>
"""

def main():
    # parser = argparse.ArgumentParser()
    # args = parser.parse_args()
    # pdfFiles = args.files

    assert len(sys.argv) == 3, usage
    rootTest, rootRef = sys.argv[1:3]

    def directorize(fn):
        return os.path.dirname(os.path.join(fn, "xxx"))

    def matchFiles(outPdfRoot):
        mask = os.path.join(outPdfRoot, "*.%s" % suffixMasked)
        pdfFiles = glob(mask)
        pdfFiles = [fn for fn in pdfFiles if segmentedPdf(fn)]
        return pdfFiles

    def baseFiles(pdfFiles):
        return {os.path.basename(fn) for fn in pdfFiles}

    def joinFiles(dirName, baseNames):
        return [os.path.join(dirName, name) for name in baseNames]

    def sortKey(fn):
        szTest = fileSizeMB(os.path.join(rootTest, fn))
        szRef = fileSizeMB(os.path.join(rootRef, fn))
        return -szTest / szRef, -szTest

    rootTest = directorize(rootTest)
    rootRef = directorize(rootRef)
    filesTest = matchFiles(rootTest)
    filesRef = matchFiles(rootRef)
    filesCommon = sorted(baseFiles(filesTest) & baseFiles(filesRef), key=sortKey)

    filesTest = joinFiles(rootTest, filesCommon)
    filesRef = joinFiles(rootRef, filesCommon)

    totalSizeTest = 0.0
    totalSizeRef = 0.0
    numContracted = 0
    numExpanded = 0
    lines = []
    for i, fn in enumerate(filesCommon):
        sizeTest = fileSizeMB(os.path.join(rootTest, fn))
        sizeRef = fileSizeMB(os.path.join(rootRef, fn))
        ratio = sizeTest / sizeRef
        totalSizeTest += sizeTest
        totalSizeRef += sizeRef
        if ratio > 1.0:
            numExpanded += 1
        elif ratio < 1.0:
            numContracted += 1
        lines.append("%6d: %5.2f MB %5.2f MB %5.1f%% %s" % (i, sizeTest, sizeRef, 100.0*ratio, fn))

    n = len(filesCommon)
    if n == 0:
        return

    numSame = n - numContracted - numExpanded
    totalRatio = totalSizeTest / totalSizeRef

    print("Number expanded:   %3d %5.1f%%" % (numExpanded, 100.0 * numExpanded / n))
    print("Number same:       %3d %5.1f%%" % (numSame, 100.0 * numSame / n))
    print("Number contracted: %3d %5.1f%%" % (numContracted, 100.0 * numContracted/ n))
    print("Total:             %3d %5.1f%%" % (n, 100.0))
    print("%15s vs %s (reference). How much smaller is %s?" % (rootTest, rootRef, rootTest))
    print("Total : %5.2f MB %5.2f MB %5.1f%%" %  (totalSizeTest, totalSizeRef, 100.0*totalRatio))
    for l in lines:
        print(l)


def segmentedPdf(filename):
    """Return True is `filename` is a segmented PDF created by segment.go."""
    pngPdf = otherPdf(filename, suffixPng)
    jpgPdf = otherPdf(filename, suffixJpg)
    bgdPdf = otherPdf(filename, suffixBgd)
    return os.path.exists(pngPdf) and os.path.exists(jpgPdf) and os.path.exists(bgdPdf)


def otherPdf(filename, suffix):
    if not suffix:
        return filename
    base = filename[:-len(suffixMasked)]
    return base + suffix


def fileSizeMB(filename):
    return os.path.getsize(filename) / 1e6


main()
