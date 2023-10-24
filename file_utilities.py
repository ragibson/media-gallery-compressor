"""This file handles details related to the filesystem itself."""
from collections import defaultdict
import shutil
import os


def sizeof_fmt(num, suffix="B"):
    """
    Convert a number of bytes into a more human-readable format.

    Note that this uses decimal bytes rather than binary. For instance, we use
        1 gigabyte (GB) is 10^9 bytes
    instead of
        1 gibibyte (GiB) is 2^30 ~ 1.07 * 10^9 bytes
    """
    for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < 10 ** 3:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 10 ** 3
    return f"{num:.1f} Y{suffix}"


def lowercase_file_extension(filename):
    """
    Return lowercase version of the file extension for this file.

    This really just exists to remind myself to never pull the file extension without converting it to lowercase.
    """
    return os.path.splitext(filename)[-1].lower()


def prepare_directories(args):
    """
    Copy the directory structure (no files) of the input media files over to the output and temp directories.

    Notably, the temp subdirectories are mainly to avoid name collisions since they will only ever contain a few files.
    """
    for destination_directory in (args.output_directory, args.temp_directory):
        shutil.copytree(
            args.input_directory, destination_directory,
            ignore=lambda directory, files: [f for f in files if os.path.isfile(os.path.join(directory, f))]
        )


def summarize_directory_files(args, arg_name, all_files):
    """Print a summary of the files in this directory to stdout, broken down by directory and file extension.

    arg_name is used to convert absolute file paths to relative ones for more concise output.

    :param args: Command line arguments from argparse
    :param arg_name: CLI argument name specifying directory to analyze (e.g., input_directory, output_directory, etc.)
    :param all_files: A list of all file paths in this directory to analyze
    """
    directory_sizes = defaultdict(int)  # directory -> size
    filetype_sizes = defaultdict(lambda: defaultdict(int))  # directory -> file extension -> size
    for fn in all_files:
        if os.path.isfile(fn):
            dir_name, file_size = os.path.dirname(fn), os.path.getsize(fn)
            directory_sizes[dir_name] += file_size
            filetype_sizes[dir_name][lowercase_file_extension(fn)] += file_size

    print(f"{arg_name} summary ({sizeof_fmt(sum(directory_sizes.values()))} in total):")
    for directory, total_filesize in sorted(directory_sizes.items(), key=lambda x: x[1], reverse=True):
        print(f"{arg_name} -> {os.path.relpath(directory, getattr(args, arg_name))} "
              f"({sizeof_fmt(total_filesize)} in total):")
        for extension, filesize in sorted(filetype_sizes[directory].items(), key=lambda x: x[1], reverse=True):
            print(f"|  {extension} only: {sizeof_fmt(filesize)}")
    print()
