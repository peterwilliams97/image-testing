TODO - Segment
==============
* Create PDF with page size that matches rasters


TODO - Entropy
==================
* Copy `image` directory to `pdf.ouput/<name>.entropy`
* Handle synthetic images inside natural images. e.g. studies_2012_2.pdf adobe-sign.pdf page 1
* Expand rectangle to enclose whole natural image. e.g. 01-intro.pdf
* Split polygon into multiple rectangles. e.g. pmitc.pdf page 1
* Find whole image e.g. adobe-sign.pdf page 2 Or maybe not. Over segmenting gives good results here.
* Not detecting image in EY Trader Surveillance report.pdf page 1
* Two natural image regions have been merged and cover text. e.g. good_guts.pdf page 1
* Overlapping rectangles. lee.json lee.fgd.pdf page 1  FIXED!
* Too much PNG? EY Trader Surveillance report.pdf or AIPopularPress1985.pdf which is text on a textured background. Can we re-quanitize the png? Can we use a high quality jpeg? Could we use jpeg2000?
* Natural images are getting missed e.g. real_estate.pdf page 1, gx.pdf
* BUG: Missing edges of high entropy area in HistoryOfRome.pdf page 1
* /Users/peter/testdata/misc/THE BEHAVIORAL AND BRAIN SCIENCES (1984) 7, 173-221.pdf should compress with JBIG2
* PaperCutMF-Top-10-Reasons.masked.pdf won't open in Adobe Reader
* CCCITT indexed colorspaces https://blog.idrsolutions.com/2013/03/understanding-the-pdf-file-format-filter-and-decodeparms-objects-for-a-pdf-image/

IDEAS
-----
### nlmeans before entropy search
### Compute 2 entropy thesholds
  Compute high entropy rectangles at high threshold
  Expand those rectangles until entropy drops below low threshold
  This would handle the cases where we detect a noisy part of a natural region.

### Grayscale detection

### Requanitize (Letopica?) before detecting entropy
    This may be give a more meaningful entropy value.
    Count color levels in Flate. ***
         Reduce to palette if <= 256. Reduce to grays

### jbig2
http://www.leptonica.org/jbig2.html

Results  6 September 2019
-------------------------
     0: 0.05 (0.02)  0.54 MB [Fri Sep  6 16:19:14 2019] pdf.output/green_jobs.masked.pdf
     1: 0.06 (0.03)  0.18 MB [Fri Sep  6 16:22:02 2019] pdf.output/matrix.masked.pdf
     2: 0.07 (0.04)  0.90 MB [Fri Sep  6 16:07:40 2019] pdf.output/Volunteer.masked.pdf
     3: 0.08 (0.03)  0.53 MB [Fri Sep  6 16:23:14 2019] pdf.output/HistoryOfRome.masked.pdf
     4: 0.09 (0.06)  0.91 MB [Fri Sep  6 17:11:11 2019] pdf.output/good_guts.masked.pdf
     5: 0.10 (0.08)  0.60 MB [Fri Sep  6 17:06:04 2019] pdf.output/NewsletterIssue1-1.masked.pdf
     6: 0.10 (0.07)  0.62 MB [Fri Sep  6 16:12:21 2019] pdf.output/william-shakespeare.masked.pdf
     7: 0.11 (0.08)  0.51 MB [Fri Sep  6 16:12:45 2019] pdf.output/golub-gene.masked.pdf
     8: 0.11 (0.08)  0.55 MB [Fri Sep  6 16:09:11 2019] pdf.output/shakespeare.masked.pdf
     9: 0.11 (0.07)  0.50 MB [Fri Sep  6 16:16:29 2019] pdf.output/ap5.masked.pdf
    10: 0.12 (0.05)  0.50 MB [Fri Sep  6 16:58:24 2019] pdf.output/global.masked.pdf
    11: 0.13 (0.10)  1.32 MB [Fri Sep  6 17:03:17 2019] pdf.output/adobe-sign.masked.pdf
    12: 0.17 (0.13)  0.18 MB [Fri Sep  6 17:01:27 2019] pdf.output/01-intro.masked.pdf
    13: 0.21 (0.05)  0.79 MB [Fri Sep  6 17:04:01 2019] pdf.output/studies_2012_2.masked.pdf
    14: 0.23 (0.17)  0.28 MB [Fri Sep  6 16:59:57 2019] pdf.output/NeAF-BPG-vol1.masked.pdf
    15: 0.24 (0.16)  0.60 MB [Fri Sep  6 16:20:07 2019] pdf.output/course-signal-denoising.masked.pdf
    16: 0.24 (0.15)  0.29 MB [Fri Sep  6 17:08:49 2019] pdf.output/DocuSign-User-Guide_2015.masked.pdf
    17: 0.27 (0.16)  1.21 MB [Fri Sep  6 17:07:29 2019] pdf.output/South_West_Healthcare_2014-15_tw80smF0.masked.pdf
    18: 0.33 (0.27)  0.51 MB [Fri Sep  6 16:53:34 2019] pdf.output/face-matching-services-fact-sheet.masked.pdf
    19: 0.36 (0.32)  0.34 MB [Fri Sep  6 16:16:52 2019] pdf.output/pmitc.masked.pdf
    20: 0.38 (0.36)  0.36 MB [Fri Sep  6 16:22:29 2019] pdf.output/devops.masked.pdf
    21: 0.42 (0.24)  1.58 MB [Fri Sep  6 16:17:47 2019] pdf.output/lee.masked.pdf
    22: 0.42 (0.38)  0.57 MB [Fri Sep  6 16:58:51 2019] pdf.output/PDFA_eSeminar_Slides_updated.masked.pdf
    23: 0.43 (0.41)  3.81 MB [Fri Sep  6 16:13:36 2019] pdf.output/hobbes.masked.pdf
    24: 0.43 (0.40)  0.45 MB [Fri Sep  6 16:05:48 2019] pdf.output/product.masked.pdf
    25: 0.45 (0.41)  0.52 MB [Fri Sep  6 17:02:27 2019] pdf.output/cv_dl_resource_guide.masked.pdf
    26: 0.46 (0.32)  0.46 MB [Fri Sep  6 16:08:31 2019] pdf.output/LifeShakespeare.masked.pdf
    27: 0.50 (0.48)  0.48 MB [Fri Sep  6 16:06:03 2019] pdf.output/pettifor.masked.pdf
    28: 0.50 (0.39)  0.77 MB [Fri Sep  6 16:06:53 2019] pdf.output/hospitaller.masked.pdf
    29: 0.51 (0.46)  0.57 MB [Fri Sep  6 16:18:19 2019] pdf.output/radon.masked.pdf
    30: 0.51 (0.48)  2.72 MB [Fri Sep  6 17:09:35 2019] pdf.output/CRCSI-Global-Outlook-Report-2018.masked.pdf
    31: 0.53 (0.35)  0.51 MB [Fri Sep  6 17:08:09 2019] pdf.output/PDF_A_101_An_Intro_Final.masked.pdf
    32: 0.54 (0.28)  0.77 MB [Fri Sep  6 16:21:15 2019] pdf.output/systembiologie.masked.pdf
    33: 0.64 (0.54)  0.74 MB [Fri Sep  6 16:56:19 2019] pdf.output/comradeship_august_2011.masked.pdf
    34: 0.65 (0.53)  0.43 MB [Fri Sep  6 16:05:06 2019] pdf.output/HannibalAlps.masked.pdf
    35: 0.66 (0.44)  0.52 MB [Fri Sep  6 16:59:24 2019] pdf.output/How_to_Insert_a_Digital_Signature_PDF_Doc.masked.pdf
    36: 0.69 (0.66)  1.55 MB [Fri Sep  6 16:57:45 2019] pdf.output/Legal Services Industry Brief.masked.pdf
    37: 0.83 (0.81)  0.62 MB [Fri Sep  6 16:06:31 2019] pdf.output/CTimes.masked.pdf
    38: 0.90 (0.88)  2.21 MB [Fri Sep  6 16:10:15 2019] pdf.output/peterkm224.masked.pdf
    39: 0.95 (0.93)  2.41 MB [Fri Sep  6 17:05:16 2019] pdf.output/gazette.masked.pdf
    40: 0.98 (0.96)  0.55 MB [Fri Sep  6 16:54:01 2019] pdf.output/sample01.masked.pdf
    41: 1.00 (1.00) 16.30 MB [Fri Sep  6 16:14:46 2019] pdf.output/AIPopularPress1985.masked.pdf
    42: 1.00 (1.00)  6.78 MB [Fri Sep  6 17:00:37 2019] pdf.output/EY Trader Surveillance report.masked.pdf
    43: 1.00 (1.00)  6.52 MB [Fri Sep  6 17:10:21 2019] pdf.output/real_estate.masked.pdf
    44: 1.00 (1.00)  3.08 MB [Fri Sep  6 16:15:25 2019] pdf.output/gx.masked.pdf
    45: 1.00 (1.00)  0.66 MB [Fri Sep  6 16:14:08 2019] pdf.output/manual.masked.pdf
    46: 1.00 (1.00)  0.66 MB [Fri Sep  6 16:21:42 2019] pdf.output/star.masked.pdf
    47: 1.00 (1.00)  0.56 MB [Fri Sep  6 16:07:58 2019] pdf.output/plato.masked.pdf
    48: 1.00 (1.00)  0.53 MB [Fri Sep  6 16:54:23 2019] pdf.output/digitalid.masked.pdf
    49: 1.00 (1.00)  0.53 MB [Fri Sep  6 16:20:34 2019] pdf.output/wtf.masked.pdf
    50: 1.00 (1.00)  0.48 MB [Fri Sep  6 16:57:09 2019] pdf.output/ironman.masked.pdf
    51: 1.00 (1.00)  0.47 MB [Fri Sep  6 16:11:41 2019] pdf.output/Range Filters.masked.pdf
    52: 1.00 (1.00)  0.42 MB [Fri Sep  6 16:56:43 2019] pdf.output/ElectronicVaultAdvantage.masked.pdf
    53: 1.00 (1.00)  0.41 MB [Fri Sep  6 16:04:38 2019] pdf.output/battle.masked.pdf
    54: 1.00 (1.00)  0.41 MB [Fri Sep  6 17:01:04 2019] pdf.output/report02-3.masked.pdf
    55: 1.00 (1.00)  0.39 MB [Fri Sep  6 16:15:48 2019] pdf.output/statistical_region_merging.masked.pdf
    56: 1.00 (1.00)  0.38 MB [Fri Sep  6 16:04:01 2019] pdf.output/Vogl-Paper.masked.pdf
    57: 1.00 (1.00)  0.38 MB [Fri Sep  6 17:04:30 2019] pdf.output/nvsr66_06_tables.masked.pdf
    58: 1.00 (1.00)  0.38 MB [Fri Sep  6 16:55:21 2019] pdf.output/LFEA.masked.pdf
    59: 1.00 (1.00)  0.34 MB [Fri Sep  6 16:52:23 2019] pdf.output/Reader-rights.masked.pdf
    60: 1.00 (1.00)  0.30 MB [Fri Sep  6 16:53:06 2019] pdf.output/Legal.masked.pdf
    61: 1.00 (1.00)  0.27 MB [Fri Sep  6 16:52:44 2019] pdf.output/RSA.masked.pdf
    62: 1.00 (1.00)  0.25 MB [Fri Sep  6 17:01:56 2019] pdf.output/DORA-State of DevOps.masked.pdf
    63: 1.00 (1.00)  0.25 MB [Fri Sep  6 16:10:42 2019] pdf.output/Leviathon.masked.pdf
    64: 1.00 (1.00)  0.22 MB [Fri Sep  6 16:11:12 2019] pdf.output/Expertise_buendeln_Studienvergleich.masked.pdf
    65: 1.00 (1.00)  0.22 MB [Fri Sep  6 16:05:27 2019] pdf.output/address.masked.pdf
    66: 1.00 (1.00)  0.21 MB [Fri Sep  6 16:51:50 2019] pdf.output/Acrobat_SignatureCreationQuickKeyAll.masked.pdf
    67: 1.00 (1.00)  0.18 MB [Fri Sep  6 16:04:13 2019] pdf.output/ShakespeareResume.masked.pdf
    68: 1.00 (1.00)  0.16 MB [Fri Sep  6 16:09:40 2019] pdf.output/eso.masked.pdf
    69: 1.00 (1.00)  0.15 MB [Fri Sep  6 16:54:56 2019] pdf.output/ml-elecsig-e.masked.pdf
    70: 1.00 (1.00)  0.13 MB [Fri Sep  6 16:52:00 2019] pdf.output/certificate.masked.pdf
    71: 1.00 (1.00)  0.13 MB [Fri Sep  6 16:55:32 2019] pdf.output/SampleSignedPDFDocument.masked.pdf
    72: 1.00 (1.00)  0.12 MB [Fri Sep  6 16:55:43 2019] pdf.output/palace.masked.pdf
    73: 1.00 (1.00)  0.00 MB [Fri Sep  6 16:51:38 2019] pdf.output/legal-certificate.masked.pdf
    ================================================================================
    Compressed = 41 =  55.4%
          Same = 33 =  44.6%
      Expanded =  0 =   0.0%
