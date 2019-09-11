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

# JBIG2 Encoder
# https://github.com/agl/jbig2enc

import sys
import re
import struct
import glob
import os
from pprint import PrettyPrinter

pprinter = PrettyPrinter(stream=sys.stderr)


# This is a very simple script to make a PDF file out of the output of a
# multipage symbol compression.
# Run ./jbig2 -s -p <other options> image1.jpeg image1.jpeg ...
# python pdf.py output > out.pdf

dpi = 72

class Ref:
  def __init__(self, x):
    self.x = x
  def __bytes__(self):
    return b"%d 0 R" % self.x

class Dict:
  def __init__(self, values = {}):
    self.d = {}
    for k, v in values.items():
        if isinstance(k, str):
            k = k.encode('ascii')
        if isinstance(v, str):
            v = v.encode('ascii')
        self.d[k] = v
        assert not isinstance(k, str), (k, v)
        assert not isinstance(v, str), (k, v)
    for k, v in self.d.items():
        assert not isinstance(k, str), (k, v)
        assert not isinstance(v, str), (k, v)

    # self.d = {k.encode('ascii'): v.encode('ascii') for k, v in values.items()}
    # self.d.update(values)

  def __bytes__(self):
    s = [b'<< ']
    for k, v in self.d.items():
        assert not isinstance(k, str), (k, v)
        assert not isinstance(v, str), (k, v)
        s.append(b'/%s ' % k)
        s.append(v)
        s.append(b'\n')
    s.append(b'>>\n')

    return b''.join(s)

  def __str__(self):
      assert False

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
    s.append(b'endobj\n')

    # print("** %s %d %s" % (type(s), len(s), [type(k) for k in s]), file=sys.stderr)

    for i, k in enumerate(s):
        assert not isinstance(k, str), (i, k)

    return b''.join(s)

    def __str__(self):
        assert False

class Doc:
  def __init__(self):
    self.objs = []
    self.pages = []

  def add_object(self, o):
    self.objs.append(o)
    return o

  def add_page(self, o):
    self.pages.append(o)
    return self.add_object(o)

  def __bytes__(self):
    a = []
    j = [0]
    offsets = []

    def add(x):
        assert not isinstance(x, str), x
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
    a.append(b'<< /Size %d\n/Root 1 0 R >>' % (len(offsets) + 1))
    a.append(b'startxref')
    a.append(bytes(xrefstart))
    a.append(b'%%EOF')

    return b'\n'.join(a)

def ref(x):
    return b'%d 0 R' % x

def main(symboltable='symboltable', pagefiles=glob.glob('page-*')):
    print("** symboltable=%s" % symboltable, file=sys.stderr)
    print("** pagefiles= %d: %s" % (len(pagefiles), pagefiles), file=sys.stderr)
    doc = Doc()
    doc.add_object(Obj({'Type' : '/Catalog', 'Outlines' : ref(2), 'Pages' : ref(3)}))
    doc.add_object(Obj({'Type' : '/Outlines', 'Count': '0'}))
    pages = Obj({'Type' : '/Pages'})
    doc.add_object(pages)
    symd = doc.add_object(Obj({}, open(symboltable, 'rb').read()))
    page_objs = []

    pagefiles.sort()

    for i, p in enumerate(pagefiles):
        print("** page %d: %s" % (i, p), file=sys.stderr)
        try:
            contents = open(p, mode='rb').read()
        except IOError:
            sys.stderr.write("error reading page file %s\n"% p)
            continue
        (width, height, xres, yres) = struct.unpack('>IIII', contents[11:27])

        # print('** (width, height, xres, yres)', [width, height, xres, yres], file=sys.stderr)

        if xres == 0:
            xres = dpi
        if yres == 0:
            yres = dpi

        xobj = Obj({'Type': '/XObject', 'Subtype': '/Image', 'Width':
                str(width), 'Height': str(height), 'ColorSpace': '/DeviceGray',
                'BitsPerComponent': '1', 'Filter': '/JBIG2Decode', 'DecodeParms':
                ' << /JBIG2Globals %d 0 R >>' % symd.id}, contents)
        contents = Obj({}, b'q %f 0 0 %f 0 0 cm /Im1 Do Q' % (float(width * 72) / xres, float(height * 72) / yres))
        resources = Obj({'ProcSet': '[/PDF /ImageB]',
                'XObject': '<< /Im1 %d 0 R >>' % xobj.id})
        page = Obj({'Type': '/Page', 'Parent': '3 0 R',
                'MediaBox': '[ 0 0 %f %f ]' % (float(width * 72) / xres, float(height * 72) / yres),
                'Contents': ref(contents.id),
                'Resources': ref(resources.id)})
        [doc.add_object(x) for x in [xobj, contents, resources, page]]
        page_objs.append(page)

        pages.d.d[b'Count'] = b'%d' % len(page_objs)
        pages.d.d[b'Kids'] = b'[' + b' '.join([ref(x.id) for x in page_objs]) + b']'

    sys.stdout.buffer.write(bytes(doc))


def usage(script, msg):
    if msg:
        sys.stderr.write("%s: %s\n"% (script, msg))
        sys.stderr.write("Usage: %s [file_basename] > out.pdf\n"% script)
    sys.exit(1)


def myMain():
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

    if not os.path.exists(sym):
        usage(sys.argv[0], "symbol table %s not found!"% sym)
    elif len(pages) == 0:
        usage(sys.argv[0], "no pages found!")

    main(sym, pages)


def pprint(msg):
    """Pretty print `msg` to stderr."""
    return
    pprinter.pprint(msg)


if __name__ == '__main__':
    myMain()
