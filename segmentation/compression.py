#!/usr/bin/env python
"""
   Rank the scanned PDF files compressed by entropy.py
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

    assert len(sys.argv) > 1, "Usage: python compression.py <directory>"
    outPdfRoot = sys.argv[1]

    mask = os.path.join(outPdfRoot, "*.%s" % suffixMasked)
    pdfFiles = glob(mask)
    pdfFiles = [fn for fn in pdfFiles if segmentedPdf(fn) ]

    # pdfFiles.sort(key=lambda fn: (-suffixMB(fn, None), fn))
    # pdfFiles.sort(key=lambda fn: (-ratio(fn, suffixPng), -ratio(fn, suffixBgd), -suffixMB(fn, None), fn))

    # 2nd default
    # pdfFiles.sort(key=lambda fn: (-ratio(fn, suffixPng),
    #                               -suffixMB(fn, None),
    #                               -ratio(fn, suffixBgd),
    #                               fn))

    # pdfFiles.sort(key=lambda fn: (-ratio(fn, suffixPng),
    #                               -ratio(fn, suffixJpg), -suffixMB(fn, None), fn))

    # Default
    pdfFiles.sort(key=lambda fn: (ratio(fn, suffixPng) <= 1.0,
                                  ratio(fn, suffixPng) < 0.9,
                                  ratio(fn, suffixPng) < 0.5,
                                  -suffixMB(fn, None),
                                  ratio(fn, suffixPng),
                                  ratio(fn, suffixBgd),
                                  fn))

    # pdfFiles.sort(key=lambda fn: (-ratio(fn, suffixJpg), -ratio(fn, suffixBgd), -suffixMB(fn, None), fn))
    # pdfFiles.sort(key=lambda fn: (-ratio(fn, suffixJpg) * ratio(fn, suffixPng),
    #                               -suffixMB(fn, None), fn))
    # pdfFiles.sort(key=lambda fn: (ratio(fn, suffixBgd),
    #                               -suffixMB(fn, None),
    #                               -ratio(fn, suffixJpg),
    #                               -ratio(fn, suffixPng),
    #                               fn))
    # pdfFiles.sort(key=lambda fn: (ratio(fn, suffixBgd),
    #                               -ratio(fn, suffixPng),
    #                               -ratio(fn, suffixJpg),
    #                               -suffixMB(fn, None),
    #                               fn))

    nCompressed = 0
    nSame = 0
    nExpanded = 0
    szCompressed = 0
    szSame = 0
    szExpanded = 0

    lines = []
    totalSize = 0.0
    for i, fn in enumerate(pdfFiles):
        size = suffixMB(fn, None)
        sizePng = suffixMB(fn, suffixPng)
        sizeJpg = suffixMB(fn, suffixJpg)
        sizeBgd = suffixMB(fn, suffixBgd)
        totalSize += size
        if size < sizePng:
            nCompressed += 1
            szCompressed += size
        elif size > sizePng:
            nExpanded += 1
            szExpanded += size
        else:
            nSame += 1
            szSame += size
        # lines.append("%6d: %4.2f %5.2f (%4.2f) %5.2f MB [%s] %s" % (i,
        #     size/sizePng,  size/sizeJpg, sizeBgd/sizePng, size,
        #     time.ctime(os.path.getmtime(fn)), os.path.basename(fn)))
        lines.append("%6d: %4.2f %5.2f (%4.2f) %5.2f MB %s" % (i,
            size/sizePng,  size/sizeJpg, sizeBgd/sizePng, size,
            os.path.basename(fn)))

    n = len(pdfFiles)
    if n == 0:
        return

    print("    Compressed = %4d = %5.1f%% = %7.2f MB" % (nCompressed, 100.0 * nCompressed / n, szCompressed))
    print("          Same = %4d = %5.1f%% = %7.2f MB" % (nSame, 100.0 * nSame / n, szSame))
    print("      Expanded = %4d = %5.1f%% = %7.2f MB" % (nExpanded, 100.0 * nExpanded / n, szExpanded))
    print("         Total = %4d = %5.1f%% = %7.2f MB" % (len(pdfFiles), 100.0, totalSize))
    for l in lines:
        print(l)


def ratio(filename, suffix):
    other = otherPdf(filename, suffix)
    size = fileSizeMB(filename)
    otherSize = fileSizeMB(other)
    return size / otherSize


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


def suffixMB(filename, suffix):
    return fileSizeMB(otherPdf(filename, suffix))


def fileSizeMB(filename):
    return os.path.getsize(filename) / 1e6


main()
