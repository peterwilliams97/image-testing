from sys import argv
import cv2
import os

def main():
    assert len(argv) == 2, (len(argv), argv)
    inPath = argv[1]
    name = os.path.basename(inPath)
    name, _ = os.path.splitext(name)
    color_path = '%s_color.png' % name
    gray_path = '%s_gray.png' % name

    image = cv2.imread(inPath, cv2.IMREAD_COLOR)
    print(type(image))
    print("%s:%s" % (image.shape, image.dtype))
    # assert image, inPath
    source_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(color_path, image)
    cv2.imwrite(gray_path, source_gray)

    for templSize in (7, 9):
        for searchSize in (13, 21):
            denoised_path = '%s_denoised_%dx%d.png' % (
                 name, templSize, searchSize)
            denoised_gray_path = '%s_denoised_gray_%dx%d.png' % (
                name, templSize, searchSize)
            denoised_gray = cv2.fastNlMeansDenoising(source_gray, None,
                                            templateWindowSize=templSize,
                                            searchWindowSize=searchSize)
            cv2.imwrite(denoised_gray_path, denoised_gray)

            denoised = cv2.fastNlMeansDenoisingColored(image, None,
                                                     templateWindowSize=templSize,
                                                     searchWindowSize=searchSize)
            cv2.imwrite(denoised_path, denoised)


main()


# def apply_filters image, denoise=False):
#         """ This method is used to apply required filters to the
#             to extracted regions of interest. Every square in a
#             sudoku square is considered to be a region of interest,
#             since it can potentially contain a value. """
#         # Convert to grayscale
#         source_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         # Denoise the grayscale image if requested in the params
#         if denoise:
#             denoised_gray = cv2.fastNlMeansDenoising(source_gray, None, 9, 13)
#             source_blur = cv2.GaussianBlur(denoised_gray, BLUR_KERNEL_SIZE, 3)
#             # source_blur = denoised_gray
#         else:
#             source_blur = cv2.GaussianBlur(source_gray, (3, 3), 3)
#         source_thresh = cv2.adaptiveThreshold(source_blur, 255, 0, 1, 5, 2)
#         kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
#         source_eroded = cv2.erode(source_thresh, kernel, iterations=1)
#         source_dilated = cv2.dilate(source_eroded, kernel, iterations=1)
#         if ENABLE_PREVIEW_ALL:
#             image_preview(source_dilated)
#         return source_dilated
