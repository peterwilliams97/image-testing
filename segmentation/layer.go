// We build layered images using PDF image masks.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"image"
	"image/color"
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

const usage = "go run layer.go <json file>"

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
	err := makeDoc(flag.Arg(0))
	if err != nil {
		panic(err)
	}
}

// The basic idea is that we need the following categories of images.
//  - 1 bit or contone
//  - grayscale or color
//  - lossless or lossy
// This is our CoreImags. The ImageSpec is a PDF image which has a location, size and optional masking
// image.

// CoreImage is our basic image specfication. ImageSpec is built from this.
// For each of these choices we create an encoding.
// Today we have (see makeEncoder)
//  - CCITT for 1 bit
//  - Flate for lossless contone
//  - DCT for lossy contone  (DCT quality is a program setting)
// In the future we will use
//  - JBIG2 for 1 bit
//  - Flate for lossless contone
//  - Maybe in the distant future JPEG2000 for lossy contone\
type CoreImage struct {
	ImagePath string // Input image. We don't change resolution.
	// Rendering instructions
	ColorComponents  int
	BitsPerComponent int
	Lossy            bool
}

// ImageSpec specifies how an image is rendered on a PDF page. It has an optional image mask and
// the size and location of the image on the page.
type ImageSpec struct {
	CoreImage                   // Main image
	MaskImage         CoreImage // Optional image mask
	X, Y, W, H, Theta float64   // Location and size on page in points
}

// PageSpec specifies a PDF page contain zero or more images.
type PageSpec struct {
	W, H   float64     // Width and height of page in points
	Rotate int         // Page rotation flag
	Images []ImageSpec // Images to be placed on page
}

// DocSpec describes a PDF document containing images
type DocSpec struct {
	Pages []PageSpec
}

// makeDoc makes a PDF file from the instructions in JSON file `jsonPath`.
// The JSON file is of a DocSpec.
func makeDoc(jsonPath string) error {
	common.Log.Info("makeDoc: %q", jsonPath)

	doc, err := loadDocMark(jsonPath)
	if err != nil {
		return err
	}
	common.Log.Info("doc=%+v", doc)
	common.Log.Info("makeDoc: %d pages", len(doc.Pages))

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
	common.Log.Info("makeDoc: %d pages\n\t   %q\n\t-> %q", len(doc.Pages), jsonPath, outPath)
	return nil
}

// makePage makes a PDF file from the instructions in `pageSpec`.
// The JSON file is of a DocSpec.
func (pageSpec PageSpec) makePage(c *creator.Creator) error {
	page := model.NewPdfPage()
	mediaBox := model.PdfRectangle{Urx: pageSpec.W, Ury: pageSpec.H}
	page.MediaBox = &mediaBox
	rotate := int64(pageSpec.Rotate)
	page.Rotate = &rotate
	common.Log.Info("page=%+v %d", *page.MediaBox, *page.Rotate)
	c.AddPage(page)

	for _, spec := range pageSpec.Images {
		if err := spec.addImageToPage(c); err != nil {
			return err
		}
	}
	return nil
}

// addImageToPage adds the input image in `spc` to the PDF file represented by `c`.
// The main image is in `spec.ImagePath`. The optional mask image in in `spec.MaskImage.ImagePath`.
func (spec ImageSpec) addImageToPage(c *creator.Creator) error {
	common.Log.Info("addImageToPage: spec=%+v", spec)

	var goMaskImg image.Image
	if spec.MaskImage.ImagePath != "" {
		if spec.MaskImage.ImagePath == spec.ImagePath {
			panic(spec.MaskImage.ImagePath)
		}
		var err error
		goMaskImg, err = loadGoImage(spec.MaskImage.ImagePath, spec.MaskImage.ColorComponents)
		if err != nil {
			panic(err)
			return err
		}
		showGoImage("goMaskImg", goMaskImg)
	}

	goImg, err := loadGoImage(spec.ImagePath, spec.ColorComponents)
	if err != nil {
		return err
	}
	showGoImage("goImg", goImg)

	common.Log.Info("addImageToPage: img=%t maskImg=%t %q",
		goImg != nil, goMaskImg != nil, spec.MaskImage.ImagePath)

	img, err := c.NewImageWithMaskFromGoImages(goImg, goMaskImg)
	if err != nil {
		return err
	}

	common.Log.Info("addImageToPage:\n%s", img.String())

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

// makeEncoder makes a UniDoc core.StreamEncoder for Go image `goImg` for bits per component `bpc`.
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

// loadGoImage loads the image in file `imagePath` and returns it as a Go image.
func loadGoImage(imagePath string, cpts int) (image.Image, error) {
	imgfile, err := os.Open(imagePath)
	if err != nil {
		return nil, err
	}
	defer imgfile.Close()

	img, _, err := image.Decode(imgfile)
	if err != nil {
		return nil, err
	}

	showGoImage(imagePath, img)
	if img.ColorModel() == color.RGBAModel && cpts == 1 {
		return goImageToGray(img, false), nil
	} else if img.ColorModel() == color.GrayModel && cpts == 3 {
		// TODO: Convert to RBGA.
		// We don't need this yet because all our inpt images are RGB
		panic("not implemented")
	}
	common.Log.Info("colormodel=%+v", img.ColorModel())
	return img, err
}

// showGoImage prints out the dimensions of `img`.
func showGoImage(title string, img image.Image) {
	common.Log.Info("Go image %+q %v", title, img.Bounds())
	return
	// x0, x1 := img.Bounds().Min.X, img.Bounds().Max.X
	// y0, y1 := img.Bounds().Min.Y, img.Bounds().Max.Y
	// for y := y0; y < y1; y++ {
	// 	fmt.Printf("\t")
	// 	for x := x0; x < x1; x++ {
	// 		fmt.Printf("%v, ", img.At(x, y))
	// 	}
	// 	fmt.Printf("\n")
	// }
}

// goImageToGray returns the gray pixel version of `img`. If `bilevel` is true, the gray image is
// thresholded and 0 or 255 level pixels are returned.
func goImageToGray(img image.Image, bilevel bool) image.Image {
	common.Log.Info("goImageToGray: %v %t", img.Bounds(), bilevel)
	x0, x1 := img.Bounds().Min.X, img.Bounds().Max.X
	y0, y1 := img.Bounds().Min.Y, img.Bounds().Max.Y

	grayImg := image.NewGray(img.Bounds())

	for y := y0; y < y1; y++ {
		for x := x0; x < x1; x++ {
			grayImg.Set(x, y, img.At(x, y))
		}
	}
	if bilevel {
		for y := y0; y < y1; y++ {
			for x := x0; x < x1; x++ {
				g := grayImg.GrayAt(x, y).Y
				if g < 127 {
					g = 0
				} else {
					g = 255
				}
				grayImg.SetGray(x, y, color.Gray{g})
			}
		}
	}

	return grayImg
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
