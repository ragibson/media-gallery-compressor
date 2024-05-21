# media-gallery-compressor

Tool to compress the entire set of photos and videos in a directory (where beneficial).

## Table of Contents

* [Features](#features)
* [Basic Usage](#basic-usage)
* [Examples and other quality recommendations](#examples-and-other-quality-recommendations)
* [Why?](#why)

## Features

* Multithreaded compression typically achieves a throughput of a few GB of images per minute
* Retains "visually lossless" images and photos with extremely high default quality settings that typically achieve ~60%
  compression
    * PNG: maximum compression level and extra processing pass to determine optimal encoder settings
    * JPEG: 95 quality, 4:4:4 subsampling, and extra processing pass to determine optimal encoder settings
    * Videos: H.265 encoding with CRF 24
* Downscales images based on the smaller dimension to support arbitrary aspect ratios
    * By default, keeps resolutions higher than a 4K equivalent
* Corrects image file extensions that are incorrect in the source filesystem
* Retains most image and video metadata from the input as well as the files' modified and access times
* Double checks that all files from the input were copied over to the output, explicitly tagging those that were
  compressed
* Only depends on Pillow (for image compression), ffmpeg (for video compression), and tqdm (for displaying progress)

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
  -p PROCESSES, --processes PROCESSES
                        Maximum number of compression processes to run in parallel. Defaults to the number of CPUs in the system. (default: 8)
```

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

### Examples and other quality recommendations

Using default settings, we get an overall compression rate of ~60%.

Some alternative "high-quality" settings would be using 1440p resolution, JPEG quality 90, and CRF 26. This achieves a
compression rate of ~80%.

Finally, a more "medium" quality setting of 1080p resolution, JPEG quality 85, JPEG 4:2:0 subsampling, and CRF 28
yields a compression rate of ~90%.

```bash
$ python3 compressor.py -i "media_to_compress" -o "media_after_compression"
Processing 8445 input files...

input_directory summary (49.5 GB in total):
input_directory -> Camera (48.7 GB in total):
|  .jpg only: 28.8 GB
|  .mp4 only: 19.5 GB
|  .mov only: 168.9 MB
|  .dng only: 99.9 MB
|  .png only: 56.6 MB
(Other subdirectories omitted for example)

Compressing input files: 100%|█████████████████████████████| 8445/8445
Output directory appears consistent with the input.

output_directory summary (20.9 GB in total):
output_directory -> Camera (20.4 GB in total):
|  .jpg only: 14.9 GB
|  .mp4 only: 5.3 GB
|  .dng only: 99.9 MB
|  .png only: 43.2 MB
|  .mov only: 6.2 MB
(Other subdirectories omitted for example)

$ python3 compressor.py -i "media_to_compress" -o "media_after_compression" -m 1440 --jpeg-quality 90 --video-crf 26
(Input summary omitted for example)
output_directory summary (9.6 GB in total):
output_directory -> Camera (9.2 GB in total):
|  .jpg only: 5.2 GB
|  .mp4 only: 3.9 GB
|  .dng only: 99.9 MB
|  .png only: 36.6 MB
(Other subdirectories omitted for example)

$ python3 compressor.py -i "media_to_compress" -o "media_after_compression" -m 1080 --jpeg-quality 85 --jpeg-subsampling "4:2:0" --video-crf 28
(Input summary omitted for example)
output_directory summary (5.5 GB in total):
output_directory -> Camera (5.3 GB in total):
|  .mp4 only: 2.8 GB
|  .jpg only: 2.3 GB
|  .dng only: 99.9 MB
|  .png only: 32.2 MB
(Other subdirectories omitted for example)
```

## Why?

Obviously, this could be used to drastically reduce the file sizes of a media library without any perceptible loss of
quality, but I actually use it to trim down the content on secondary devices.

Perhaps this a bit of an unusual use case, but I have a tremendous amount of photos/videos on my phone and use them more
as a scrapbook to look through occasionally or for reference to trips from long ago. This balloons in size very quickly,
but all the content is backed up elsewhere, so it does not need to be in the original, raw quality at all.

As such, this mass compression focuses on visually lossless, high-quality defaults and otherwise falls back to copying
over the original file if that saves no space.