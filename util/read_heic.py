import glob
import logging
import os
import os.path
import pathlib
import shutil
import zlib
import datetime

import dateutil.parser
import traceback
import ffmpeg
from collections import defaultdict
from datetime import datetime
from enum import Enum
from PIL import Image
import PIL
from pillow_heif import register_heif_opener

TRAIL_RUN = False
TRAIL_RUN_MAX = 10000

FILE_LOGGER_LEVEL       = logging.INFO
CONSOLE_LOGGER_LEVEL    = logging.INFO

class Media_Type(Enum):
    PHOTO = 1
    VIDEO = 2
    NON_MEDIA = 9

BACKUP_STATUS_FILENAME = 'backup.status.csv'

CHUNK_SIZE = 65536
PROGRESS_COUNTER = 100
RUN_ID = 0
RUN_ID_PROMOTER = 20
AD_START_TIME = "1111/11/11 11:11:11"

EXIF_IMAGE_DATETIME_TAG_36867 = 36867
EXIF_IMAGE_DATETIME_TAG_306 = 306


WILDCARD_FILES_PATTERN = r'**/*.*'

video_ext = {"webm","mkv","flv","flv","vob","ogv","ogg","drc","gif","gifv","mng","avi","MTS","M2TS","TS","mov","qt","wmv",
             "yuv","rm","rmvb","viv","asf","amv","mp4","m4p","m4v","mpg","mp2","mpeg","mpe","mpv","mpg","mpeg","m2v","m4v",
             "svi","3gp","3g2","mxf","roq","nsv","flv ","f4v ","f4p ","f4a ","f4b"}
photo_ext = {"ase",	"art","bmp","blp","cd5","cit","cpt","cr2","cut","dds","dib","djvu","egt","exif","gif","gpl",
             "grf","icns","ico","iff","jng","jpeg","jpg","jfif","jp2","jps","lbm","max","miff","mng","msp","nef","nitf",
             "ota","pbm","pc1","pc2","pc3","pcf","pcx","pdn","pgm","PI1","PI2","PI3","pict","pct","pnm","pns","ppm","psb",
             "psd","pdd","psp","px","pxm","pxr","qfx","raw","rle","sct","sgi","rgb","int"

    ,"bw","tga","tiff","tif","vtf",
             "xbm","xcf","xpm","3dv","amf","ai","awg","cgm","cdr","cmx","dxf","e2d","egt","eps","fs","gbr","odg","svg",
             "stl","vrml","x3d","sxd","v2d","vnd","wmf","emf","art","xar","png","webp","jxr","hdp","wdp","cur","ecw",
             "iff","lbm","liff","nrrd","pam","pcx","pgf","sgi","rgb","rgba","bw","int","inta","sid","ras","sun","tga",
             "heic","heif"}

class FOSS_DATE_FORMAT:
    STANDARD = "%Y/%m/%d %H:%M:%S"
    INCOMING_DOTTED_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"
    INCOMING_DOTTED_DATE_FORMAT_SHORTER = "%Y:%m:%d %H:%M"
    INCOMING_DOTTED_DATE_FORMAT_NONPADDED  = "%Y:%m:%d %H:%M:%S"
    INCOMING_HYPHEN_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    #OUTPUT_FOLDER_FORMAT="%Y\\"
    OUTPUT_FOLDER_FORMAT="%Y" + os.path.sep + "%m" + os.path.sep
    INCOMING_HYPHEN_TZ_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'



# from PIL import Image
# from pillow_heif import register_heif_opener
#
# register_heif_opener()
#
#
# im = Image.open(r'D:\temp\2023\12\2023-07-05_12-52-41_021.heic')  # do whatever need with a Pillow image
# exif =  im.getexif()
# for tag, value in exif.items():
#     print(tag, value)

# str = "".join(str(k) + str(v) + "\n"   for k,v in exif.items())
# print(str)
# input = '2023/12/24 18:29:35'
# input = input[0:10]
# fragments = input.split('/')
# year = fragments[0]
# month = fragments[1]
#
# print(year,month, fragments)
#
# import datetime
#
# x = datetime.datetime(1, 1, 1)
# print(x)


import os
import sys
#from PIL import Image
from PIL.ExifTags import TAGS
#from PIL import Image, ExifTags
#
# img = r'D:\foss_backup\1111\11\MorganStanley-Brokrage -5.jpg'
#
# from PIL import Image
# from PIL.ExifTags import TAGS
#
# # open the image
# image = Image.open(img)
#
# # extracting the exif metadata
# exifdata = image.getexif()
#
# # looping through all the tags present in exifdata
# for tagid in exifdata:
#     # getting the tag name instead of tag id
#     #tagname = TAGS.get(tagid, tagid)
#     # passing the tagid to get its respective value
#     value = exifdata.get(tagid)
#     # printing the final result
#     print(f"{tagid:25}: {value}")



try:
    import PIL
    import PIL.Image as PILimage
    from PIL import ImageDraw, ImageFont, ImageEnhance
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError as err:
    exit(err)
def getLesserDateAsCreateDt(file):
    if os.path.getctime(file) < os.path.getmtime(file):
        creation_time = datetime.fromtimestamp(os.path.getctime(file)).strftime(FOSS_DATE_FORMAT.STANDARD)
    else:
        creation_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime(FOSS_DATE_FORMAT.STANDARD)
    return creation_time


def getImageCreateDate( file ):
    file_ext = pathlib.Path(file).suffix.lower()
    #print("incoming file:{}".format(file))
    try:
        #if file_ext.lower() in [".heic",".png"]:
        readMeta = False
        creation_time = ""

        if file_ext.lower() in [".jpeg"]:
            jpgfile = PIL.open(file)
            print(jpgfile.bits, jpgfile.size, jpgfile.format)
        elif file_ext.lower() in [".heic"]:
            register_heif_opener()  ## KM wha t does this do ?
            im = Image.open(file)  # do whatever need with a Pillow image
            exif = im.getexif()
            creation_time = exif[EXIF_IMAGE_DATETIME_TAG_306][:16]
            creation_time = datetime.strptime(creation_time,FOSS_DATE_FORMAT.INCOMING_DOTTED_DATE_FORMAT_SHORTER).strftime( FOSS_DATE_FORMAT.STANDARD)
            readMeta = True
        elif file_ext.lower() in [".jpg"] :
            img = PIL.Image.open(file)
            info = img._getexif()
            if info and EXIF_IMAGE_DATETIME_TAG_36867 in info.keys():
                creation_time = info[EXIF_IMAGE_DATETIME_TAG_36867][:16]
                creation_time = datetime.strptime(creation_time,FOSS_DATE_FORMAT.INCOMING_DOTTED_DATE_FORMAT_SHORTER).strftime(FOSS_DATE_FORMAT.STANDARD)                # print('after creation_time',creation_time)
                readMeta = True
            elif info and EXIF_IMAGE_DATETIME_TAG_306 in info.keys():
                creation_time = info[EXIF_IMAGE_DATETIME_TAG_306][:16]
                # print('before creation_time',creation_time)
                creation_time = datetime.strptime(creation_time,
                                                  FOSS_DATE_FORMAT.INCOMING_DOTTED_DATE_FORMAT_SHORTER).strftime(
                    FOSS_DATE_FORMAT.STANDARD)
                # print('after creation_time',creation_time)
                readMeta = True
        else:
            exif_data = Image.open(file).getexif() #does this work?
            if exif_data and EXIF_IMAGE_DATETIME_TAG_36867 in exif_data.keys():
                creation_time = exif_data[EXIF_IMAGE_DATETIME_TAG_36867][:16]
                #print('before creation_time',creation_time)
                creation_time = datetime.strptime(creation_time,FOSS_DATE_FORMAT.INCOMING_DOTTED_DATE_FORMAT_SHORTER ).strftime(FOSS_DATE_FORMAT.STANDARD)
                #print('after creation_time',creation_time)
                readMeta = True
            elif exif_data and EXIF_IMAGE_DATETIME_TAG_306 in exif_data.keys():
                creation_time = exif_data[EXIF_IMAGE_DATETIME_TAG_306][:16]
                #print('before creation_time',creation_time)
                creation_time = datetime.strptime(creation_time,FOSS_DATE_FORMAT.INCOMING_DOTTED_DATE_FORMAT_SHORTER ).strftime(FOSS_DATE_FORMAT.STANDARD)
                #print('after creation_time',creation_time)
                readMeta = True

        if readMeta == False:
            creation_time = AD_START_TIME
            #logger.warning("Did not find true media capture time for video {}. Taking assumptions as: {} ".format(file,
                                                                                                                  # AD_START_TIME))

    except  Exception as ex:
        #print("Exception on processing file:", file, creation_time, traceback.format_exc())
        #logger.error("Exception on processing file:" + file + "," +  creation_time +", " + traceback.format_exc())
        creation_time = getLesserDateAsCreateDt(file)
    return creation_time


class Worker(object):
    def __init__(self, img):
        self.img = img
        self.get_exif_data()
        self.date =self.get_date_time()
        super(Worker, self).__init__()

    def get_exif_data(self):
        exif_data = {}
        info = self.img._getexif()
        print('info:',info)
        print('info[36867]', info[36867])
        #info[36867]
        if info:
            for tag, value in info.items():
                exif_data[tag] = value
                # decoded = TAGS.get(tag, tag)
                # if decoded == "GPSInfo":
                #     gps_data = {}
                #     for t in value:
                #         sub_decoded = GPSTAGS.get(t, t)
                #         gps_data[sub_decoded] = value[t]
                #
                #     exif_data[decoded] = gps_data
                # else:
                #     exif_data[decoded] = value
        self.exif_data = exif_data
        # return exif_data


    def get_date_time(self):
        if 'DateTime' in self.exif_data:
            date_and_time = self.exif_data['DateTime']
            return date_and_time


# def main():
#     date = image.date
#     print(date)

if __name__ == '__main__':
    try:
        file = r'D:\amazon_photo_download\Amazon Photos Downloads\Pictures\Korou’s IPhone X\2018-10-10_13-56-22_559.jpeg'
        getImageCreateDate(file)
        # img = PILimage.open(file)
        # info = img._getexif()
        # print('info:',info)
        # print(' my info info[36867]:',info[36867])
        # image = Worker(img)
        # meta = image.exif_data()
        # print(meta)

        # date = image.date
        # print(date)

    except Exception as e:
        print(e)