"""
This file handles compression of individual image or video files. Notably,
    1) Resize images down to a smaller size if requested
    2) Correct file extensions that are incorrect in the source filesystem
    3) Retain "visually lossless", high-quality media by default:
        PNG    - maximum compression level + extra processing pass to determine optimal encoder settings
        JPEG   - 95 quality + 4:4:4 subsampling + extra processing pass to determine optimal encoder settings
        videos - H.265 encoding with CRF 24

The basic idea throughout this script is that we have three versions of the same file at various times:
    Input: the original, unedited photo/video
    Temp: a temporary file of the same name (and a compression filename tag) corresponding to an input file
    Output: the final result that is the smallest of the original input or the compressed, temporary file
"""
from PIL import Image
from file_utilities import lowercase_file_extension
import os
import subprocess


def resize_image_and_retain_exif(im, minimum_image_dimension):
    """Resize image if the smaller dimension of its resolution exceeds the requested minimum image dimension.

    At this time, we also load in the EXIF data for copying later.

    The default for this resizing is 2160 (i.e., the height of a 4K monitor), so
        1) Large horizontal 16:9 images will be resized to 3840x2160
        2) Large vertical 16:9 images will be resized to 2160x3840

    However, this also applies to any other aspect ratio. For example, we would resize
        (32MP, ultra-wide 21:9) 8652x3708 -> 5040x2160 (~11 MP)
    """
    # just in case -- "[in some] image formats, EXIF data is not guaranteed to be in info until load() has been called."
    im.load()
    exif_data = im.info['exif'] if 'exif' in im.info else b""

    if min(im.size) > minimum_image_dimension:
        scaling = minimum_image_dimension / min(im.size)
        im = im.resize(tuple(round(scaling * d) for d in im.size))

    return im, exif_data


def correct_image_extension_if_needed(image_format, temp_filename):
    """If an input photo has the incorrect file extension, correct it in the temp file's name before compressing."""
    temp_extension = lowercase_file_extension(temp_filename)
    if image_format == "JPEG" and temp_extension != "jpg":
        temp_filename = f"{os.path.splitext(temp_filename)[0]}.jpg"
    elif image_format == "PNG" and temp_extension != "png":
        temp_filename = f"{os.path.splitext(temp_filename)[0]}.png"
    return temp_filename


def compress_image(input_filename, temp_filename, args):
    """Run compression on a single input image and save the compressed version to a temporary file."""
    im = Image.open(input_filename)
    temp_filename = correct_image_extension_if_needed(im.format, temp_filename)

    if im.format == "JPEG":
        compress_jpeg(im, temp_filename, args.minimum_image_dimension, args.jpeg_quality, args.jpeg_subsampling)
    elif im.format == "PNG":
        compress_png(im, temp_filename, args.minimum_image_dimension)
    elif args.verbose:
        print(f"Pillow detected image as {repr(im.format)}, skipping compression of {repr(input_filename)}")

    return temp_filename


def compress_png(im, temp_filename, minimum_image_dimension):
    """Compress PNG file with the maximum compression level + postprocessing to determine optimal encoder settings"""
    im, exif = resize_image_and_retain_exif(im, minimum_image_dimension)
    # Note: "when optimize=True, compress_level is set to 9 regardless of a value passed"
    im.save(temp_filename, type='png', optimize=True, exif=exif)


def compress_jpeg(im, temp_filename, minimum_image_dimension, jpeg_quality, jpeg_subsampling):
    """Compress JPEG file with default settings of 95 quality + 4:4:4 subsampling + encoder postprocessing."""
    im, exif = resize_image_and_retain_exif(im, minimum_image_dimension)
    im.save(temp_filename, type='jpeg', quality=jpeg_quality, subsampling=jpeg_subsampling, optimize=True, exif=exif)


def correct_video_extension(temp_filename):
    """Change temporary file extensions to MP4 to support H.265 encoding."""
    return f"{os.path.splitext(temp_filename)[0]}.mp4"  # force mp4 container for libx265


def compress_video(input_filename, temp_filename, args):
    """
    Run ffmpeg to compress an input video into the temp file with default settings of H.265 and CRF 24.

    We also try to suppress some codec-specific logging output for H.264 / H.265 and retain (most) video metadata.
    """
    temp_filename = correct_video_extension(temp_filename)

    suppress_codec_logging = (  # suppress, e.g., "x265 [info]:" lines on stdout unless they're related to errors
        ["-x265-params", "log-level=error"] if args.video_codec == "libx265"
        else ["-x264-params", "log-level=error"] if args.video_codec == "libx264"
        else []
    )
    # this retains most of the available metadata from the input videos
    retain_video_metadata = ["-movflags", "use_metadata_tags", "-map_metadata", "0"]

    result = subprocess.run(  # completely deferring to ffmpeg subprocess here
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostats", "-i", input_filename, "-vcodec", args.video_codec]
        + suppress_codec_logging + ["-crf", args.video_crf] + retain_video_metadata + [temp_filename]
    )

    # if ffmpeg failed, make sure that the output temp file does not exist
    if result.returncode:
        print(f"ffmpeg appears to have failed, skipping compression of {repr(input_filename)}")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    return temp_filename
