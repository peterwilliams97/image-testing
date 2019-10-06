package main

import (
	"image"
	"image/color"
	"image/png"
	"os"
	"path/filepath"

	"github.com/unidoc/unipdf/v3/common"
)

const imageDir = "artificial.images" // Where image segments are stored.

func main() {

	if _, err := os.Stat(imageDir); os.IsNotExist(err) {
		os.Mkdir(imageDir, 0777)
	}
	if err := create("tricolor.png", tricolor); err != nil {
		panic(err)
	}
	if err := create("left.png", left); err != nil {
		panic(err)
	}
	if err := create("right.png", right); err != nil {
		panic(err)
	}
	if err := create("top.png", top); err != nil {
		panic(err)
	}
	if err := create("bottom.png", bottom); err != nil {
		panic(err)
	}
	if err := create("white.png", whiteBox); err != nil {
		panic(err)
	}
	if err := create("black.png", blackBox); err != nil {
		panic(err)
	}
}

func create(filename string, rectList []RectCol) error {
	filename = filepath.Join(imageDir, filename)
	img := createImage(rectList)
	return saveGoImage(filename, img)
}

func createImage(rectList []RectCol) image.Image {
	b := union(rectList).bounds()
	rgba := image.NewRGBA(b)
	for _, r := range rectList {
		fillRect(rgba, r.Rect, r.Col)
	}
	return rgba
}

var (
	red    = image.NewUniform(color.RGBA{R: 0xFF, G: 0x00, B: 0x00, A: 0xFF})
	blue   = image.NewUniform(color.RGBA{R: 0x00, G: 0x00, B: 0xFF, A: 0xFF})
	yellow = image.NewUniform(color.RGBA{R: 0xFF, G: 0xFF, B: 0x00, A: 0xFF})
	white  = image.NewUniform(color.RGBA{R: 0xFF, G: 0xFF, B: 0xFF, A: 0xFF})
	black  = image.NewUniform(color.RGBA{R: 0x00, G: 0x00, B: 0x00, A: 0xFF})

	tricolor = []RectCol{
		RectCol{Rect{0, 0, 2, 6}, red},
		RectCol{Rect{2, 0, 4, 6}, blue},
		RectCol{Rect{4, 0, 6, 6}, yellow},
	}
	left = []RectCol{
		RectCol{Rect{0, 0, 3, 6}, white},
		RectCol{Rect{3, 0, 6, 6}, black},
	}
	right = []RectCol{
		RectCol{Rect{0, 0, 3, 6}, black},
		RectCol{Rect{3, 0, 6, 6}, white},
	}
	top = []RectCol{
		RectCol{Rect{0, 0, 6, 3}, white},
		RectCol{Rect{0, 3, 6, 6}, black},
	}
	bottom = []RectCol{
		RectCol{Rect{0, 0, 6, 3}, black},
		RectCol{Rect{0, 3, 6, 6}, white},
	}
	whiteBox = []RectCol{
		RectCol{Rect{0, 0, 6, 6}, white},
	}
	blackBox = []RectCol{
		RectCol{Rect{0, 0, 6, 6}, black},
	}
)

type RectCol struct {
	Rect
	Col *image.Uniform
}
type Rect struct {
	X0, Y0, X1, Y1 int
}

func union(rectList []RectCol) Rect {
	var u Rect
	for _, r := range rectList {
		if r.X0 < u.X0 {
			u.X0 = r.X0
		}
		if r.Y0 < u.Y0 {
			u.Y0 = r.Y0
		}
		if r.X1 > u.X1 {
			u.X1 = r.X1
		}
		if r.Y1 > u.Y1 {
			u.Y1 = r.Y1
		}
	}
	return u
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

func fillRect(img *image.RGBA, r Rect, col *image.Uniform) {
	for y := r.Y0; y < r.Y1; y++ {
		for x := r.X0; x < r.X1; x++ {
			img.Set(x, y, col)
		}
	}
}

// saveGoImage saves Go image `img` to file `filename` with imageEncoding `enc`.
func saveGoImage(filename string, img image.Image) error {
	out, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer out.Close()

	return png.Encode(out, img)
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

	return grayImg
}
