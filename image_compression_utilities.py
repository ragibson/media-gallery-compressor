from PIL import Image
import os


def resize_image(im, minimum_image_dimension):
    if min(im.size) > minimum_image_dimension:
        scaling = minimum_image_dimension / min(im.size)
        im = im.resize(tuple(round(scaling * d) for d in im.size))

    # just in case -- "[in some] image formats, EXIF data is not guaranteed to be in info until load() has been called."
    im.load()
    exif_data = im.info['exif'] if 'exif' in im.info else b""

    return im, exif_data


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


def compress_image(input_filename, temp_filename, output_filename, minimum_image_dimension):
    im = Image.open(input_filename)
    temp_filename, output_filename = correct_file_extension_if_needed(im.format, temp_filename, output_filename)

    if im.format == "JPEG":
        compress_jpeg(im, temp_filename, minimum_image_dimension)
    elif im.format == "PNG":
        compress_png(im, temp_filename, minimum_image_dimension)
    else:
        print(f"Image recognized as {repr(im.format)}, which is neither JPEG nor PNG: {repr(input_filename)}")

    return temp_filename, output_filename


def compress_png(im, temp_filename, minimum_image_dimension):
    im, exif = resize_image(im, minimum_image_dimension)
    # Note: "when optimize=True, compress_level is set to 9 regardless of a value passed"
    im.save(temp_filename, type='png', optimize=True, exif=exif)


def compress_jpeg(im, temp_filename, minimum_image_dimension):
    im, exif = resize_image(im, minimum_image_dimension)
    im.save(temp_filename, type='jpeg', quality=95, subsampling="4:4:4", optimize=True, exif=exif)
