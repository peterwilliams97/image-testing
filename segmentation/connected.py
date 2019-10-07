#!/usr/bin/python
#
# This is a copy of pdf.py from https://github.com/agl/jbig2enc modified to work with Python 3.
# The original copyright notice is below.
#
# Copyright 2006 Google Inc.
# Author: agl@imperialviolet.org (Adam Langley)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# JBIG2 Encoder https://github.com/agl/jbig2enc

"""
  Typical usage:
    jbig2 -s -S -p pdf.output.reference/hobbes/doc-001.png
    python pdf.py output > a.pdf
"""

import sys
import re
import struct
import glob
import os
import cv2
import zlib
import subprocess
import argparse
from pprint import PrettyPrinter

pprinter = PrettyPrinter(stream=sys.stderr)


# This is a very simple script to make a PDF file out of the output of a
# multipage symbol compression.
# Run ./jbig2 -s -p <other options> image1.jpeg image1.jpeg ...
# python pdf.py output > out.pdf

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--background", action="store_true",
                        help="remove background")
    parser.add_argument("-f", "--foreground", action="store_true",
                        help="remove foreground")
    parser.add_argument("files", nargs="+",
                        help="input files; glob and @ expansion performed")
    parser.add_argument("-o", "--force",
                        help="force processing of PDF file")

    args = parser.parse_args()
    files = args.files
    doBgd = not args.background
    doFgd = not args.foreground

    for inDir in files:
        # processDirectory(inDir, doBgd, doFgd)
        processDirectory(inDir, True, True)
        # processDirectory(inDir, True, False)
        # processDirectory(inDir, False, True)


dataDir = 'jbig2.data'
here = os.getcwd()
prog = os.path.join(here, 'jbig2')
assert os.path.exists(prog), prog


def processDirectory(inDir, doBgd, doFgd):
    """Create a layered PDF file from the rasters in `inDir`
        Temp files are stored in `jbigDir`
    """

    base = os.path.basename(inDir)
    base, _ = os.path.splitext(base)
    jbigDir = os.path.join(dataDir, base)
    symbolPath = os.path.join(jbigDir, 'output.sym')
    if doBgd and doFgd:
        pdfPath = base + '.connected.pdf'
    elif doBgd:
        pdfPath = base + '.connected.bgd.pdf'
    elif doFgd:
        pdfPath = base + '.connected.fgd.pdf'
    else:
        assert False, "nothing to do"

    def jbigPath(i):
        return os.path.join(jbigDir, 'output.%04d' % i)

    mask = os.path.join(os.path.abspath(inDir), '*.png')
    rasterList = sorted(glob.glob(mask))
    assert rasterList, mask
    rasterPage = {fn: jbigPath(i) for i, fn in enumerate(rasterList)}

    print("** processDirectory: inDir=%s doBgd=%s doFgd=%s pdfPath=%s" % (
          inDir, doBgd, doFgd, pdfPath), file=sys.stderr)
    print("** processDirectory: base=%s" % base, file=sys.stderr)
    print("** processDirectory: jbigDir= %s" % jbigDir, file=sys.stderr)

    os.makedirs(jbigDir, exist_ok=True)
    try:
        os.chdir(jbigDir)
        print("** cwd=%s" % os.getcwd())

        #  jbig2 -s -S -p pdf.output.reference/AIPopularPress1985/*.png
        cmd = [prog, '-s', '-S', '-p', '-a'] + rasterList
        p = subprocess.Popen(cmd, shell=False)
        retval = p.wait()
        assert retval == 0, (retval, ' '.join(cmd))
    finally:
        os.chdir(here)

    pagefiles = sorted(rasterPage.values())
    print("** processDirectory: jbigDir=%s" % jbigDir, file=sys.stderr)

    doc = buildPDF(symbolPath, pagefiles, doBgd, doFgd)
    writeFile(pdfPath, bytes(doc))


def buildPDF(symbolPath, pagefiles, doBgd, doFgd):
    """Build a PDF from JBIG2 symbol table file `symbolPath` and page files `pagefiles`.
    """
    print("** symbolPath=%s" % symbolPath, file=sys.stderr)
    print("** pagefiles= %d: %s" % (len(pagefiles), pagefiles), file=sys.stderr)

    doc = Doc()
    pages = Obj({'Type': '/Pages'})
    doc.add_object(pages)
    catalog = Obj({'Type': '/Catalog',  'Pages': ref(pages.id)})
    doc.add_catalog(catalog)
    symd = doc.add_object(Obj({}, readFile(symbolPath)))

    page_objs = []
    pagefiles.sort()
    for i, pageFile in enumerate(pagefiles):
        bgdFile = pageFile + '.png'
        jpgFile = pageFile + '.jpg'
        print("** page %d: %s" % (i, pageFile), file=sys.stderr)

        fgdContents = readFile(pageFile)

        # Big endian (Network byte order) 4 byte integers.
        width, height, xres, yres = struct.unpack('>IIII', fgdContents[11:27])

        print('** fgd (width, height, xres, yres)', [width, height, xres, yres], file=sys.stderr)

        widthPts = float(width * 72) / xres
        heightPts = float(height * 72) / yres

        if os.path.exists(bgdFile):
            bgd = cv2.imread(bgdFile)
            h, w = bgd.shape[:2]
            print('** bgd original    (width, height)', [w, h], file=sys.stderr)
            assert w <= width and h <= height, 'jpeg=%s jbig2=%s' % ([w, h], [width, height])
            if w < width or h < height:
                top = 0
                left = 0
                right = width - w
                bottom = height - h
                WHITE = [255, 255, 255]
                bgd = cv2.copyMakeBorder(bgd, top, bottom, left, right, cv2.BORDER_CONSTANT, value=WHITE)

            # bgd[:] = [255, 0, 0]   # !@#$
            bgd, bgdXform = clip(bgd)
            cv2.imwrite(jpgFile, bgd, [cv2.IMWRITE_JPEG_QUALITY, 25])
            bgdContents = readJpegFile(jpgFile)
            h, w = bgd.shape[:2]
            print('** bgd             (width, height)', [w, h], file=sys.stderr)
        else:
            bgdContents = None

        bgdIm = b'/ImBgd%d' % (i + 1)
        fgdIm = b'/ImFgd%d' % (i + 1)

        if doFgd:
            # <</Type /XObject /Subtype /Image
            # /Width 3520 /Height 2464
            # /BitsPerComponent 1
            # /ImageMask true
            # /BlackIs1 false
            # /Length 14306
            # /Filter / JBIG2Decode
            # >>

            maskXobj = Obj({'Type': '/XObject', 'Subtype': '/Image',
                        'Width': str(width), 'Height': str(height),
                        # 'ColorSpace': '/DeviceGray',
                        'BitsPerComponent': '1',
                        'ImageMask': 'true',
                        'BlackIs1': 'false',
                        'Filter': '/JBIG2Decode',
                        'DecodeParms': b'<< /JBIG2Globals %s >>' % symd.ref()},
                        fgdContents)
            black = b'\x00\x00\x00'
            fgdXobj = Obj({'Type': '/XObject', 'Subtype': '/Image',
                           'Width':'1', 'Height': '1',
                           'ColorSpace': '/DeviceRGB',
                           'BitsPerComponent': '8',
                           'Mask': '%d 0 R' % maskXobj.id
                           },
                            black)
            fgdDo = b'%s Do' % fgdIm
            fgdRef = b'%s %s ' % (fgdIm, fgdXobj.ref())
        else:
            fgdXobj = None
            fgdDo = b''
            fgdRef = b''

        if doBgd and bgdContents is not None:
            bgdDict = {'Type': '/XObject', 'Subtype': '/Image',
                       'Width': str(w),
                       'Height': str(h),
                       'ColorSpace': '/DeviceRGB',
                       'BitsPerComponent': '8',
                       'Filter': '[/FlateDecode /DCTDecode]'
                       }
            bgdXobj = Obj(bgdDict, bgdContents)
            bgdDo = b'%s Do' % bgdIm
            bgdRef = b'%s %s ' % (bgdIm, bgdXobj.ref())
        else:
            bgdXobj = None
            bgdDo = b''
            bgdRef = b''

        # scale image to widthPts x heightPts points
        scale = b'%f 0 0 %f 0 0 cm' % (widthPts, heightPts)

        # rectFill = b'''
        # q
        # 1 0 0 rg
        # 1 1 0 RG
        # 50 50 500 700 re
        # B
        # Q
        # '''

        scaledBgd = b'q %s %s Q' % (bgdXform, bgdDo)

        cmds = Obj({},  b'q %s %s %s Q' % (scale, scaledBgd, fgdDo))
        # cmds = Obj({},  b'q %s %s Q' % (scale, scaledBgd))
        # cmds = Obj({},  b'%s q %s %s %s Q' % (rectFill, scale, bgdDo, fgdDo))

        resources = Obj({'XObject': b'<<%s%s>>' % (bgdRef, fgdRef)})
        page = Obj({'Type': '/Page', 'Parent': pages.ref(),
                    'MediaBox': '[0 0 %f %f]' % (widthPts, heightPts),
                    'Contents': cmds.ref(),
                    'Resources': resources.ref()
                    })
        doc.add_objects([maskXobj, bgdXobj, fgdXobj, cmds, resources, page])
        page_objs.append(page)

        pages.d.d[b'Count'] = b'%d' % len(page_objs)
        pages.d.d[b'Kids'] = b'[%s]' % b' '.join(o.ref() for o in page_objs)

    return doc


class Doc:
  def __init__(self):
    self.objs = []
    self.pages = []
    self.catalogId = -1

  def add_objects(self, objs):
    for o in objs:
        if o is not None:
            self.add_object(o)

  def add_object(self, o):
    self.objs.append(o)
    return o

  def add_catalog(self, o):
    self.catalogId = o.id
    return self.add_object(o)

  def add_page(self, o):
    self.pages.append(o)
    return self.add_object(o)

  pos = 0

  def __bytes__(self):
    pos = 0
    a = []
    Doc.pos = 0
    offsets = []

    def add(x):
        a.append(x)
        Doc.pos += len(x) + 1

    self.objs.sort(key=lambda o: (o.stream is not None,
                                  (not o.stream.endswith(b'Do Q')) if o.stream is not None else True,
                                  b'Pages' not in o.d.d,
                                  b'Kids' not in o.d.d,
                                  o.d.d.get(b'Type', b'Z'),
                                  ))

    add(b'%PDF-1.4')
    for o in self.objs:
      offsets.append(Doc.pos)
      add(b'%d 0 obj' % o.id)
      add(bytes(o))
    xrefstart = Doc.pos
    a.append(b'xref')
    a.append(b'0 %d' % (len(offsets) + 1))
    a.append(b'0000000000 65535 f ')
    for o in offsets:
        a.append(b'%010d 00000 n ' % o)
    a.append(b'')
    a.append(b'trailer')
    a.append(b'<</Size %d\n/Root %s>>' % (len(offsets) + 1, ref(self.catalogId)))
    a.append(b'startxref')
    a.append(bytes(xrefstart))
    a.append(b'%%EOF')

    return b'\n'.join(a)


class Obj:
  next_id = 1

  def __init__(self, d={}, stream=None):
    if stream is not None:
      d[b'Length'] = b'%d' % (len(stream))
    self.d = Dict(d)
    self.stream = stream
    self.id = Obj.next_id
    Obj.next_id += 1

  def __bytes__(self):
    s = []
    s.append(bytes(self.d))
    if self.stream is not None:
      s.append(b'stream\n')
      s.append(self.stream)
      s.append(b'\nendstream\n')
    s.append(b'endobj')
    return b''.join(s)

  def ref(self):
      return ref(self.id)


class Dict:
  def __init__(self, values={}):
    self.d = {}
    for k, v in values.items():
        if isinstance(k, str):
            k = k.encode('ascii')
        if isinstance(v, str):
            v = v.encode('ascii')
        self.d[k] = v

  def __bytes__(self):
    s = [b'<<']
    for k, v in self.d.items():
        s.append(b'/%s %s\n' % (k, v))
    s.append(b'>>\n')
    return b''.join(s)


def ref(i):
    """ref returns a string with a reference to object number `i`"""
    return b'%d 0 R' % i


def readJpegFile(orig):
    # filename = orig + '.lo.jpg'
    # img = cv2.imread(orig)
    # cv2.imwrite(filename, img, [int(cv2.IMWRITE_JPEG_QUALITY), 25])
    filename = orig
    data = readFile(filename)
    compressed = zlib.compress(data, level=9)
    print("readJpegFile: %s %d -> %d = %.1f%%" % (orig, len(data), len(compressed),
                                                  100.0 * len(compressed) / len(data),
    ))
    return compressed


allScales = []


def clip(img):
    global allScales
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape[:2]
    y0, y1 = roiY(gray)
    region = gray[y0:y1, :].T
    x0, x1 = roiY(region)

    print("-- x0=%d x1=%d w=%d" % (x0, x1, w))
    print("-- y0=%d y1=%d h=%d" % (y0, y1, h))


    img = img[y0:y1, x0:x1]

    scaleX = (x1 - x0) / w
    scaleY = (y1 - y0) / h
    dx = x0 / w
    dy = (h-y1) / h
    m = b'%f 0 0 %f %f %f cm' % (scaleX, scaleY, dx, dy)

    print("-- scale = %.2f x %.2f = %.2f" % (scaleX, scaleY, scaleX * scaleY))
    allScales.append(scaleX * scaleY)
    print("-- m=%s" % m)
    return img, m


def roiY(gray):
    h, w = gray.shape[:2]
    y0 = 0
    for y in range(h):
        if any(gray[y, :] != 255):
            break
        y0 = y + 1
    y1 = 0
    for y in range(h-1, y0, -1):
        if any(gray[y, :] != 255):
            break
        y1 = y

    # print("** y0=%d y1=%d h=%d w=%d" % (y0, y1, h, w))
    return y0, y1


def readFile(filename):
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except IOError:
        print("error reading file %s" % filename, file=sys.stderr)
        raise


def writeFile(filename, obj):
    try:
        with open(filename, 'wb') as f:
            return f.write(obj)
    except IOError:
        print("error writing file %s" % filename, file=sys.stderr)
        raise


def pprint(msg):
    """Pretty print `msg` to stderr."""
    return
    pprinter.pprint(msg)


def usage(script, msg):
    if msg:
        print("%s: %s\n" % (script, msg), file=sys.stderr)
        print("Usage: %s [file_basename] > out.pdf\n" % script, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    main()
    for i, scale in enumerate(allScales):
        print("%3d: %5.3f" % (i, scale))
