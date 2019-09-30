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
	"image/jpeg"
	"image/png"
	"io/ioutil"
	"os"
	"path/filepath"

	"github.com/unidoc/unipdf/v3/common"
	"github.com/unidoc/unipdf/v3/core"
	"github.com/unidoc/unipdf/v3/creator"
	"github.com/unidoc/unipdf/v3/model"
)

// Encoding types
type imageEncoding int

const (
	encodeFlate imageEncoding = iota
	encodeCCITT
	encodeDCT
	encodeJBIG2
)

var (
	encodingName = map[imageEncoding]string{
		encodeFlate: "png",
		encodeCCITT: "ccitt",
		encodeDCT:   "jpg",
		encodeJBIG2: "jbig2",
	}
	allEncodings = []imageEncoding{
		encodeFlate,
		encodeCCITT,
		encodeDCT,
		encodeJBIG2,
	}
)

// Default settings
const (
	imageDir    = "layered.images"
	jpegQuality = 25 // Quality setting for DCT images
)

type ImageMark struct {
	*core.PdfObjectReference
	*core.PdfObjectDictionary
	// *model.Image
	ImagePath         string  // We don't need imagePath and Image
	Filter            string  // GetFilterName()
	Width, Height     int     // Width and height of image
	X, Y, W, H, Theta float64 // Location and size on page
	ColorComponents   int
	BitsPerComponent  int
	Lossy             bool
	Mask              *core.PdfObjectReference
	MaskOf            *core.PdfObjectReference
	Name              string
}

type PageMark struct {
	W, H   float64
	Rotate int
	Images []ImageMark
}

type DocMark struct {
	Pages []PageMark
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

func (pgMark PageMark) makePage(c *creator.Creator) error {
	// for _, imgMark := range pgMark.Images {
	page := model.NewPdfPage()
	mediaBox := model.PdfRectangle{Urx: pgMark.W, Ury: pgMark.H}
	page.MediaBox = &mediaBox
	rotate := int64(pgMark.Rotate)
	page.Rotate = &rotate
	common.Log.Info("page=%+v %d", *page.MediaBox, *page.Rotate)
	c.AddPage(page)

	for _, imgMark := range pgMark.Images {
		if err := imgMark.addImageToPage(c); err != nil {
			return err
		}
	}
	return nil
}

// addImageToPage adds the input image in the file `pagePath` to the PDF file represented by `c`.
// Foreground subimages are created from the rectangles `rectList` applied to this image and a
// a background image is created by blanking the rectangles on the image.
func (imgMark ImageMark) addImageToPage(c *creator.Creator) error {
	common.Log.Info("addImageToPage: imgMark=%+v", imgMark)

	img, err := loadGoImage(imgMark.ImagePath)
	if err != nil {
		return err
	}

	// Draw the background image.
	return imgMark.addImage(c, img)
}

func makeEncoder(encodingName string, w, h int) core.StreamEncoder {
	switch encodingName {
	case "JBIG2Decode":
		return core.NewFlateEncoder()
	default:
		encoder := core.NewDCTEncoder()
		encoder.Width = w
		encoder.Height = h
		encoder.Quality = jpegQuality
		return encoder

		// case encodeCCITT:
		// 	encoder := core.NewCCITTFaxEncoder()
		// 	encoder.Columns = w
		// 	encoder.Rows = h
		// 	return encoder
		// case encodeFlate:
		// 	return core.NewFlateEncoder()
		// case encodeDCT:
		// 	encoder := core.NewDCTEncoder()
		// 	encoder.Width = w
		// 	encoder.Height = h
		// 	encoder.Quality = jpegQuality
		// 	return encoder
	}
	panic(fmt.Errorf("unknown imageEncoding %#v", encodingName))
}

// addImage adds image in `imagePath` to `c` with encoding and scale given by `encoder` and `scale`.
func (imgMark ImageMark) addImage(c *creator.Creator, goImg image.Image) error {
	encoder := makeEncoder(imgMark.Filter, imgMark.Width, imgMark.Height)
	// img.SetEncoder(encoder)
	// if enc == encodeCCITT || enc == encodeJBIG2 {
	// 	img.SetBitsPerComponent(1)
	// }
	img, err := c.NewImageFromGoImageMask(goImg, nil)
	if err != nil {
		return err
	}
	if imgMark.BitsPerComponent == 1 {
		img.SetBitsPerComponent(1)
		ccittEncoder := core.NewCCITTFaxEncoder()
		ccittEncoder.Columns = int(img.Width())
		img.SetEncoder(ccittEncoder)
	} else {
		img.SetEncoder(encoder)
	}

	img.SetPos(imgMark.X, imgMark.Y)
	img.SetWidth(imgMark.W)
	img.SetHeight(imgMark.H)
	common.Log.Info("encoder=%v", encoder)
	return c.Draw(img)
}

// saveGoImage saves Go image `img` to file `filename` with imageEncoding `enc`.
func saveGoImage(filename string, img image.Image, enc imageEncoding) error {
	out, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer out.Close()

	switch enc {
	case encodeFlate, encodeCCITT, encodeJBIG2:
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

func saveDocMark(filename string, doc DocMark) error {
	b, err := json.MarshalIndent(doc, "", "\t")
	if err != nil {
		return err
	}
	err = ioutil.WriteFile(filename, b, 0644)
	return err
}

func loadDocMark(filename string) (DocMark, error) {
	b, err := ioutil.ReadFile(filename)
	if err != nil {
		return DocMark{}, err
	}
	var doc DocMark
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
