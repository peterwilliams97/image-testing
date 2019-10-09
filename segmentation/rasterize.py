#!/usr/bin/env python

import sys
import shutil
import os
import re
import subprocess
import numpy as np
from glob import glob
import argparse
import cv2
import json
from pprint import pprint
from deoverlap import reduceRectDicts


# All files are saved in outPdfRoot.
outPdfRoot = os.path.abspath("pdf.rasterized")

# DPI used for the rasters being tested
rasterDPI = 300

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start", default=-1, type=int,
                        help="first page in PDF")
    parser.add_argument("-e", "--end", default=-1, type=int,
                        help="last page in PDF")
    parser.add_argument("-n", "--number", default=-1, type=int,
                        help="Max number of PDF files to process")
    parser.add_argument("-m", "--needed", default=1, type=int,
                        help="min number of pages required")
    parser.add_argument("files", nargs="+",
                        help="input files; glob and @ expansion performed")
    parser.add_argument("-f", "--force", action="store_true",
                        help="force processing of PDF file")

    args = parser.parse_args()
    os.makedirs(outPdfRoot, exist_ok=True)
    pdfFiles = args.files
    pdfFiles = [fn for fn in pdfFiles if not derived(fn)]
    pdfFiles.sort(key=lambda fn: (os.path.getsize(fn), fn))
    if args.number > 0:
        pdfFiles = pdfFiles[:args.number]
    print("Processing %d files" % len(pdfFiles))
    for i, fn in enumerate(pdfFiles):
        print("%3d: %4.2f MB %s" % (i, os.path.getsize(fn)/1e6, fn))

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
    """Return True if `filename` is one of the PDF files we create.
    """
    name = os.path.basename(filename)
    return name.count(".") > 1


def processPdfFile(pdfFile, start, end, needed, force):
    assert needed >= 0, needed
    baseName = os.path.basename(pdfFile)
    baseBase, _ = os.path.splitext(baseName)
    outPdfFile = os.path.join(outPdfRoot, baseName)
    outJsonFile = os.path.join(outPdfRoot, "%s.json" % baseBase)
    outRoot = os.path.join(outPdfRoot, baseBase)

    if not force and os.path.exists(outJsonFile):
        print("%s exists. skipping" % outPdfFile)
        return False

    if not os.path.exists(os.path.join(outRoot, "doc-001.png")):
        os.makedirs(outRoot, exist_ok=True)
        retval = runGhostscript(pdfFile, outRoot, resample=1)
        if retval != 0:
            print("runGhostscript failed outRoot=%s retval=%d. skipping" % (outPdfFile, retval))
            return False
        assert retval == 0
    searchMask = os.path.join(outRoot, "doc-*.png")
    print("searchMask=%s" % searchMask)
    fileList = glob(searchMask)
    fileList = [fn for fn in fileList if ".denoised.png" not in fn]

    print("fileList=%d %s" % (len(fileList), fileList))
    return True


gsImageFormat = "doc-%03d.png"


def runGhostscript(pdf, outputDir, resample=1):
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
           "-r%d" % (rasterDPI * resample),
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


main()
