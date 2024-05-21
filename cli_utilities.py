"""This file handles details related to the command line interface of the media compressor."""
from multiprocessing import cpu_count
import argparse
import os
import shutil

DEFAULT_COMPRESSED_FILENAME_TAG = "_RG01COMPRESS"  # default filename suffix to tag files that were compressed


def parse_arguments():
    """Set up arguments for the compressor's command line interface."""
    parser = argparse.ArgumentParser(description="Compress all files within a media directory, where beneficial",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     argument_default=argparse.SUPPRESS)
    parser.add_argument("-i", "--input-directory", help="Input media directory", required=True)
    parser.add_argument("-o", "--output-directory", help="Output media directory to create", required=True)
    parser.add_argument("-t", "--temp-directory", help="Temporary directory to create for intermediate files",
                        default=f"temp{DEFAULT_COMPRESSED_FILENAME_TAG}")
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="If specified, will increase the verbosity of printed information")
    parser.add_argument("-d", "--delete-existing", action="store_true", default=False,
                        help="If specified, will delete existing output and temp directories")
    parser.add_argument("-s", "--suffix", help="Suffix to append to file names when compressed",
                        default=DEFAULT_COMPRESSED_FILENAME_TAG)
    parser.add_argument("-m", "--minimum-image-dimension", default=2160, type=int,
                        help="Resolution to reduce the smaller image dimension to, if needed")
    parser.add_argument("-p", "--processes", default=cpu_count(), type=int,
                        help="Maximum number of compression processes to run in parallel. "
                             "Defaults to the number of CPUs in the system.")
    parser.add_argument("--jpeg-quality", default=95, type=int, help="Quality setting for compressing JPEG images")
    parser.add_argument("--jpeg-subsampling", default="4:4:4", help="Subsampling setting for compressing JPEG images")
    parser.add_argument("--video-codec", default="libx265", help="Codec for compressing videos with ffmpeg")
    parser.add_argument("--video-crf", default="24", help="Constant rate factor for compressing videos with ffmpeg")
    parser.add_argument("--maximum-expected-compression", default=99, type=int,
                        help="Maximum compression percentage for sanity checks. An error will be raised if this "
                             "threshold is ever exceeded after compressing a file")
    return parser.parse_args()


def validate_arguments(args):
    """
    Validate CLI arguments. In particular:
        1) The I/O directories used should all be unique
        2) The input directory must exist
        3) If the user did not explicitly ask for deletion of existing temp and output directories, then the existence
           of those directories is treated as a fatal error

    Afterward, print out a summary of the options being used.
    """
    if len({args.input_directory, args.output_directory, args.temp_directory}) != 3:
        raise ValueError("Input, output, and temp directories should all be unique!")

    if not os.path.exists(args.input_directory):
        raise ValueError(f"Input directory does not exist: {repr(args.input_directory)}")

    if args.delete_existing:
        for fp in [args.output_directory, args.temp_directory]:
            if os.path.exists(fp):
                shutil.rmtree(fp)

    if os.path.exists(args.output_directory):
        raise ValueError(f"Output directory should not exist. Did you mean to include --delete-existing? "
                         f"{repr(args.output_directory)}")

    if os.path.exists(args.temp_directory):
        raise ValueError(f"Temp directory should not exist. Did you mean to include --delete-existing? "
                         f"{repr(args.temp_directory)}")

    # final summary of CLI options after validation
    if args.verbose:
        print(f"Continuing with options:")
        for arg in vars(args):
            print(f"  {arg}: {repr(getattr(args, arg))}")
        print()
