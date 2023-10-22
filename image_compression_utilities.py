from PIL import Image
import os
import shutil


def resize_image(im, minimum_image_dimension):
    if min(im.size) > minimum_image_dimension:
        scaling = minimum_image_dimension / min(im.size)
        im = im.resize(tuple(round(scaling * d) for d in im.size))

    # just in case -- "[in some] image formats, EXIF data is not guaranteed to be in info until load() has been called."
    im.load()
    exif_data = im.info['exif'] if 'exif' in im.info else b""

    return im, exif_data


def copy_optimal_compressed_file(input_filename, temp_filename, output_filename, suffix):
    assert os.path.exists(input_filename) and os.path.exists(temp_filename)
    assert not os.path.exists(output_filename)

    if os.path.getsize(temp_filename) < os.path.getsize(input_filename):
        # use compressed tag suffix since we edited this file
        filename, ext = os.path.splitext(output_filename)
        shutil.move(temp_filename, f"{filename}{suffix}{ext}")  # TODO: retain modify/access times
    else:
        os.remove(temp_filename)
        shutil.copyfile(input_filename, output_filename)


def correct_file_extension_if_needed(image_format, temp_filename, output_filename):
    temp_extension = os.path.splitext(temp_filename)[-1]
    assert os.path.splitext(output_filename)[-1] == temp_extension

    if image_format == "JPEG" and temp_extension != "jpg":
        temp_filename = f"{os.path.splitext(temp_filename)[0]}.jpg"
        output_filename = f"{os.path.splitext(output_filename)[0]}.jpg"
    elif image_format == "PNG" and temp_extension != "png":
        temp_filename = f"{os.path.splitext(temp_filename)[0]}.png"
        output_filename = f"{os.path.splitext(output_filename)[0]}.png"
    return temp_filename, output_filename


def compress_image(input_filename, temp_filename, output_filename, suffix, minimum_image_dimension):
    im = Image.open(input_filename)
    temp_filename, output_filename = correct_file_extension_if_needed(im.format, temp_filename, output_filename)

    if im.format == "JPEG":
        compress_jpeg(im, temp_filename, minimum_image_dimension)
        copy_optimal_compressed_file(input_filename, temp_filename, output_filename, suffix)
    elif im.format == "PNG":
        compress_png(im, temp_filename, minimum_image_dimension)
        copy_optimal_compressed_file(input_filename, temp_filename, output_filename, suffix)
    else:
        print(f"Ignoring image with file type {repr(im.format)}")  # TODO: remove
        shutil.copyfile(input_filename, output_filename)


def compress_png(im, temp_filename, minimum_image_dimension):
    im, exif = resize_image(im, minimum_image_dimension)
    # Note: "when optimize=True, compress_level is set to 9 regardless of a value passed"
    im.save(temp_filename, type='png', optimize=True, exif=exif)


def compress_jpeg(im, temp_filename, minimum_image_dimension):
    im, exif = resize_image(im, minimum_image_dimension)
    im.save(temp_filename, type='jpeg', quality=95, subsampling="4:4:4", optimize=True, exif=exif)
