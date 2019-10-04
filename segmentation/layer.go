//
// Segment images then combines the segments in a PDF file.
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
	"io/ioutil"
	"os"
	"path/filepath"

	"github.com/unidoc/unipdf/v3/common"
	"github.com/unidoc/unipdf/v3/core"
	"github.com/unidoc/unipdf/v3/creator"
	"github.com/unidoc/unipdf/v3/model"
)

// Default settings
const (
	imageDir    = "layered.images"
	jpegQuality = 25 // Quality setting for DCT images
)

// Basic idea is that we need the following categories of image
//  - 1 bit or contone
//  - grayscale or color
//  - lossless or lossy

// For each of these choices we create an encoding.
// Today we have
//  - CCITT for 1 bit
//  - Flate for lossless contone
//  - DCT for lossy contone  (DCT quality is a program setting)
// In the future we will use
//  - JBIC2 for 1 bit
//  - Flate for lossless contone
//  - Maybe in the distrant future JPEG2000 for lossy contone\
type CoreImage struct {
	ImagePath string // Input image. We don't change resolution.
	// Rendering instructions
	ColorComponents  int
	BitsPerComponent int
	Lossy            bool
}
type ImageSpec struct {
	CoreImage                   // Main image
	MaskImage         CoreImage // Optional image mask
	X, Y, W, H, Theta float64   // Location and size on page in points
}

type PageSpec struct {
	W, H   float64     // Width and height of page in points
	Rotate int         // Page rotation flag
	Images []ImageSpec // Images to be placed on page
}

type DocSpec struct {
	Pages []PageSpec
}

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
	err := makePdf(flag.Arg(0))
	if err != nil {
		panic(err)
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
func makePdf(jsonPath string) error {

	common.Log.Info("makePdf: %q", jsonPath)

	doc, err := loadDocMark(jsonPath)
	if err != nil {
		return err
	}
	common.Log.Info("doc=%+v", doc)
	common.Log.Info("makePdf: %d pages", len(doc.Pages))

	c := creator.New()
	for _, page := range doc.Pages {
		err := page.makePage(c)
		if err != nil {
			return err
		}
	}
	outPath := changeExtOnly(jsonPath, ".pdf")

	err = c.WriteToFile(outPath)
	if err != nil {
		return err
	}
	common.Log.Info("makePdf: %d pages\n\t   %q\n\t-> %q", len(doc.Pages), jsonPath, outPath)

	return nil
}

func (pgMark PageSpec) makePage(c *creator.Creator) error {
	page := model.NewPdfPage()
	mediaBox := model.PdfRectangle{Urx: pgMark.W, Ury: pgMark.H}
	page.MediaBox = &mediaBox
	rotate := int64(pgMark.Rotate)
	page.Rotate = &rotate
	common.Log.Info("page=%+v %d", *page.MediaBox, *page.Rotate)
	c.AddPage(page)

	for _, spec := range pgMark.Images {
		if err := spec.addImageToPage(c); err != nil {
			return err
		}
	}
	return nil
}

// addImageToPage adds the input image in the file `pagePath` to the PDF file represented by `c`.
// The main image is in `spec.ImagePath`. The optional mask image in in `spec.MaskImage.ImagePath`.
func (spec ImageSpec) addImageToPage(c *creator.Creator) error {
	common.Log.Info("addImageToPage: spec=%+v", spec)

	goImg, err := loadGoImage(spec.ImagePath)
	if err != nil {
		return err
	}

	var goMaskImg image.Image
	if spec.MaskImage.ImagePath != "" {
		goMaskImg, err = loadGoImage(spec.ImagePath)
		if err != nil {
			panic(err)
			return err
		}
	}

	common.Log.Info("addImageToPage: img=%t maskImg=%t %q",
		goImg != nil, goMaskImg != nil, spec.MaskImage.ImagePath)

	img, err := c.NewImageWithMaskFromGoImages(goImg, goMaskImg)
	if err != nil {
		return err
	}
	img.SetBitsPerComponent(int64(spec.BitsPerComponent))

	encoder := makeEncoder(spec.BitsPerComponent, spec.Lossy, goImg)
	img.SetEncoder(encoder)
	common.Log.Info("encoder=%v", encoder)

	if spec.MaskImage.ImagePath != "" {

		img.SetMaskBitsPerComponent(int64(spec.MaskImage.BitsPerComponent))
		maskEncoder := makeEncoder(spec.MaskImage.BitsPerComponent, spec.MaskImage.Lossy, goMaskImg)
		img.SetMaskEncoder(maskEncoder)
		common.Log.Info("maskEncoder=%v", maskEncoder)
	}

	img.SetPos(spec.X, spec.Y)
	img.SetWidth(spec.W)
	img.SetHeight(spec.H)

	return c.Draw(img)
}

func makeEncoder(bpc int, lossy bool, goImg image.Image) core.StreamEncoder {
	b := goImg.Bounds()
	w := b.Max.X - b.Min.X
	h := b.Max.Y - b.Min.Y

	if bpc == 1 {
		ccittEncoder := core.NewCCITTFaxEncoder()
		ccittEncoder.Columns = w
		return ccittEncoder
	}
	if !lossy {
		return core.NewFlateEncoder()
	}
	encoder := core.NewDCTEncoder()
	encoder.Width = w
	encoder.Height = h
	encoder.Quality = jpegQuality
	return encoder
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

func saveDocSpec(filename string, doc DocSpec) error {
	b, err := json.MarshalIndent(doc, "", "\t")
	if err != nil {
		return err
	}
	err = ioutil.WriteFile(filename, b, 0644)
	return err
}

func loadDocMark(filename string) (DocSpec, error) {
	b, err := ioutil.ReadFile(filename)
	if err != nil {
		return DocSpec{}, err
	}
	var doc DocSpec
	err = json.Unmarshal(b, &doc)
	common.Log.Info("doc=%+v err=%v", doc, err)
	return doc, err
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

// makeUsage updates flag.Usage to include usage message `msg`.
func makeUsage(msg string) {
	usage := flag.Usage
	flag.Usage = func() {
		fmt.Fprintln(os.Stderr, msg)
		usage()
	}
}
