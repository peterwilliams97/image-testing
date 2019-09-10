#!/usr/bin/env python
"""
   Compare directories of PDF files compressed by entropy.py
   Ranking is by (mixture PDF file size) / (pure PNG file size)
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

def main():
    # parser = argparse.ArgumentParser()
    # args = parser.parse_args()
    # pdfFiles = args.files

    assert len(sys.argv) == 3, "Usage: python weigh.py <directory1> <directory2>"
    outPdfRoot1, outPdfRoot2 = sys.argv[1:3]

    def directorize(fn):
        return os.path.dirname(os.path.join(fn, "xxx"))

    def matchFiles(outPdfRoot):
        mask = os.path.join(outPdfRoot, "*.%s" % suffixMasked)
        pdfFiles = glob(mask)
        pdfFiles = [fn for fn in pdfFiles if testedPdf(fn)]
        return pdfFiles

    def baseFiles(pdfFiles):
        return {os.path.basename(fn) for fn in pdfFiles}

    def joinFiles(dirName, baseNames):
        return [os.path.join(dirName, name) for name in baseNames]

    def sortKey(fn):
        sz1 = fileSizeMB(os.path.join(outPdfRoot1, fn))
        sz2 = fileSizeMB(os.path.join(outPdfRoot2, fn))
        return sz2 / sz1

    outPdfRoot1 = directorize(outPdfRoot1)
    outPdfRoot2 = directorize(outPdfRoot2)
    pdfFiles1 = matchFiles(outPdfRoot1)
    pdfFiles2 = matchFiles(outPdfRoot2)
    commonFiles = sorted(baseFiles(pdfFiles1) & baseFiles(pdfFiles2), key=sortKey)

    pdfFiles1 = joinFiles(outPdfRoot1, commonFiles)
    pdfFiles2 = joinFiles(outPdfRoot2, commonFiles)

    totalSize1 = 0.0
    totalSize2 = 0.0
    numContracted = 0
    numExpanded = 0
    lines = []
    for i, fn in enumerate(commonFiles):
        size1 = fileSizeMB(os.path.join(outPdfRoot1, fn))
        size2 = fileSizeMB(os.path.join(outPdfRoot2, fn))
        ratio = size1 / size2
        totalSize1 += size1
        totalSize2 += size2
        if ratio > 1.0:
            numExpanded += 1
        elif ratio < 1.0:
            numContracted += 1
        lines.append("%6d: %5.2f MB %5.2f MB %5.1f%% %s" % (i, size1, size2, 100.0*ratio, fn))

    n = len(commonFiles)
    if n == 0:
        return

    numSame = n - numContracted - numExpanded
    totalRatio = totalSize1 / totalSize2

    print("Number expanded:   %3d %5.1f%%" % (numExpanded, 100.0 * numExpanded / n))
    print("Number same:       %3d %5.1f%%" % (numSame, 100.0 * numSame / n))
    print("Number contracted: %3d %5.1f%%" % (numContracted, 100.0 * numContracted/ n))
    print("Total:             %3d %5.1f%%" % (n, 100.0))
    print("%15s vs %s (reference). How much smaller is %s?" % (outPdfRoot1, outPdfRoot2, outPdfRoot1))
    print("Total : %5.2f MB %5.2f MB %5.1f%%" %  (totalSize1, totalSize2, 100.0*totalRatio))
    for l in lines:
        print(l)


def ratio(filename, suffix):
    other = otherPdf(filename, suffix)
    size = fileSizeMB(filename)
    otherSize = fileSizeMB(other)
    return size / otherSize


def testedPdf(filename):
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
