//
// Segment images then combine the segments in a PDF file.
// Another program will create a JSON file with segmentation instructions. This program reads the
// JSON file, segments the images referenced in the JSON file, encodes rectangle enclosed segements
// as DCT, encoded the rest of the image as Flate then combines the images in a PDF file.
//
// Example JSON instructions file for a images that are 300 dpi A4 whole page scans.
//   {
//     "pdf.output/Volunteer/doc-001.png": [
//         {"X0":   0,  "Y0":    0, "Y1": 2450} ],
//     "pdf.output/Volunteer/doc-002.png": [
//         {"X0": 356, "X1": 2148, "Y0": 1432, "Y1": 2935},
//         {"X0":  66, "X1": 118,  "Y0":  990, "Y1": 3508} ]
//   }
//
// The example JSON files references 300 dpi RGB raster files doc-001.png and doc-002.png. It
// requests that the area x,y: X0 <= x < X1 and Y0 <= y < Y1 for all the rectangles for that page
// be DCT encoded and the remainder of the image be Flate encoded.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/jpeg"
	"image/png"
	"io/ioutil"
	"os"
	"path/filepath"
	"sort"

	"github.com/ultimate-guitar/go-imagequant"
	"github.com/unidoc/unipdf/v3/common"
	"github.com/unidoc/unipdf/v3/core"
	"github.com/unidoc/unipdf/v3/creator"
)

// Encoding types
type imageEncoding int

const (
	encodeFlate imageEncoding = iota
	encodeCCITT
	encodeDCT
)

var (
	encodingName = map[imageEncoding]string{
		encodeFlate: "png",
		encodeCCITT: "ccitt",
		encodeDCT:   "jpg",
	}
	allEncodings = []imageEncoding{
		encodeFlate,
		encodeCCITT,
		encodeDCT,
	}
)

// PDF creation modes.
type createMode int

const (
	createSimple createMode = iota
	createBgd
	createFgd
	createCompound
)

var (
	modeName = map[createMode]string{
		createSimple:   "createSimple",
		createBgd:      "createBgd",
		createFgd:      "createFgd",
		createCompound: "createCompound",
	}
	allModes = []createMode{
		createSimple,
		createBgd,
		createFgd,
		createCompound,
	}
)

// Default settings
const (
	imageDir    = "images"    // Where image segments are stored.
	fgdEncoding = encodeDCT   // Encoding used for foreground image fragments.
	bgdEncoding = encodeFlate // Encoding used for background image fragments.
	binEncoding = encodeCCITT // Encoding used for bilevel image fragments.
	jpegQuality = 25          // Quality setting for DCT images
	dilation    = 2           // Knockouts are reduced by this number of pixexl to hide seams.
)

// More default settings
var (
	knockoutColor  = image.NewUniform(color.RGBA{R: 0xFF, G: 0xFF, B: 0xFF, A: 0xFF}) // image.White                                    // knockoutColor is used for drawing knockouts in the background
	highlightColor = image.NewUniform(color.RGBA{B: 0xFF, A: 0xFF})                   // for showing knockout locations
)

const usage = "go run segment.go <json file>"

func main() {
	common.SetLogger(common.NewConsoleLogger(common.LogLevelInfo))
	makeUsage(usage)
	flag.Parse()
	if len(flag.Args()) == 0 {
		flag.Usage()
		os.Exit(1)
	}
	if _, err := os.Stat(imageDir); os.IsNotExist(err) {
		os.Mkdir(imageDir, 0777)
	}
	for _, inPath := range flag.Args() {
		for _, mode := range allModes {
			if err := makePdf(inPath, mode, encodeFlate); err != nil {
				panic(err)
			}
			if mode == createSimple {
				if err := makePdf(inPath, mode, encodeDCT); err != nil {
					panic(err)
				}
			}
		}
	}
}

// makePdf makes a PDF file from the instructions in JSON file `jsonPath`.
// The JSON file is a dict of pageName: []Rect where the rectangles are masking coordinate for the
// input image in the image file pageName.
// Creation `mode` can be one of:
//   createSimple: Build the PDF one input image per page (ignoring rectangles) encoded in `enc`.
//   createCompound: Build the PDF with for each page:
//     background = input image with the rectangles knocked out, encoded in `bgdEncoding`
//     foreground = the rectangles extracted from the input image, encoded in `fgdEncoding`
//   createBgd: Build the PDF from only the background images in createCompound.
//   createFgd: Build the PDF from only the foreground images in createCompound.
func makePdf(jsonPath string, mode createMode, enc imageEncoding) error {
	var outPath string
	switch mode {
	case createSimple:
		outPath = changeExtOnly(jsonPath, fmt.Sprintf(".unmasked.%s.pdf", encodingName[enc]))
	case createBgd:
		outPath = changeExtOnly(jsonPath, ".bgd.pdf")
	case createFgd:
		outPath = changeExtOnly(jsonPath, ".fgd.pdf")
	case createCompound:
		outPath = changeExtOnly(jsonPath, ".masked.pdf")
	default:
		panic(fmt.Errorf("unsupported creation mode %#v", mode))
	}

	pageRectList, err := loadPageRectList(jsonPath)
	if err != nil {
		return err
	}
	common.Log.Info("makePdf: %d pages\n\t   %q\n\t-> %q", len(pageRectList), jsonPath, outPath)

	c := creator.New()
	for _, pagePath := range pageKeys(pageRectList) {
		rectList := pageRectList[pagePath]
		err := addImageToPage(c, pagePath, rectList, mode, enc)
		if err != nil {
			return err
		}
	}
	err = c.WriteToFile(outPath)
	if err != nil {
		return err
	}
	common.Log.Info("makePdf: %d pages\n\t   %q\n\t-> %q", len(pageRectList), jsonPath, outPath)

	return nil
}

// addImageToPage adds the input image in the file `pagePath` to the PDF file represented by `c`.
// Foreground subimages are created from the rectangles `rectList` applied to this image and a
// a background image is created by blanking the rectangls on the image.
func addImageToPage(c *creator.Creator, pagePath string, rectList []Rect, mode createMode,
	enc imageEncoding) error {
	bgdPath := changeDirExt(pagePath, ".bgd.png")
	common.Log.Info("addImageToPage: pagePath=%q rectList=%v mode=%#v ", pagePath, rectList, mode)

	img, err := loadGoImage(pagePath)
	if err != nil {
		return err
	}
	bounds := img.Bounds()
	w := bounds.Max.X - bounds.Min.X
	h := bounds.Max.Y - bounds.Min.Y

	if mode == createSimple {
		return placeImageOnPage(c, pagePath, w, h, enc)
	}

	fgdList := makeForegroundList(img, rectList)
	bgd := makeBackground(img, dilate(rectList, -dilation), mode == createBgd)
	err = saveGoImage(bgdPath, bgd, bgdEncoding)
	if err != nil {
		panic(err)
	}

	makePrintHistogram("background", bgd)
	isBilevel := histogramBilevel(bgd)
	isBilevel = false
	// // if isBilevel {
	// // 	panic("Bilevel")
	// // }
	// if !isBilevel {
	// 	if histogramQuanitizable(bgd) {
	// 		crushedPath := bgdPath + ".crushed.png"
	// 		err = crushFile(bgdPath, crushedPath, 3, png.BestCompression)
	// 		if err != nil {
	// 			panic(err)
	// 		}
	// 		// TODO: Figure out how to work with paletted PNGs !@#$
	// 		// bgdPath = crushedPath
	// 		// bgd, err := loadGoImage(bgdPath)
	// 		// if err != nil {
	// 		// 	panic(err)
	// 		// }
	// 		// makePrintHistogram("crushed", bgd)
	// 	}
	// }

	var fgdPathList []string
	for i, fgd := range fgdList {
		fgdPath := makeFgdPath(pagePath, i)
		err = saveGoImage(fgdPath, fgd, fgdEncoding)
		if err != nil {
			return err
		}
		fgdPathList = append(fgdPathList, fgdPath)
	}

	doBgd := mode != createFgd
	doFgd := mode != createBgd
	common.Log.Info("mode=%v=%#q", mode, modeName[mode])
	return overlayImagesOnPage(c, bgdPath, rectList, fgdPathList, w, h, doBgd, doFgd, isBilevel)
}

const (
	// // A4
	// widthMM  = 210.0
	// heightMM = 297.0
	// widthPt  = (widthMM / 25.4) * 72.0
	// heightPt = (heightMM / 25.4) * 72.0

	// US letter
	widthInch  = 8.5
	heightInch = 11.0
	widthPt    = widthInch * 72.0
	heightPt   = heightInch * 72.0

	// xPos     = widthPt / 10.0
	// yPos     = heightPt / 10.0
	xPos   = 0.0
	yPos   = 0.0
	width  = widthPt - 2*xPos
	height = heightPt - 2*yPos
)

// computeScale returns the scale for w x h -> width x height
func computeScale(width, height, w, h float64) (scale, xOfs, yOfs float64) {
	xScale := width / w
	yScale := height / h
	if xScale < yScale {
		scale = xScale
		yOfs = 0.5 * (height - scale*h)
	} else {
		scale = yScale
		xOfs = 0.5 * (width - scale*w)
	}
	if xOfs < 0 || yOfs < 0 {
		panic("can't happen")
	}
	return
}

// overlayImagesOnPage overlay image in `fgdPath` over image in `bgdPath` (currently assumed to be have the same
// dimensions `w` x `h`) and write the resulting single page `width` x `height` PDF to `outPath`.
// is the width of the image in PDF document dimensions (height/width ratio is maintained).
func overlayImagesOnPage(c *creator.Creator, bgdPath string, rectList []Rect, fgdPathList []string,
	w, h int, doBgd, doFgd, isBilevel bool) error {
	scale, xOfs, yOfs := computeScale(width, height, float64(w), float64(h))
	common.Log.Info("### overlayImagesOnPage: doBgd=%t doFgd=%t isBilevel=%t", doBgd, doFgd, isBilevel)
	common.Log.Info("   scale=%.3f width=%.1f height=%.1f w=%d h=%d",
		scale, width, height, w, h)
	common.Log.Info("    scale * w x h = %.1f x%.1f", scale*float64(w), scale*float64(h))

	c.NewPage()
	if doBgd {
		// Draw the background image.
		r := Rect{X0: 0, Y0: 0, X1: w, Y1: h}
		enc := bgdEncoding
		if isBilevel {
			enc = binEncoding
		}
		if err := addImage(c, bgdPath, enc, r, scale, xOfs, yOfs); err != nil {
			return err
		}
	}
	if doFgd {
		// Draw the foreground images.
		for i, fgdPath := range fgdPathList {
			r := rectList[i]
			if err := addImage(c, fgdPath, fgdEncoding, r, scale, xOfs, yOfs); err != nil {
				return err
			}
		}
	}
	return nil
}

func placeImageOnPage(c *creator.Creator, bgdPath string, w, h int, enc imageEncoding) error {
	scale, xOfs, yOfs := computeScale(width, height, float64(w), float64(h))
	common.Log.Info("placeImageOnPage: scale=%.3f width=%.1f height=%.1f w=%d h=%d",
		scale, width, height, w, h)
	common.Log.Info("                  scale * w x h = %.1f x%.1f", scale*float64(w), scale*float64(h))

	// return overlayImagesOnPage(c, bgdPath, nil, nil, w, h, true, false)
	c.NewPage()
	// Draw the background image.
	r := Rect{X0: 0, Y0: 0, X1: w, Y1: h}
	if err := addImage(c, bgdPath, enc, r, scale, xOfs, yOfs); err != nil {
		return err
	}
	return nil
}

func makeEncoder(enc imageEncoding, w, h int) core.StreamEncoder {
	switch enc {
	case encodeCCITT:
		encoder := core.NewCCITTFaxEncoder()
		encoder.Columns = w
		encoder.Rows = h
		return encoder
	case encodeFlate:
		return core.NewFlateEncoder()
	case encodeDCT:
		encoder := core.NewDCTEncoder()
		encoder.Width = w
		encoder.Height = h
		encoder.Quality = jpegQuality
		return encoder
	}
	panic(fmt.Errorf("unknown imageEncoding %#v", enc))
}

// addImage adds image in `imagePath` to `c` with encoding and scale given by `encoder` and `scale`.
func addImage(c *creator.Creator, imgPath string, enc imageEncoding,
	r Rect, scale, xOfs, yOfs float64) error {
	common.Log.Info("addImage: imgPath=%q r=%v", imgPath, r)

	var goW, goH int
	{
		goImg, err := loadGoImage(imgPath)
		if err != nil {
			return err
		}
		bounds := goImg.Bounds()
		goW, goH = bounds.Max.X, bounds.Max.Y

		if enc == encodeCCITT {
			grayPath := changeExtOnly(imgPath, ".gray.png")
			grayImg := makeGrayImage(goImg)
			err := saveGoImage(grayPath, grayImg, enc)
			if err != nil {
				return err
			}
			imgPath = grayPath

		}
	}

	img, err := c.NewImageFromFile(imgPath)
	if err != nil {
		return err
	}

	encoder := makeEncoder(enc, goW, goH)
	img.SetEncoder(encoder)
	if enc == encodeCCITT {
		img.SetBitsPerComponent(1)
	}

	x, y := float64(r.X0)*scale+xOfs, float64(r.Y0)*scale+yOfs
	w, h := float64(r.X1-r.X0)*scale, float64(r.Y1-r.Y0)*scale // +1? !@#$
	common.Log.Info("addImage: r=%v scale=%.3f xOfs=%.3f yOfs=%.3f", r, scale, xOfs, yOfs)
	common.Log.Info("addImage: xPos=%6.2f yPos=%6.2f width=%6.2f height=%6.2f %q", x, y, w, h, imgPath)
	img.SetPos(x, y)
	img.SetWidth(w)
	img.SetHeight(h)
	common.Log.Info("encoder=%v", encoder)
	return c.Draw(img)
}

// makeForegroundList images of returns `img` clipped by the rectangles in `rectList`.
func makeForegroundList(img image.Image, rectList []Rect) []image.Image {
	bounds := img.Bounds()
	w := bounds.Max.X - bounds.Min.X
	h := bounds.Max.Y - bounds.Min.Y
	r := fromBounds(bounds)
	common.Log.Info("makeForegroundList: rectList=%v", rectList)
	common.Log.Info("bounds=%#v", bounds)
	common.Log.Info("r=%#v w=%d h=%d", r, w, h)

	fgdList := make([]image.Image, len(rectList))
	for i, r := range rectList {
		rgba := image.NewRGBA(r.zpBounds())
		wind := r.bounds()
		draw.Draw(rgba, r.zpBounds(), img, r.position(), draw.Src)
		fgdList[i] = rgba
		common.Log.Info("%4d: %v=%v -> %v", i, r, wind, rgba.Bounds())
		// panic("$")
	}
	return fgdList
}

// makeBackground returns `img` with the rectangles in `rectList` knocked out.
// If `higlight` is true the knockouts are filled with a highlight color, otherwise a color that
// compresses well. The color that will compress best is the background color of `img` around the
// knockouts.
func makeBackground(img image.Image, rectList []Rect, highlight bool) image.Image {
	bounds := img.Bounds()
	w := bounds.Max.X - bounds.Min.X
	h := bounds.Max.Y - bounds.Min.Y
	r := fromBounds(bounds)
	common.Log.Info("makeBackground: rectList=%v", rectList)
	common.Log.Info("bounds=%#v", bounds)
	common.Log.Info("r=%#v w=%d h=%d", r, w, h)

	fillColor := knockoutColor
	if highlight {
		fillColor = highlightColor
	}

	rgba := image.NewRGBA(img.Bounds())
	draw.Draw(rgba, r.bounds(), img, r.position(), draw.Src)
	for _, r := range rectList {
		fillRect(rgba, r, fillColor)
	}
	return rgba
}

func makePrintHistogram(title string, img image.Image) {
	n, histo := histogram(img)
	printHistogram(title, n, histo)
}

func histogramQuanitizable(img image.Image) bool {
	n, histo := histogram(img)
	maxColors := 255
	threshold := 0.99
	return quanitizable(n, histo, maxColors, threshold)
}

// histogramBilevel returns true if `img` is an approximately bilevel image. Our current definition
// of "approximateley bilevel" is that at least 99% of the pixels are in 2 colors or less.
func histogramBilevel(img image.Image) bool {
	n, histo := histogram(img)
	maxColors := 2
	threshold := 0.99
	bilevel := quanitizable(n, histo, maxColors, threshold)
	common.Log.Info("histogramBilevel: bilevel=%t img=%v", bilevel, img.Bounds())
	return bilevel
}

// histogram returns the number of pixels and map of {rbga: number} of the number of pixels with
// each rbga value.
func histogram(imgIn image.Image) (int, map[uint32]int) {
	img := imgIn.(*image.RGBA)
	bounds := img.Bounds()
	w := bounds.Max.X - bounds.Min.X
	h := bounds.Max.Y - bounds.Min.Y

	histo := map[uint32]int{}
	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			p := img.RGBAAt(x, y)
			r, g, b, a := p.RGBA()
			u := r + g<<8 + b<<16 + a<<24
			histo[u]++
		}
	}
	return w * h, histo
}

// quantizable returns true if the `maxColors` most common pixel colors cover `n` x `threshold`
// pixels in `histo`.
// If qualitizable returns true then a palette of `maxColors` can be used to approximate the image
// n and histo were computed from
func quanitizable(n int, histo map[uint32]int, maxColors int, threshold float64) bool {
	var keys []uint32
	for u := range histo {
		keys = append(keys, u)
	}
	sort.Slice(keys, func(i, j int) bool {
		ki, kj := keys[i], keys[j]
		hi, hj := histo[ki], histo[kj]
		if hi != hj {
			return hi >= hj
		}
		return ki < kj
	})

	m := len(histo)
	if m > maxColors {
		m = maxColors
	}
	cumulative := 0
	for _, u := range keys[:m] {
		cumulative += histo[u]
	}
	fraction := float64(cumulative) / float64(n)
	possible := fraction >= threshold

	common.Log.Info("quanitizable: %d colors %d pixels maxColors=%d => threshold=%.1f%%\n"+
		"\tfraction=%.1f%% possible=%t",
		len(histo), n, maxColors, 100.0*threshold, 100.0*fraction, possible)
	return possible
}

func printHistogram(title string, n int, histo map[uint32]int) {
	var keys []uint32
	for u := range histo {
		keys = append(keys, u)
	}
	sort.Slice(keys, func(i, j int) bool {
		ki, kj := keys[i], keys[j]
		hi, hj := histo[ki], histo[kj]
		if hi != hj {
			return hi >= hj
		}
		return ki < kj
	})

	common.Log.Info("printHistogram: %q %d colors %d pixels.\n\tMost common colors:",
		title, len(histo), n)

	thresholdCount := map[float64]int{}
	cumulative := 0
	color256 := -1
	tk := 0
	for i, u := range keys {
		r := u & 0xff
		g := (u >> 8) & 0xff
		b := (u >> 16) & 0xff
		a := (u >> 24) & 0xff
		cnt := histo[u]
		cumulative += cnt
		if i < maxColors {
			fmt.Printf("%4d: 0x%08X (%3d %3d %3d | %3d) %7d %5.1f%% %g%%\n",
				i, u, r, g, b, a, cnt, 100.0*float64(cnt)/float64(n), 100.0*float64(cumulative)/float64(n))
		}
		for tk < len(thresholdSteps) && float64(cumulative)/float64(n) >= thresholdSteps[tk] {
			thresholdCount[thresholdSteps[tk]] = i + 1
			tk++
		}
		if i == 255 {
			color256 = cumulative
		}
	}
	if color256 < 0 {
		color256 = cumulative
	}

	common.Log.Info("Histogram: %d thresholds %d pixels %d colors", tk, n, len(histo))
	for k := 0; k < tk; k++ {
		threshold := thresholdSteps[k]
		cnt := thresholdCount[threshold]
		fmt.Printf("%4d: %6.2f%% pixels covered by %8d = %5.1f%% colors\n", k, 100.0*threshold, cnt,
			100.0*float64(cnt)/float64(len(histo)))
	}
	common.Log.Info("256 colors cover %d = %5.1f%% pixels", color256,
		100.0*float64(color256)/float64(n))
}

const maxColors = 10

var thresholdSteps = []float64{
	0.25,
	0.50,
	0.75,
	0.90,
	0.95,
	0.99,
	0.995,
	0.999,
	0.9995,
	0.9999,
}

func crushFile(srcPath, dstPath string, speed int, compression png.CompressionLevel) error {
	err := crushFile_(srcPath, dstPath, speed, compression)
	if err != nil {
		return err
	}
	srcMB := fileSizeMB(srcPath)
	dstMB := fileSizeMB(dstPath)
	common.Log.Info("crushFile: %q->%q", srcPath, dstPath)
	common.Log.Info("crushFile: %.3f MB -> %.3f MB %.1f%% ", srcMB, dstMB, 100.0*dstMB/srcMB)
	return nil
}

func crushFile_(srcPath, dstPath string, speed int, compression png.CompressionLevel) error {
	common.Log.Info("crushFile: %q->%q", srcPath, dstPath)

	sourceFh, err := os.OpenFile(srcPath, os.O_RDONLY, 0444)
	if err != nil {
		return fmt.Errorf("os.OpenFile: %s", err.Error())
	}
	defer sourceFh.Close()

	image, err := ioutil.ReadAll(sourceFh)
	if err != nil {
		return fmt.Errorf("ioutil.ReadAll: %s", err.Error())
	}

	optiImage, err := imagequant.Crush(image, speed, compression)
	if err != nil {
		return fmt.Errorf("imagequant.Crush: %s", err.Error())
	}

	destFh, err := os.OpenFile(dstPath, os.O_WRONLY|os.O_CREATE, 0644)
	if err != nil {
		return fmt.Errorf("os.OpenFile: %s", err.Error())
	}
	defer destFh.Close()

	destFh.Write(optiImage)
	return nil
}

func fileSizeMB(filename string) float64 {
	fi, err := os.Stat(filename)
	if err != nil {
		common.Log.Error("Stat failed. filename=%q err=%v", filename, err)
		return -1.0
	}
	return float64(fi.Size()) / 1024.0 / 1024.0
}

// Rect is a rectangle that is deserialized from JSON files.
type Rect struct {
	X0, Y0, X1, Y1 int
}

func fromBounds(b image.Rectangle) Rect {
	return Rect{
		X0: b.Min.X,
		Y0: b.Min.Y,
		X1: b.Max.X,
		Y1: b.Max.Y,
	}
}

func (r Rect) bounds() image.Rectangle {
	return image.Rect(r.X0, r.Y0, r.X1, r.Y1)
}

func (r Rect) position() image.Point {
	return image.Point{r.X0, r.Y0}
}

func (r Rect) zpBounds() image.Rectangle {
	return image.Rect(0, 0, r.X1-r.X0, r.Y1-r.Y0)
}

// dilate returns the Rects in `rectList` dilated by `d` on all 4 sides
func dilate(rectList []Rect, d int) []Rect {
	outList := make([]Rect, len(rectList))
	for i, r := range rectList {
		if r.X1-r.X0 < 2*d || r.Y1-r.Y0 < 2*d {
			common.Log.Error("r=%+v dilation=%d", r, d)
			panic("not allowed")
		}
		r.X0 -= d
		r.X1 += d
		r.Y0 -= d
		r.Y1 += d
		outList[i] = r
	}
	return outList
}

func fillRect(img *image.RGBA, r Rect, col *image.Uniform) {
	for y := r.Y0; y < r.Y1; y++ {
		for x := r.X0; x < r.X1; x++ {
			img.Set(x, y, col)
		}
	}
}

func saveRectList(filename string, rectList []Rect) error {
	b, err := json.MarshalIndent(rectList, "", "\t")
	if err != nil {
		return err
	}
	err = ioutil.WriteFile(filename, b, 0644)
	return err
}

func loadPageRectList(filename string) (map[string][]Rect, error) {
	b, err := ioutil.ReadFile(filename)
	if err != nil {
		return nil, err
	}
	var pageRectList map[string][]Rect
	err = json.Unmarshal(b, &pageRectList)
	return pageRectList, err
}

func pageKeys(pageRectList map[string][]Rect) []string {
	keys := make([]string, 0, len(pageRectList))
	for page := range pageRectList {
		keys = append(keys, page)
	}
	sort.Strings(keys)
	return keys
}

func drawPixels(img *image.Alpha, px, py, pw, ph uint, fill bool) {
	var x, y uint
	for y = 0; y < ph; y++ {
		for x = 0; x < pw; x++ {
			if fill {
				img.Set(int(px*pw+x), int(py*ph+y), image.White)
			} else {
				img.Set(int(px*pw+x), int(py*ph+y), image.Transparent)
			}
		}
	}
}

func makeFgdPath(outPath string, i int) string {
	return changeDirExt(outPath, fmt.Sprintf("-%03d.fgd.png", i))
}

func changeDirExt(filename, newExt string) string {
	base := filepath.Base(filename)
	filename = filepath.Join(imageDir, base)
	return changeExtOnly(filename, newExt)
}

func changeExtOnly(filename, newExt string) string {
	ext := filepath.Ext(filename)
	return filename[:len(filename)-len(ext)] + newExt
}

// saveGoImage saves Go image `img` to file `filename` with imageEncoding `enc`.
func saveGoImage(filename string, img image.Image, enc imageEncoding) error {
	out, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer out.Close()

	switch enc {
	case encodeFlate, encodeCCITT:
		return png.Encode(out, img)
	case encodeDCT:
		return jpeg.Encode(out, img, nil)
	}
	return fmt.Errorf("unsupported encoding %#v", enc)
}

// loadGoImage loads the image in file `pagePath` and returns it as a Go image.
func loadGoImage(pagePath string) (image.Image, error) {
	imgfile, err := os.Open(pagePath)
	if err != nil {
		return nil, err
	}
	defer imgfile.Close()

	img, _, err := image.Decode(imgfile)
	return img, err
}

func makeGrayImage(img image.Image) image.Image {
	common.Log.Info("makeGrayImage: %v", img.Bounds())
	x0, x1 := img.Bounds().Min.X, img.Bounds().Max.X
	y0, y1 := img.Bounds().Min.Y, img.Bounds().Max.Y

	grayImg := image.NewGray(img.Bounds())

	for y := y0; y < y1; y++ {
		for x := x0; x < x1; x++ {
			grayImg.Set(x, y, img.At(x, y))
			g := grayImg.GrayAt(x, y).Y
			if g < 127 {
				g = 0
			} else {
				g = 255
			}
			grayImg.SetGray(x, y, color.Gray{g})
		}
	}

	// for y := img.Bounds().Min.Y; y < img.Bounds().Max.Y; y++ {
	// 	for x := img.Bounds().Min.X; x < img.Bounds().Max.X; x++ {
	// 		g := img.GrayAt(x,y)
	// 		if g < 127 {
	// 			g = 0
	// 		} else {
	// 			g = 255
	// 		}
	// 		grayImg.SetGray(x, y, g)
	// 	}
	// }

	return grayImg
}

// makeUsage updates flag.Usage to include usage message `msg`.
func makeUsage(msg string) {
	usage := flag.Usage
	flag.Usage = func() {
		fmt.Fprintln(os.Stderr, msg)
		usage()
	}
}
