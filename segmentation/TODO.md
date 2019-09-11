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

Results 11 September 2019
-------------------------
     Compressed =  119 = 76.8% = 1064.88 MB
          Same =   35 =  22.6% =   94.22 MB
      Expanded =    1 =   0.6% =    0.62 MB
         Total =  155 = 100.0% = 1159.71 MB
     0: 1.26  0.95 (0.22)  0.62 MB periodictable.masked.pdf
     1: 0.99  2.61 (0.98) 27.27 MB gazette.masked.pdf
     2: 0.99  2.47 (0.99) 21.28 MB gazette72.masked.pdf
     3: 1.00 19.29 (1.00) 16.30 MB AIPopularPress1985.masked.pdf
     4: 0.91  1.53 (0.90) 10.59 MB lzwandflatef.masked.pdf
     5: 0.91  7.57 (0.91) 10.54 MB Goedel.masked.pdf
     6: 1.00  6.48 (1.00) 10.48 MB l9_concurrentprocesses2013.masked.pdf
     7: 0.94  1.10 (0.94)  9.74 MB EY Trader Surveillance report.masked.pdf
     8: 0.90  1.51 (0.87)  9.37 MB Channar-Overland-Conveyor-1991.masked.pdf
     9: 0.94  1.75 (0.93)  9.23 MB TypeScript.masked.pdf
    10: 1.00  0.92 (1.00)  7.77 MB grav_const.masked.pdf
    11: 0.96  1.48 (0.89)  7.53 MB Crop Tree Management.masked.pdf
    12: 0.97  0.68 (0.96)  6.38 MB DocumentCaptureMarket.masked.pdf
    13: 1.00  0.96 (1.00)  5.87 MB gx.masked.pdf
    14: 1.00  0.79 (1.00)  5.64 MB Amity.masked.pdf
    15: 0.92  1.10 (0.91)  5.64 MB WeeklyBulletin.masked.pdf
    16: 1.00  0.74 (1.00)  4.81 MB RoadTrauma.masked.pdf
    17: 1.00  0.92 (1.00)  4.45 MB Mulheir.masked.pdf
    18: 1.00  0.37 (1.00)  4.45 MB Leviathon.masked.pdf
    19: 1.00  0.40 (1.00)  4.31 MB knuth-plass-breaking.masked.pdf
    20: 0.92  0.58 (0.91)  3.89 MB manual.masked.pdf
    21: 1.00  0.36 (1.00)  3.54 MB nvsr66_06_tables.masked.pdf
    22: 0.91  0.60 (0.85)  3.49 MB go-scp.masked.pdf
    23: 1.00  1.43 (0.99)  3.34 MB USRisk.masked.pdf
    24: 1.00  0.42 (0.98)  3.14 MB CryogenicGases.masked.pdf
    25: 1.00  0.42 (1.00)  2.99 MB Range Filters.masked.pdf
    26: 1.00  0.56 (1.00)  2.86 MB ScienceViews.masked.pdf
    27: 1.00  0.37 (1.00)  2.74 MB report02-3.masked.pdf
    28: 1.00  0.39 (1.00)  2.33 MB LFEA.masked.pdf
    29: 1.00  0.37 (1.00)  2.23 MB ml-elecsig-e.masked.pdf
    30: 1.00  0.30 (1.00)  2.14 MB ironman.masked.pdf
    31: 1.00  0.66 (1.00)  2.12 MB PSG11_CUG_EN_03.masked.pdf
    32: 0.91  0.60 (0.89)  1.90 MB ElectronicVaultAdvantage.masked.pdf
    33: 1.00  0.37 (1.00)  1.13 MB Vogl-Paper.masked.pdf
    34: 1.00  1.98 (1.00)  1.12 MB a_im_diag_exact.masked.pdf
    35: 1.00  0.42 (1.00)  1.11 MB plato.masked.pdf
    36: 1.00  4.92 (1.00)  1.05 MB scan_alan_2016-03-30-10-38-15.masked.pdf
    37: 1.00  1.04 (1.00)  0.96 MB Geelong-Bus-Network.masked.pdf
    38: 0.97  0.49 (0.94)  0.73 MB jbig2recompression.masked.pdf
    39: 1.00  0.94 (1.00)  0.71 MB Box.masked.pdf
    40: 0.98  0.57 (0.96)  0.60 MB sample01.masked.pdf
    41: 1.00  0.82 (1.00)  0.53 MB digitalid.masked.pdf
    42: 1.00  0.50 (1.00)  0.45 MB Legal.masked.pdf
    43: 1.00  0.42 (1.00)  0.41 MB battle.masked.pdf
    44: 1.00  0.40 (1.00)  0.37 MB RSA.masked.pdf
    45: 1.00  0.52 (1.00)  0.34 MB Reader-rights.masked.pdf
    46: 1.00  0.34 (1.00)  0.22 MB address.masked.pdf
    47: 1.00  0.42 (1.00)  0.21 MB Acrobat_SignatureCreationQuickKeyAll.masked.pdf
    48: 1.00  0.39 (1.00)  0.18 MB ShakespeareResume.masked.pdf
    49: 1.00  0.36 (1.00)  0.13 MB certificate.masked.pdf
    50: 1.00  0.60 (1.00)  0.13 MB SampleSignedPDFDocument.masked.pdf
    51: 1.00  0.50 (1.00)  0.12 MB palace.masked.pdf
    52: 1.00  0.50 (1.00)  0.00 MB legal-certificate.masked.pdf
    53: 0.58  1.09 (0.56) 80.02 MB JoannaBaillie.masked.pdf
    54: 0.51  8.35 (0.49) 43.47 MB electric_planes.masked.pdf
    55: 0.52  6.41 (0.46) 42.56 MB Trump.masked.pdf
    56: 0.53  9.09 (0.50) 42.03 MB MasterPlan.masked.pdf
    57: 0.85  3.69 (0.84) 33.54 MB real_estate.masked.pdf
    58: 0.73  3.06 (0.71) 24.58 MB espionage.masked.pdf
    59: 0.87  2.72 (0.86) 19.14 MB Executive-Summary.masked.pdf
    60: 0.67  2.41 (0.57) 15.67 MB research_books_L5.masked.pdf
    61: 0.70  3.27 (0.61) 15.13 MB Buffalo.masked.pdf
    62: 0.82  4.07 (0.77) 14.32 MB Brooklyn.masked.pdf
    63: 0.52  2.75 (0.50) 13.96 MB atomic_theory.masked.pdf
    64: 0.53  1.78 (0.41) 13.22 MB studies_2012_2.masked.pdf
    65: 0.71  1.09 (0.68) 12.60 MB Biomechanics_of_predator-prey_arms_race_in_lion_ze.masked.pdf
    66: 0.86  1.43 (0.78) 11.31 MB RLS_NDR2017_ReportLR.masked.pdf
    67: 0.86  4.03 (0.86) 11.18 MB ISTE_2016_quick_reference_guide.masked.pdf
    68: 0.77  1.43 (0.76) 11.04 MB Australian_Government_Information_Security_Manual.masked.pdf
    69: 0.67  1.27 (0.65) 10.81 MB CervicalScreening.masked.pdf
    70: 0.83  1.10 (0.82) 10.49 MB snow.masked.pdf
    71: 0.86  5.38 (0.85) 10.45 MB tu-dresden-success-story.masked.pdf
    72: 0.78 11.95 (0.76)  9.74 MB maths_solutions.masked.pdf
    73: 0.63  0.87 (0.61)  9.16 MB NASA.masked.pdf
    74: 0.74  0.99 (0.74)  8.21 MB tir2018_en.masked.pdf
    75: 0.59  0.56 (0.46)  8.21 MB ARL.masked.pdf
    76: 0.89  2.12 (0.88)  7.95 MB Help-Center-eBook-11-21.masked.pdf
    77: 0.55  6.52 (0.52)  7.19 MB ImaginesIIIflyer.masked.pdf
    78: 0.87  0.50 (0.81)  6.90 MB Kernerman.masked.pdf
    79: 0.83  0.85 (0.81)  6.09 MB Expertise_buendeln_Studienvergleich.masked.pdf
    80: 0.87  1.23 (0.83)  5.71 MB cfg-parsing.masked.pdf
    81: 0.88  0.65 (0.88)  5.58 MB gocrypto.masked.pdf
    82: 0.90  0.68 (0.87)  5.49 MB QuigginReport.masked.pdf
    83: 0.79  0.58 (0.68)  5.37 MB systembiologie.masked.pdf
    84: 0.77  1.88 (0.76)  5.36 MB PrintDeploy.masked.pdf
    85: 0.66  0.77 (0.63)  5.19 MB CRCSI-Global-Outlook-Report-2018.masked.pdf
    86: 0.56  0.53 (0.54)  5.06 MB ap5.masked.pdf
    87: 0.84  0.68 (0.79)  4.84 MB Glushko.masked.pdf
    88: 0.79  0.53 (0.76)  4.50 MB DeepEyes.masked.pdf
    89: 0.66  1.97 (0.64)  4.41 MB Top_Core_Exercises.masked.pdf
    90: 0.79  0.42 (0.73)  4.00 MB DocuSign-User-Guide_2015.masked.pdf
    91: 0.69  0.48 (0.66)  3.94 MB eso.masked.pdf
    92: 0.78  2.73 (0.72)  3.87 MB MorrisonS_CTZ45P.masked.pdf
    93: 0.84  0.98 (0.83)  3.79 MB Legal Services Industry Brief.masked.pdf
    94: 0.70  1.42 (0.62)  3.71 MB decd-term-calendar-2018.masked.pdf
    95: 0.88  0.51 (0.78)  3.62 MB Chapter_6_Pythagoras_Theorem_plus.masked.pdf
    96: 0.70  0.53 (0.62)  3.46 MB DORA-State of DevOps.masked.pdf
    97: 0.88  0.70 (0.84)  3.42 MB PDF_A_101_An_Intro_Final.masked.pdf
    98: 0.69  2.66 (0.67)  3.24 MB PHYS3060-QM4-Handout.masked.pdf
    99: 0.72  0.68 (0.69)  3.05 MB star.masked.pdf
   100: 0.76  0.38 (0.74)  2.92 MB NeAF-BPG-vol1.masked.pdf
   101: 0.68  0.53 (0.58)  2.92 MB comradeship_august_2011.masked.pdf
   102: 0.56  0.75 (0.48)  2.88 MB LifeShakespeare.masked.pdf
   103: 0.54  0.61 (0.50)  2.87 MB cv_dl_resource_guide.masked.pdf
   104: 0.71  1.22 (0.69)  2.74 MB pmitc.masked.pdf
   105: 0.71  0.74 (0.66)  2.34 MB twitter.masked.pdf
   106: 0.90  4.18 (0.88)  2.21 MB peterkm224.masked.pdf
   107: 0.74  1.22 (0.72)  1.68 MB product.masked.pdf
   108: 0.62  0.53 (0.50)  0.97 MB HannibalAlps.masked.pdf
   109: 0.74  0.49 (0.67)  0.82 MB CTimes.masked.pdf
   110: 0.50  1.21 (0.39)  0.77 MB hospitaller.masked.pdf
   111: 0.86  0.58 (0.71)  0.65 MB PaperCutMF-Top-10-Reasons.masked.pdf
   112: 0.50  1.06 (0.48)  0.48 MB pettifor.masked.pdf
   113: 0.44  1.35 (0.21) 37.02 MB transactor.masked.pdf
   114: 0.39  2.55 (0.33) 28.80 MB cgs.masked.pdf
   115: 0.07  1.81 (0.03) 19.64 MB Fibonacci.masked.pdf
   116: 0.39  1.84 (0.34) 19.30 MB geography.masked.pdf
   117: 0.48  2.41 (0.45) 19.26 MB iae_slides.masked.pdf
   118: 0.50  3.49 (0.48) 18.24 MB reykjavik.masked.pdf
   119: 0.33  0.71 (0.24) 14.59 MB CERNCourier.masked.pdf
   120: 0.50  1.16 (0.31) 13.12 MB lee.masked.pdf
   121: 0.39  1.29 (0.35)  9.56 MB bliq.masked.pdf
   122: 0.41  1.39 (0.11)  8.95 MB DoublyGifted.masked.pdf
   123: 0.18  1.36 (0.11)  8.84 MB course-signal-denoising.masked.pdf
   124: 0.47  0.90 (0.43)  8.33 MB PW15-Advance-lr.masked.pdf
   125: 0.21  0.70 (0.18)  7.85 MB good_guts.masked.pdf
   126: 0.40  0.77 (0.26)  7.00 MB South_West_Healthcare_2014-15_tw80smF0.masked.pdf
   127: 0.36  2.20 (0.33)  6.93 MB devops.masked.pdf
   128: 0.09  0.77 (0.06)  6.43 MB NewsletterIssue1-1.masked.pdf
   129: 0.29  2.20 (0.27)  6.36 MB MuskFan.masked.pdf
   130: 0.10  0.56 (0.07)  4.89 MB green_jobs.masked.pdf
   131: 0.36  0.81 (0.35)  4.84 MB golub-gene.masked.pdf
   132: 0.38  0.52 (0.34)  4.83 MB ASL_fMRI.masked.pdf
   133: 0.50  1.86 (0.47)  4.58 MB nbn.masked.pdf
   134: 0.30  1.03 (0.21)  4.33 MB tokyo_guide_map.masked.pdf
   135: 0.17  1.16 (0.14)  4.14 MB william-shakespeare.masked.pdf
   136: 0.44  2.85 (0.43)  4.05 MB hobbes.masked.pdf
   137: 0.25  0.52 (0.22)  3.78 MB adobe-sign.masked.pdf
   138: 0.34  0.53 (0.29)  3.72 MB global.masked.pdf
   139: 0.26  1.98 (0.23)  3.64 MB BSA.masked.pdf
   140: 0.45  0.67 (0.39)  3.64 MB statistical_region_merging.masked.pdf
   141: 0.26  0.57 (0.22)  3.57 MB image_retriveval.masked.pdf
   142: 0.42  0.52 (0.31)  3.55 MB Lecture_8.masked.pdf
   143: 0.19  0.64 (0.16)  3.51 MB ICML-2018.masked.pdf
   144: 0.34  0.42 (0.30)  3.17 MB HistoryOfRome.masked.pdf
   145: 0.28  0.55 (0.21)  3.10 MB wtf.masked.pdf
   146: 0.20  0.66 (0.16)  2.64 MB shakespeare.masked.pdf
   147: 0.45  0.62 (0.36)  2.39 MB PDFA_eSeminar_Slides_updated.masked.pdf
   148: 0.35  0.62 (0.30)  2.33 MB radon.masked.pdf
   149: 0.37  0.74 (0.32)  2.13 MB HansRosling.masked.pdf
   150: 0.41  0.51 (0.37)  1.67 MB 01-intro.masked.pdf
   151: 0.36  0.39 (0.34)  1.63 MB matrix.masked.pdf
   152: 0.40  0.73 (0.21)  1.49 MB How_to_Insert_a_Digital_Signature_PDF_Doc.masked.pdf
   153: 0.07  0.93 (0.04)  0.90 MB Volunteer.masked.pdf
   154: 0.40  0.44 (0.35)  0.69 MB face-matching-services-fact-sheet.masked.pdf
