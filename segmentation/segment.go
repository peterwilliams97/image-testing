//
// Segment images then combine the segments in a PDF file.
//
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"image" // for color.Alpha{a}
	"image/color"
	"image/draw"
	"image/jpeg"
	"image/png"
	"io/ioutil"
	"os"
	"path/filepath"
	"sort"

	"github.com/unidoc/unipdf/v3/common"
	"github.com/unidoc/unipdf/v3/core"
	"github.com/unidoc/unipdf/v3/creator"
)

// Encoding types
type imageEncoding int

const (
	encodeFlate imageEncoding = iota
	encodeDCT
)

var (
	encodingName = map[imageEncoding]string{
		encodeFlate: "png",
		encodeDCT:   "jpg",
	}
	allEncodings = []imageEncoding{
		encodeFlate,
		encodeDCT,
	}
)

// PDF creation modes.
type createMode int

const (
	createSimple createMode = iota
	createBgd
	createCompound
)

var allModes = []createMode{
	createSimple,
	createBgd,
	createCompound,
}

// Default settings
const (
	imageDir    = "images"    // Where image segments are stored.
	fgdEncoding = encodeDCT   // Encoding used for foreground image fragments.
	bgdEncoding = encodeFlate // Encoding used for background image fragments.
	jpegQuality = 25          // Quality setting for DCT images
	dilation    = 2           // Knockouts are reduced by this number of pixexl to hide seams.
)

// More default settings
var (
	knockoutColor  = image.White                                    // knockoutColor is used for drawing knockouts in the background
	highlightColor = image.NewUniform(color.RGBA{B: 0xFF, A: 0xFF}) // for showing knockout locations
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
//   createBgd: Build the PDF from the input images with the rectangles knocked out
//   createCompound: Build the PDF with for each page:
//     background = input image with the rectangles knocked out, encoded in `bgdEncoding`
///    foreground = the rectangles extracted from the input image, encoded in `fgdEncoding`.
// Example JSON instructions file for a images that are 300 dpi A4 whole page scans.
//   {
//     "pdf.output/Volunteer/doc-001.png": [
//         {"X0":   0, "X1": 2481, "Y0":    0, "Y1": 2450} ],
//     "pdf.output/Volunteer/doc-002.png": [
//         {"X0": 356, "X1": 2148, "Y0": 1432, "Y1": 2935},
//         {"X0":  66, "X1": 118,  "Y0":  990, "Y1": 3508} ]
//   }
func makePdf(jsonPath string, mode createMode, enc imageEncoding) error {
	var outPath string
	switch mode {
	case createSimple:
		outPath = changeExtOnly(jsonPath, fmt.Sprintf(".unmasked.%s.pdf", encodingName[enc]))
	case createBgd:
		outPath = changeExtOnly(jsonPath, ".bgd.pdf")
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
		// for _, enc := range allEncodings {
		// 	encPath := changeDirExt(pagePath, fmt.Sprint(".orig.%s", encodingName[enc]))
		// 	if err = saveImage(encPath, img, enc); err != nil {
		// 		panic(err)
		// 	}
		// 	fmt.Printf("saved original to %q\n", encPath)
		// }

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
//
func addImageToPage(c *creator.Creator, pagePath string, rectList []Rect, mode createMode,
	enc imageEncoding) error {
	bgdPath := changeDirExt(pagePath, ".bgd.png")

	common.Log.Info("addImageToPage: pagePath=%q rectList=%v mode=%#v ", pagePath, rectList, mode)

	img, err := loadImage(pagePath)
	if err != nil {
		return err
	}
	bounds := img.Bounds()
	w, h := bounds.Max.X, bounds.Max.Y

	if mode == createSimple {
		return placeImageOnPage(c, pagePath, w, h, enc)
	}

	fgdList := makeForegroundList(img, rectList)
	bgd := makeBackground(img, dilate(rectList, -dilation), mode == createBgd)

	var fgdPathList []string
	for i, fgd := range fgdList {
		fgdPath := makeFgdPath(pagePath, i)
		err = saveImage(fgdPath, fgd, fgdEncoding)
		if err != nil {
			panic(err)
		}
		fmt.Printf("saved foreground to %q\n", fgdPath)
		fgdPathList = append(fgdPathList, fgdPath)
	}

	err = saveImage(bgdPath, bgd, bgdEncoding)
	if err != nil {
		panic(err)
	}
	fmt.Printf("saved background to %q\n", bgdPath)

	if mode == createBgd {
		return placeImageOnPage(c, bgdPath, w, h, enc)
	}

	err = overlayImagesOnPage(c, bgdPath, rectList, fgdPathList, w, h, dilation)
	if err != nil {
		panic(err)
	}
	return nil
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
		panic("Can't happend")
	}
	return
}

// overlay image in `fgdPath` over image in `bgdPath` (currently assumed to be have the same
// dimensions `w` x `h`) and write the resulting single page `width` x `height` PDF to `outPath`.
// is the width of the image in PDF document dimensions (height/width ratio is maintained).
func overlayImagesOnPage(c *creator.Creator, bgdPath string, rectList []Rect, fgdPathList []string,
	w, h, dilation int) error {
	scale, xOfs, yOfs := computeScale(width, height, float64(w), float64(h))
	common.Log.Info("overlayImagesOnPage: scale=%.3f width=%.1f height=%.1f w=%d h=%d",
		scale, width, height, w, h)
	common.Log.Info("               scale * w x h = %.1f x%.1f", scale*float64(w), scale*float64(h))
	// c := creator.New()
	c.NewPage()

	r := Rect{X0: 0, Y0: 0, X1: w, Y1: h}
	enc := makeEncoder(bgdEncoding, w, h)
	if err := addImage(c, bgdPath, enc, r, scale, xOfs, yOfs, 0); err != nil {
		return err
	}
	for i, fgdPath := range fgdPathList {
		r := rectList[i]
		enc := makeEncoder(fgdEncoding, w, h)
		if err := addImage(c, fgdPath, enc, r, scale, xOfs, yOfs, dilation); err != nil {
			return err
		}
	}
	return nil
}

func placeImageOnPage(c *creator.Creator, bgdPath string, w, h int, enc imageEncoding) error {
	scale, xOfs, yOfs := computeScale(width, height, float64(w), float64(h))
	common.Log.Info("placeImageOnPage: scale=%.3f width=%.1f height=%.1f w=%d h=%d",
		scale, width, height, w, h)
	common.Log.Info("                  scale * w x h = %.1f x%.1f", scale*float64(w), scale*float64(h))
	c.NewPage()

	r := Rect{X0: 0, Y0: 0, X1: w, Y1: h}
	encoder := makeEncoder(enc, w, h)
	if err := addImage(c, bgdPath, encoder, r, scale, xOfs, yOfs, 0); err != nil {
		return err
	}
	return nil
}

func makeEncoder(enc imageEncoding, w, h int) core.StreamEncoder {
	switch enc {
	case encodeFlate:
		return core.NewFlateEncoder()
	case encodeDCT:
		dctEnc := core.NewDCTEncoder()
		dctEnc.Width = w
		dctEnc.Height = h
		dctEnc.Quality = jpegQuality
		return dctEnc
	}
	panic(fmt.Errorf("unknown imageEncoding %#v", enc))
}

// addImage adds image in `imagePath` to `c` with encoding and scale given by `encoder` and `scale`.
func addImage(c *creator.Creator, imgPath string, encoder core.StreamEncoder,
	r Rect, scale, xOfs, yOfs float64, dilation int) error {
	common.Log.Info("addImage: imgPath=%q r=%v", imgPath, r)
	img, err := c.NewImageFromFile(imgPath)
	if err != nil {
		return err
	}
	if encoder != nil {
		img.SetEncoder(encoder)
	}
	x, y := float64(r.X0)*scale+xOfs, float64(r.Y0)*scale+yOfs
	w, h := float64(r.X1-r.X0)*scale, float64(r.Y1-r.Y0)*scale // +1? !@#$
	common.Log.Info("addImage: r=%v scale=%.3f xOfs=%.3f yOfs=%.3f", r, scale, xOfs, yOfs)
	common.Log.Info("addImage: xPos=%6.2f yPos=%6.2f width=%6.2f height=%6.2f %q", x, y, w, h, imgPath)
	img.SetPos(x, y)
	img.SetWidth(w)
	img.SetHeight(h)
	return c.Draw(img)
}

// makeForeground returns `img` masked to the rectangles in `rectList`.
func _makeForeground(img image.Image, rectList []Rect) image.Image {
	bounds := img.Bounds()
	w, h := bounds.Max.X, bounds.Max.Y
	r := fromBounds(bounds)
	fmt.Printf("makeForeground: rectList=%v\n", rectList)
	fmt.Printf("bounds=%#v\n", bounds)
	fmt.Printf("r=%#v\n", r)
	fmt.Printf("w=%d h=%d\n", w, h)

	rgba := image.NewRGBA(img.Bounds())
	fillRect(rgba, r, image.Transparent)
	for _, r := range rectList {
		draw.Draw(rgba, r.bounds(), img, r.position(), draw.Src)
		// fillRect(rgba, r, image.White)
	}
	return rgba
}

// makeForegroundList images of returns `img` clipped by the rectangles in `rectList`.
func makeForegroundList(img image.Image, rectList []Rect) []image.Image {
	bounds := img.Bounds()
	w, h := bounds.Max.X, bounds.Max.Y
	r := fromBounds(bounds)
	fmt.Printf("makeForegroundList: rectList=%v\n", rectList)
	fmt.Printf("bounds=%#v\n", bounds)
	fmt.Printf("r=%#v\n", r)
	fmt.Printf("w=%d h=%d\n", w, h)

	fgdList := make([]image.Image, len(rectList))
	for i, r := range rectList {
		rgba := image.NewRGBA(r.zpBounds())
		wind := r.bounds()
		draw.Draw(rgba, r.zpBounds(), img, r.position(), draw.Src)
		fgdList[i] = rgba
		fmt.Printf("%4d: %v=%v -> %v\n", i, r, wind, rgba.Bounds())
	}
	return fgdList
}

// makeForeground returns `img` with the rectangles in `rectList` knocked out.
// If `higlight` is true the knockouts are filled with a highlight color, otherwise a color that
// compresses well. The color that will compress best is the background color of `img` around the
// knockouts.
func makeBackground(img image.Image, rectList []Rect, highlight bool) image.Image {
	bounds := img.Bounds()
	w, h := bounds.Max.X, bounds.Max.Y
	r := fromBounds(bounds)
	fmt.Printf("makeBackground: rectList=%v\n", rectList)
	fmt.Printf("bounds=%#v\n", bounds)
	fmt.Printf("r=%#v\n", r)
	fmt.Printf("w=%d h=%d\n", w, h)

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
	fmt.Printf("dilate: d=%d %v->%v\n", d, rectList, outList)
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

// saveImage saves image `img` to file `filename` with encoding `enc`.
func saveImage(filename string, img image.Image, enc imageEncoding) error {
	out, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer out.Close()

	switch enc {
	case encodeFlate:
		return png.Encode(out, img)
	case encodeDCT:
		return jpeg.Encode(out, img, nil)
	}
	return fmt.Errorf("unsupported encoding %#v", enc)
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

func loadImage(pagePath string) (image.Image, error) {
	imgfile, err := os.Open(pagePath)
	if err != nil {
		return nil, err
	}
	defer imgfile.Close()

	img, _, err := image.Decode(imgfile)
	return img, err
}

// makeUsage updates flag.Usage to include usage message `msg`.
func makeUsage(msg string) {
	usage := flag.Usage
	flag.Usage = func() {
		fmt.Fprintln(os.Stderr, msg)
		usage()
	}
}
