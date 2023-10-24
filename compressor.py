# TODO: add docstrings
# TODO: overall refactor to encapsulate saving functionality, image vs. video shared details, etc.
from image_compression_utilities import compress_image
from video_compression_utilities import compress_video
import argparse
from collections import defaultdict
import glob
from multiprocessing import Pool
import os
import shutil
from tqdm import tqdm

COMPRESSED_FILENAME_TAG = "_RG1COMPRESS"
IMPLEMENTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png"}
IMPLEMENTED_VIDEO_FORMATS = {".mp4", ".mov", ".3gp"}


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < 10 ** 3:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 10 ** 3
    return f"{num:.1f} Y{suffix}"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Compress all files within a media directory",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     argument_default=argparse.SUPPRESS)
    parser.add_argument("-i", "--input-directory", help="Input media directory", required=True)
    parser.add_argument("-o", "--output-directory", help="Output media directory to create", required=True)
    parser.add_argument("-s", "--suffix", help="Suffix to append to file names when compressed",
                        default=COMPRESSED_FILENAME_TAG)
    parser.add_argument("-m", "--minimum-image-dimension", default=2160,
                        help="Resolution to reduce the smaller image dimension to, if needed")
    parser.add_argument("-t", "--temp-directory", help="Temporary directory to create for intermediate files",
                        default=f"temp{COMPRESSED_FILENAME_TAG}")
    parser.add_argument("-d", "--delete-existing", action="store_true", default=False,
                        help="If specified, will delete existing output and temp directories")
    return parser.parse_args()


def validate_arguments(args):
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
        raise ValueError(f"Output directory should not exist. Did you mean to include --delete-existing? "
                         f"{repr(args.temp_directory)}")

    print(f"Continuing with options:")
    for arg in vars(args):
        print(f"  {arg}: {repr(getattr(args, arg))}")
    print()


def prepare_directories(args):
    # copy directory structure (no files) over to output and temp directories
    shutil.copytree(args.input_directory, args.output_directory,
                    ignore=lambda directory, files: [f for f in files if os.path.isfile(os.path.join(directory, f))])

    # the temp subdirectories are only to avoid name collisions since it will only contain a few files at any given time
    shutil.copytree(args.input_directory, args.temp_directory,
                    ignore=lambda directory, files: [f for f in files if os.path.isfile(os.path.join(directory, f))])


def summarize_directory_files(args, arg_name, all_files):
    directory_sizes = defaultdict(int)  # directory -> size
    filetype_sizes = defaultdict(lambda: defaultdict(int))  # directory -> file extension -> size
    for fn in all_files:
        if os.path.isfile(fn):
            directory_sizes[os.path.dirname(fn)] += os.path.getsize(fn)
            filetype_sizes[os.path.dirname(fn)][os.path.splitext(fn)[-1].lower()] += os.path.getsize(fn)

    print(f"{arg_name} summary ({sizeof_fmt(sum(directory_sizes.values()))} in total):")
    for directory, total_filesize in sorted(directory_sizes.items(), key=lambda x: x[1], reverse=True):
        print(f"{arg_name} -> {os.path.relpath(directory, getattr(args, arg_name))} "
              f"({sizeof_fmt(total_filesize)} in total):")
        for extension, filesize in sorted(filetype_sizes[directory].items(), key=lambda x: x[1], reverse=True):
            print(f"|  {extension} only: {sizeof_fmt(filesize)}")
    print()


def copy_optimal_compressed_file(input_filename, temp_filename, output_filename, suffix):
    assert os.path.exists(input_filename) and not os.path.exists(output_filename)

    if os.path.exists(temp_filename) and os.path.getsize(temp_filename) < os.path.getsize(input_filename):
        # adopt final chosen file extension from compression method
        filename, _ = os.path.splitext(output_filename)
        _, ext = os.path.splitext(temp_filename)

        # use compressed tag suffix since we edited this file
        shutil.move(temp_filename, f"{filename}{suffix}{ext}")  # TODO: retain modify/access times
    else:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        shutil.copyfile(input_filename, output_filename)


def compress_single_file(bundled_imap_args):
    input_filename, args = bundled_imap_args
    if not os.path.isfile(input_filename):
        return  # no work to do
    temp_filename = os.path.join(args.temp_directory, os.path.relpath(input_filename, args.input_directory))
    output_filename = os.path.join(args.output_directory, os.path.relpath(input_filename, args.input_directory))

    claimed_file_extension = os.path.splitext(input_filename)[-1].lower()
    if claimed_file_extension in IMPLEMENTED_IMAGE_FORMATS:
        temp_filename = compress_image(input_filename, temp_filename, args.minimum_image_dimension)
        copy_optimal_compressed_file(input_filename, temp_filename, output_filename, args.suffix)
    elif claimed_file_extension in IMPLEMENTED_VIDEO_FORMATS:
        temp_filename = compress_video(input_filename, temp_filename)
        copy_optimal_compressed_file(input_filename, temp_filename, output_filename, args.suffix)
    else:
        print(f"Unimplemented file extension: {os.path.relpath(input_filename, args.input_directory)}")
        shutil.copyfile(input_filename, output_filename)


def compress_all_files(args, all_input_files):
    with Pool() as pool:
        pool_args = [(fn, args) for fn in all_input_files]
        list(tqdm(pool.imap_unordered(compress_single_file, pool_args), total=len(pool_args),
                  desc="Compressing input files"))


def verify_compression_consistency(args, all_input_files, all_output_files):
    all_temp_files = list(filter(os.path.isfile, glob.glob(os.path.join(args.temp_directory, "**"), recursive=True)))
    if len(all_temp_files):
        raise RuntimeError("The temp directory is not empty, but there should be nothing left there!")

    if len(all_input_files) != len(all_output_files):
        raise RuntimeError("The final count of output files did not match the input!")

    # TODO: verify based on file names too

    print("Output directory appears consistent with the input.\n")


def clean_up_temp_directory(args):
    shutil.rmtree(args.temp_directory)


if __name__ == "__main__":
    # Process and validate command line arguments
    args = parse_arguments()
    validate_arguments(args)

    # Prepare input, output, and temp directories
    prepare_directories(args)

    # Get list of all input media files and summarize file sizes by directory and file extension
    all_input_files = glob.glob(os.path.join(args.input_directory, "**"), recursive=True)
    print(f"Processing {len(all_input_files)} input files...\n")
    summarize_directory_files(args, "input_directory", all_input_files)

    compress_all_files(args, all_input_files)  # actually run the mass compression routines

    # verify that all input media files have a match in the output directories and remove lingering temp files
    all_output_files = glob.glob(os.path.join(args.output_directory, "**"), recursive=True)
    verify_compression_consistency(args, all_input_files, all_output_files)
    clean_up_temp_directory(args)

    # summarize final output file sizes
    summarize_directory_files(args, "output_directory", all_output_files)
