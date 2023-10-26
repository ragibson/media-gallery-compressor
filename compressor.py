"""The main entrypoint of the compression routine."""
from collections import Counter
from cli_utilities import parse_arguments, validate_arguments
from compression_utilities import compress_image, compress_video
from file_utilities import prepare_directories, summarize_directory_files, lowercase_file_extension
from multiprocessing import Pool
from tqdm import tqdm
import glob
import os
import shutil

IMPLEMENTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png"}
IMPLEMENTED_VIDEO_FORMATS = {".mp4", ".mov", ".3gp"}


def choose_compression_or_original_file(input_filename, temp_filename, output_filename, suffix):
    """
    Decide whether to copy the compressed, temp file or the original to the output directory, based on file size.

    We also maintain the access and modified times of the original files.

    Notably, the temporary file is removed during this method, either because
        (i) it was *moved* over to the output directory
        (ii) it was deleted after discovering the original input file was smaller, and we *copied* the original instead
    """
    if not os.path.exists(input_filename):
        raise ValueError(f"Input file seems to no longer exist: {repr(input_filename)}")
    if os.path.exists(output_filename):
        # this could theoretically occur if
        #   two photos with the same name exist, but one has an incorrect file extension
        #   two videos with the same name exist, but with different file extensions
        # otherwise, this is a sign that something has gone wrong, so I'm raising an error here
        # TODO: handle file name collisions automatically?
        raise ValueError(f"Encountered a file collision when copying to the output directory: {repr(output_filename)}")

    if os.path.exists(temp_filename) and os.path.getsize(temp_filename) < os.path.getsize(input_filename):
        filename, _ = os.path.splitext(output_filename)
        _, ext = os.path.splitext(temp_filename)  # adopt final file extension from the compression routines

        output_filename = f"{filename}{suffix}{ext}"  # use compressed tag suffix since we edited this file
        shutil.move(temp_filename, output_filename)  # move compressed version over to output directory
    else:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)  # the original file is smaller, so no need for the compressed version
        shutil.copyfile(input_filename, output_filename)

    # retain modify/access times from the input files
    st = os.stat(input_filename)
    os.utime(output_filename, (st.st_atime, st.st_mtime))


def compress_single_file(bundled_imap_args):
    """
    Run the compression function corresponding to the file type of the input file.

    In this case, the arguments are bundled into one object for use with multiprocessing's imap_unordered
        bundled_imap_args := input_filename (str), args (argparse.Namespace)
    """
    input_filename, args = bundled_imap_args
    if not os.path.isfile(input_filename):
        return  # no work to do
    if not os.path.exists(input_filename):
        raise ValueError(f"Tried to compress file that does not exist: {repr(input_filename)}")

    # set temp/output filenames to the input filename, but in the temp/output directories
    temp_filename = os.path.join(args.temp_directory, os.path.relpath(input_filename, args.input_directory))
    output_filename = os.path.join(args.output_directory, os.path.relpath(input_filename, args.input_directory))

    claimed_file_extension = lowercase_file_extension(input_filename)
    if claimed_file_extension not in IMPLEMENTED_IMAGE_FORMATS | IMPLEMENTED_VIDEO_FORMATS:
        # do not attempt compression, just copy this file over to the output and return
        print(f"Unimplemented file extension: {os.path.relpath(input_filename, args.input_directory)}")
        shutil.copyfile(input_filename, output_filename)
        return

    if claimed_file_extension in IMPLEMENTED_IMAGE_FORMATS:
        temp_filename = compress_image(input_filename=input_filename, temp_filename=temp_filename, args=args)
    elif claimed_file_extension in IMPLEMENTED_VIDEO_FORMATS:
        temp_filename = compress_video(input_filename=input_filename, temp_filename=temp_filename, args=args)

    # copy over the smallest of the original, input file or the compressed, temp file to the output directory
    choose_compression_or_original_file(input_filename=input_filename, temp_filename=temp_filename,
                                        output_filename=output_filename, suffix=args.suffix)


def compress_all_files(args, all_input_files):
    """Run parallel compression of all input media files."""
    with Pool() as pool:
        pool_args = [(fn, args) for fn in all_input_files]
        list(tqdm(pool.imap_unordered(compress_single_file, pool_args), total=len(pool_args),
                  desc="Compressing input files"))


def verify_compression_consistency(args, all_input_files, all_output_files):
    """
    Verify that the final output directory is consistent with the original input directory.

    This includes a few checks between the input and the output:
        (i) ensure that the number of files match
        (ii) ensure that all the names of the files match
        (iii) ensure that the compression rate is never too high
    """

    def relative_canonical_name(filepath, start, check_suffix=False):
        relname = os.path.splitext(os.path.relpath(filepath, start))[0]
        if check_suffix and relname.endswith(args.suffix):
            relname = relname[:-len(args.suffix)]
        return relname

    if len(all_input_files) != len(all_output_files):
        raise RuntimeError("The final count of output files did not match the input!")

    all_input_files.sort(key=lambda f: relative_canonical_name(f, args.input_directory))
    all_output_files.sort(key=lambda f: relative_canonical_name(f, args.output_directory, check_suffix=True))

    for idx, (input_filepath, output_filepath) in enumerate(zip(all_input_files, all_output_files)):
        if not os.path.isfile(input_filepath) and not os.path.isfile(output_filepath):
            continue

        input_name = repr(relative_canonical_name(input_filepath, args.input_directory))
        output_name = repr(relative_canonical_name(output_filepath, args.output_directory, check_suffix=True))
        if input_name != output_name:
            raise RuntimeError(f"In final consistency check, file #{idx} did not match: {input_name} vs. {output_name}")

        compression_rate = 1 - os.stat(output_filepath).st_size / os.stat(input_filepath).st_size
        if compression_rate > args.maximum_expected_compression:
            raise RuntimeError(f"Compression appears to have achieved unrealistic compression "
                               f"rate of {100 * compression_rate:.1f}% on {input_name}")

    print("Output directory appears consistent with the input.\n")


def clean_up_temp_directory(args):
    """Verify that the temporary directory is empty and delete it."""
    all_temp_files = list(filter(os.path.isfile, glob.glob(os.path.join(args.temp_directory, "**"), recursive=True)))
    if len(all_temp_files):
        # if there are still temp files left over from the compression methods, something has probably gone wrong
        raise RuntimeError("The temp directory is not empty, but there should be nothing left there!")

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

    # check for file name collisions since they could cause issues, and we do not explicitly handle them
    collisions_detected = False
    for fn, count in Counter([os.path.splitext(os.path.relpath(f, args.input_directory))[0]
                              for f in all_input_files]).items():
        if count > 1:
            collisions_detected = True
            print(f"Found multiple files ({count}) with the same name! {repr(fn)}")
    if collisions_detected:
        raise ValueError("File name collisions detected, which may cause issues when finalizing compressed output.")

    # actually run the mass compression routines
    compress_all_files(args, all_input_files)

    # verify that all input media files have a match in the output directories and remove lingering temp directories
    all_output_files = glob.glob(os.path.join(args.output_directory, "**"), recursive=True)
    verify_compression_consistency(args, all_input_files, all_output_files)
    clean_up_temp_directory(args)

    # summarize final output file sizes
    summarize_directory_files(args, "output_directory", all_output_files)
