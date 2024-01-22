from PIL import Image

# def get_jpeg_metadata(image_path):
#     try:
#         image = Image.open(image_path)
#         if hasattr(image, '_getexif'):
#             exif_data = image._getexif()
#             if exif_data is not None:
#                 return exif_data
#         return {}
#     except Exception as e:
#         return str(e)

from PIL import Image
from PIL.ExifTags import TAGS


def get_jpeg_time_taken(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()

        if exif_data is not None:
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == 'DateTimeOriginal' or tag_name == 'DateTime':
                    return value

        return None  # Return None if no time information is found in the metadata
    except Exception as e:
        return str(e)


# Example usage:
image_path = r'D:\amazon_photo_download\Amazon Photos Downloads\Pictures\Korou’s IPhone X\2018-10-10_13-56-22_559.jpeg'
time_taken = get_jpeg_time_taken(image_path)

if time_taken:
    print("Time Taken:", time_taken)
else:
    print("Time information not found in metadata.")
# Example usage:
# image_path = r'D:\amazon_photo_download\Amazon Photos Downloads\Pictures\Korou’s IPhone X\2018-10-10_13-56-22_559.jpeg'
# metadata = get_jpeg_metadata(image_path)
# print(metadata)