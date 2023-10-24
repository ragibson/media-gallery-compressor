import subprocess
import os


def correct_file_extension(temp_filename):
    return f"{os.path.splitext(temp_filename)[0]}.mp4"  # force mp4 container for libx265


def compress_video(input_filename, temp_filename):
    temp_filename = correct_file_extension(temp_filename)
    result = subprocess.run([  # completely deferring to ffmpeg here
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostats",
        "-i", input_filename, "-vcodec", "libx265", "-x265-params", "log-level=error", "-crf", "24",
        f"-movflags", "use_metadata_tags", "-map_metadata", "0",  # to maintain (most) video metadata
        temp_filename
    ])
    if result.returncode:
        print(f"ffmpeg appears to have failed on {repr(input_filename)}. Skipping...")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)  # make sure that this file does not exist
    return temp_filename
