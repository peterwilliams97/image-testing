package main

import (
	"flag"
	"image"
	"image/jpeg"
	"os"

	"github.com/mdouchement/bilateral"
	"github.com/unidoc/unipdf/v3/common"
)

func main() {
	flag.Parse()
	args := flag.Args()
	if len(args) < 1 {
		flag.Usage()
		os.Exit(1)
	}
	common.SetLogger(common.NewConsoleLogger(common.LogLevelDebug))

	filename := args[0]
	fi, _ := os.Open(filename)
	defer fi.Close()

	m, _, _ := image.Decode(fi)

	// start := time.Now()
	fbl := bilateral.New(m, 16, 0.1)
	common.Log.Info("fbl=%v", fbl)
	fbl.Execute()
	m2 := fbl.ResultImage() // Or use `At(x, y)` func or just use `fbl` as an image.Image for chained treatments.

	fo, _ := os.Create("output_path")
	defer fo.Close()

	jpeg.Encode(fo, m2, &jpeg.Options{Quality: 100})
}
