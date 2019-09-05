Image Segmentation
==================

* segment.go  Creates segmented PDFs from image segmenation json files
* entropy.py  Simple entropy based segmentation. Includes test framework and diagnostics
* compress.py Shows compression improvements for tested PDFs


Installation
------------
I used a recent Anaconda python version and the latest Go version on a Mac

entropy.py uses segment.go so you will need to build segment.go

    go build segment.go


Testing
-------
Assuming a PDF test corpus in ~/testdata

Run the tests

    python entropy.py ~/testdata/*.pdf

This will write all the compressed PDF files along with uncompressed versions of the
same PDF files to pdf.output/

Show the compression results

    python compression.py  pdf.output/
