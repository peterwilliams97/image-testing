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
from pprint import PrettyPrinter

pprinter = PrettyPrinter(stream=sys.stderr)


# This is a very simple script to make a PDF file out of the output of a
# multipage symbol compression.
# Run ./jbig2 -s -p <other options> image1.jpeg image1.jpeg ...
# python pdf.py output > out.pdf

dpi = 72


def main():
    if sys.platform == "win32":
        import msvcrt
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

    if len(sys.argv) == 2:
        sym = sys.argv[1] + '.sym'
        pages = glob.glob(sys.argv[1] + '.[0-9]*')
    elif len(sys.argv) == 1:
        sym = 'symboltable'
        pages = glob.glob('page-*')
    else:
        usage(sys.argv[0], "wrong number of args!")

    print("** argv=%d %s" % (len(sys.argv), sys.argv[1:]), file=sys.stderr)
    if not os.path.exists(sym):
        usage(sys.argv[0], "symbol table %s not found!" % sym)
    elif len(pages) == 0:
        usage(sys.argv[0], "no pages found!")

    pages = [p for p in pages if isOutput(p)]
    jig2Main(sym, pages)


OUTPUT = re.compile(r'\.\d+$')


def isOutput(p):
    return OUTPUT.search(p) is not None


def jig2Main(symbolPath='symboltable', pagefiles=glob.glob('page-*')):
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
        # assert os.path.exists(bgdFile), bgdFile

        if os.path.exists(bgdFile):
            bgd = cv2.imread(bgdFile)
            assert bgd is not None, bgdFile
            cv2.imwrite(jpgFile, bgd, [cv2.IMWRITE_JPEG_QUALITY, 25])
            bgdContents = readFile(jpgFile)
            h, w = bgd.shape[:2]
            print('** bgd (width, height)', [w, h], file=sys.stderr)
        else:
            bgdContents = None

        fgdContents = readFile(pageFile)

        # Big endian. Network byte order
        width, height, xres, yres = struct.unpack('>IIII', fgdContents[11:27])

        print('** fgd (width, height, xres, yres)', [width, height, xres, yres], file=sys.stderr)

        if xres == 0:
            xres = dpi
        if yres == 0:
            yres = dpi

        widthPts = float(width * 72) / xres
        heightPts = float(height * 72) / yres

        if bgdContents is not None:
            bgdXobj = Obj({'Type': '/XObject', 'Subtype': '/Image',
                        'Width': str(w),
                        'Height': str(h),
                        'ColorSpace': '/DeviceRGB',
                        'BitsPerComponent': '8',
                        'Filter': '/DCTDecode'},
                        bgdContents)
            bgdDo = b'/Im%d Do' % bgdXobj.id
            bgdRef = b'/Im%d %s' % (bgdXobj.id, ref(bgdXobj.id))
        else:
            bgdXobj = None
            bgdDo = b''
            bgdRef = b''

        fgdXobj = Obj({'Type': '/XObject', 'Subtype': '/Image',
                    'Width': str(width),
                    'Height': str(height),
                    'ColorSpace': '/DeviceGray',
                    'ImageMask': 'true',
                    'BlackIs1': 'false',
                    'BitsPerComponent': '1',
                    'Filter': '/JBIG2Decode',
                    'DecodeParms': b'<< /JBIG2Globals %s >>' % symd.ref()},
                    fgdContents)
        fgdDo = b'/Im%d Do' % fgdXobj.id
        fgdRef = b'/Im%d %s' % (fgdXobj.id, fgdXobj.ref())

        # scale image to widthPts x heightPts points
        scale = b'%f 0 0 %f 0 0 cm' % (widthPts, heightPts)

        cmds = Obj({},  b'q %s %s %s Q' % (scale, bgdDo, fgdDo))
        resources = Obj({'XObject': b'<<%s%s>>' % (bgdRef, fgdRef)})
        page = Obj({'Type': '/Page', 'Parent': pages.ref(),
                    'MediaBox': '[0 0 %f %f]' % (widthPts, heightPts),
                    'Contents': cmds.ref(),
                    'Resources': resources.ref()
                    })
        doc.add_objects([bgdXobj, fgdXobj, cmds, resources, page])
        page_objs.append(page)

        pages.d.d[b'Count'] = b'%d' % len(page_objs)
        pages.d.d[b'Kids'] = b'[%s]' % b' '.join(o.ref() for o in page_objs)

    sys.stdout.buffer.write(bytes(doc))


class Dict:
  def __init__(self, values = {}):
    self.d = {}
    for k, v in values.items():
        if isinstance(k, str):
            k = k.encode('ascii')
        if isinstance(v, str):
            v = v.encode('ascii')
        self.d[k] = v

  def __bytes__(self):
    s = [b'<< ']
    for k, v in self.d.items():
        s.append(b'/%s ' % k)
        s.append(v)
        s.append(b'\n')
    s.append(b'>>\n')

    return b''.join(s)


global_next_id = 1

class Obj:
  next_id = 1
  def __init__(self, d = {}, stream = None):
    global global_next_id

    if stream is not None:
      d[b'Length'] = b'%d' % (len(stream))
    self.d = Dict(d)
    self.stream = stream
    self.id = global_next_id
    global_next_id += 1
    pprint(self.d.d)

  def __bytes__(self):
    s = []
    s.append(bytes(self.d))
    if self.stream is not None:
      s.append(b'stream\n')
      s.append(self.stream)
      #  print("** stream=%s %d %s" % (type(self.stream), len(self.stream), self.stream[:10]), file=sys.stderr)
      s.append(b'\nendstream\n')
    s.append(b'endobj')

    return b''.join(s)

  def ref(self):
      return ref(self.id)


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

  def __bytes__(self):
    a = []
    j = [0]
    offsets = []

    def add(x):
        a.append(x)
        j[0] += len(x) + 1

    add(b'%PDF-1.4')
    for o in self.objs:
      offsets.append(j[0])
      add(b'%d 0 obj' % o.id)
      add(bytes(o))
    xrefstart = j[0]
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


def ref(x):
    return b'%d 0 R' % x


def usage(script, msg):
    if msg:
        sys.stderr.write("%s: %s\n" % (script, msg))
        sys.stderr.write("Usage: %s [file_basename] > out.pdf\n" % script)
    sys.exit(1)


def readFile(filename):
    try:
        return open(filename, 'rb').read()
    except IOError:
        print("error reading file %s" % filename, file=sys.stderr)
        raise


def pprint(msg):
    """Pretty print `msg` to stderr."""
    return
    pprinter.pprint(msg)


if __name__ == '__main__':
    main()
