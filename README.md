# media-gallery-compressor

Tool to compress the entire set of photos and videos in a directory (where beneficial).

## Features

* Multithreaded compression typically achieves a throughput of a few GB of images per minute
* Retains "visually lossless" images and photos with extremely high default quality settings
    * PNG: maximum compression level and extra processing pass to determine optimal encoder settings
    * JPEG: 95 quality, 4:4:4 subsampling, and extra processing pass to determine optimal encoder settings
    * Videos: H.265 encoding with CRF 24
    * This typically achieves a ~50% overall size reduction
* Downscales images based on the smaller dimension to support arbitrary aspect ratios
    * By default, keeps resolutions higher than a 4K equivalent
* Corrects image file extensions that are incorrect in the source filesystem
* Retains most image and video metadata from the input as well as the files' modified and access times
* Double checks that all files from the input were copied over to the output, explicitly tagging those that were
  compressed

## Basic Usage

```
usage: compressor.py [-h] -i INPUT_DIRECTORY -o OUTPUT_DIRECTORY
                     [-t TEMP_DIRECTORY] [-v] [-s SUFFIX]
                     [-m MINIMUM_IMAGE_DIMENSION]

Compress all files within a media directory, where beneficial

options:
  -h, --help            show this help message and exit
  -i INPUT_DIRECTORY, --input-directory INPUT_DIRECTORY
                        Input media directory
  -o OUTPUT_DIRECTORY, --output-directory OUTPUT_DIRECTORY
                        Output media directory to create
  -t TEMP_DIRECTORY, --temp-directory TEMP_DIRECTORY
                        Temporary directory to create for intermediate files
                        (default: temp_RG01COMPRESS)
  -v, --verbose         If specified, will increase the verbosity of printed
                        information (default: False)
  -s SUFFIX, --suffix SUFFIX
                        Suffix to append to file names when compressed
                        (default: _RG01COMPRESS)
  -m MINIMUM_IMAGE_DIMENSION, --minimum-image-dimension MINIMUM_IMAGE_DIMENSION
                        Resolution to reduce the smaller image dimension to,
                        if needed (default: 2160)
```

### Example (default settings)

```bash
$ python3 compressor.py -i "media_to_compress" -o "media_after_compression"
TODO
```

### Other usage options

There are a few more command line arguments that I would expect to be more rarely used.

```
  -d, --delete-existing
                        If specified, will delete existing output and temp
                        directories (default: False)
  --jpeg-quality JPEG_QUALITY
                        Quality setting for compressing JPEG images (default:
                        95)
  --jpeg-subsampling JPEG_SUBSAMPLING
                        Subsampling setting for compressing JPEG images
                        (default: 4:4:4)
  --video-codec VIDEO_CODEC
                        Codec for compressing videos with ffmpeg (default:
                        libx265)
  --video-crf VIDEO_CRF
                        Constant rate factor for compressing videos with
                        ffmpeg (default: 24)
  --maximum-expected-compression MAXIMUM_EXPECTED_COMPRESSION
                        Maximum compression percentage for sanity checks. An
                        error will be raised if this threshold is ever
                        exceeded after compressing a file. (default: 99)
```

## Why?

Obviously, this could be used to drastically reduce the file sizes of a media library without any perceptible loss of
quality, but I actually use it to trim down the content on secondary devices.

Perhaps this a bit of an unusual use case, but I have a tremendous amount of photos/videos on my phone and use them more
as a scrapbook to look through occasionally or for reference to trips from long ago. This balloons in size very quickly,
but all the content is backed up elsewhere, so it does not need to be in the original, raw quality at all.

As such, this mass compression focuses on visually lossless, high-quality defaults and otherwise falls back to copying
over the original file if that saves no space.