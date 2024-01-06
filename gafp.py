#!/usr/bin/env python
# !/usr/bin/env python
# coding: utf-8

import datetime
import glob
import logging
import os
import os.path
import pathlib
import shutil
import zlib
import dateutil.parser
import ffmpeg
import sys, traceback
#import panda as pd
from collections import defaultdict
from datetime import datetime
from enum import Enum
from PIL import Image


class Media_Type(Enum):
    PHOTO = 1
    VIDEO = 2
    NON_MEDIA = 9


FILE_LOGGER_LEVEL = logging.DEBUG
CONSOLE_LOGGER_LEVEL = logging.DEBUG

FILES_ATTRIBUTE_NAME = 'files.attribute.csv'

CHUNK_SIZE = 65536
PROGRESS_COUNTER = 100
RUN_ID = 0
RUN_ID_PROMOTER = 20

EXIF_IMAGE_DATETIME_ORIGINAL = 36867
EXIF_IMAGE_DATETIME = 306

WILDCARD_FILES_PATTERN = r'**/*.*'
WILDCARD_DIR_PATTERN = r'**'

video_ext = {"webm", "mkv", "flv", "flv", "vob", "ogv", "ogg", "drc", "gif", "gifv", "mng", "avi", "MTS", "M2TS", "TS",
             "mov", "qt", "wmv",
             "yuv", "rm", "rmvb", "viv", "asf", "amv", "mp4", "m4p", "m4v", "mpg", "mp2", "mpeg", "mpe", "mpv", "mpg",
             "mpeg", "m2v", "m4v",
             "svi", "3gp", "3g2", "mxf", "roq", "nsv", "flv ", "f4v ", "f4p ", "f4a ", "f4b"}
photo_ext = {"ase", "art", "bmp", "blp", "cd5", "cit", "cpt", "cr2", "cut", "dds", "dib", "djvu", "egt", "exif", "gif",
             "gpl",
             "grf", "icns", "ico", "iff", "jng", "jpeg", "jpg", "jfif", "jp2", "jps", "lbm", "max", "miff", "mng",
             "msp", "nef", "nitf",
             "ota", "pbm", "pc1", "pc2", "pc3", "pcf", "pcx", "pdn", "pgm", "PI1", "PI2", "PI3", "pict", "pct", "pnm",
             "pns", "ppm", "psb",
             "psd", "pdd", "psp", "px", "pxm", "pxr", "qfx", "raw", "rle", "sct", "sgi", "rgb", "int"

    , "bw", "tga", "tiff", "tif", "vtf",
             "xbm", "xcf", "xpm", "3dv", "amf", "ai", "awg", "cgm", "cdr", "cmx", "dxf", "e2d", "egt", "eps", "fs",
             "gbr", "odg", "svg",
             "stl", "vrml", "x3d", "sxd", "v2d", "vnd", "wmf", "emf", "art", "xar", "png", "webp", "jxr", "hdp", "wdp",
             "cur", "ecw",
             "iff", "lbm", "liff", "nrrd", "pam", "pcx", "pgf", "sgi", "rgb", "rgba", "bw", "int", "inta", "sid", "ras",
             "sun", "tga",
             "heic", "heif"}


class GAFP_DATE_FORMAT:
    STANDARD = "%Y/%m/%d %H:%M:%S"
    INCOMING_DOTTED_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"
    INCOMING_DOTTED_DATE_FORMAT_SHORTER = "%Y:%m:%d %H:%M"
    INCOMING_DOTTED_DATE_FORMAT_NONPADDED = "%Y:%m:%d %H:%M:%S"
    INCOMING_HYPHEN_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    # OUTPUT_FOLDER_FORMAT="%Y\\"
    OUTPUT_FOLDER_FORMAT = "%Y" + os.path.sep + "%m" + os.path.sep
    INCOMING_HYPHEN_TZ_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'


def setup_custom_logger(name):
    # create logger with 'spam_application'
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(name + '.log')
    fh.setLevel(FILE_LOGGER_LEVEL)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(CONSOLE_LOGGER_LEVEL)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def crc32(filename, chunksize=65536):
    with open(filename, "rb") as f:
        checksum = 0
        while (chunk := f.read(chunksize)):
            checksum = zlib.crc32(chunk, checksum)
        return checksum


def get_file_signature(file):
    file_size = os.path.getsize(file)
    crc = crc32(file)
    signature = str(crc) + '#' + str(file_size)
    # logger.debug("File:" + file  + ", signature:" + signature)
    return signature



def getLesserDateAsCreateDt(file):
    if os.path.getctime(file) < os.path.getmtime(file):
        creation_time = datetime.fromtimestamp(os.path.getctime(file)).strftime(GAFP_DATE_FORMAT.STANDARD)
    else:
        creation_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime(GAFP_DATE_FORMAT.STANDARD)
    return creation_time



def get_file_pattern_from_folder(input_root_dir):
    if not os.path.exists(input_root_dir):
        # print(input_root_dir , " NOT EXISTS...")
        #        logger.error(str(input_root_dir), ":NOT EXISTS...")
        # TODO: we need to throw an error.Test this
        raise Exception("Invalid input folder. Check your path")
        # return input_root_dir
    else:
        return os.path.join(input_root_dir, WILDCARD_FILES_PATTERN)




def get_print_modulator(counter):
    if counter < 10:
        return 1
    elif counter < 100:
        return 10
    elif counter > 1000:
        return 100
    elif counter > 5000:
        return 500
    elif counter > 10000:
        return 1000
    else:
        return 1000


def getImageCreateDate(file):
    file_ext = pathlib.Path(file).suffix.lower()
    # print("incoming file:{}".format(file))
    try:
        if file_ext.lower() in [".heic", ".png"]:
            creation_time = getLesserDateAsCreateDt(file)
        else:
            creation_time = ""
            exif_data = Image.open(file).getexif()  # does this work?
            if exif_data and 36867 in exif_data.keys():
                creation_time = exif_data[EXIF_IMAGE_DATETIME_ORIGINAL][:16]
                # print('before creation_time',creation_time)
                creation_time = datetime.strptime(creation_time,
                                                  GAFP_DATE_FORMAT.INCOMING_DOTTED_DATE_FORMAT_SHORTER).strftime(
                    GAFP_DATE_FORMAT.STANDARD)
                # print('after creation_time',creation_time)
            elif exif_data and 306 in exif_data.keys():
                creation_time = exif_data[EXIF_IMAGE_DATETIME][:16]
                # print('before creation_time',creation_time)
                creation_time = datetime.strptime(creation_time,
                                                  GAFP_DATE_FORMAT.INCOMING_DOTTED_DATE_FORMAT_SHORTER).strftime(
                    GAFP_DATE_FORMAT.STANDARD)
                # print('after creation_time',creation_time)
            else:
                creation_time = getLesserDateAsCreateDt(file)
    except  Exception as ex:
        # print("Exception on processing file:", file, creation_time, traceback.format_exc())
        logger.error("Exception on processing file:", file, creation_time, traceback.format_exc())
        creation_time = getLesserDateAsCreateDt(file)
    return creation_time


def getVideoCreateDate(file):
    try:
        creation_time = ""
        vid = ffmpeg.probe(file)
        if vid:
            if pathlib.Path(file).suffix.lower() in ['.mp4', '.mov']:
                creation_time = vid.get('format', {}).get('tags', {}).get('creation_time', {})
                if creation_time:
                    creation_time = datetime.strptime(creation_time,
                                                      GAFP_DATE_FORMAT.INCOMING_HYPHEN_TZ_DATE_FORMAT).strftime(
                        GAFP_DATE_FORMAT.STANDARD)
                else:
                    creation_time = getLesserDateAsCreateDt(file)

            else:
                creation_time = vid.get('format', {}).get('tags', {}).get('creation_time', {})
                # Could have some problem here other movie type
                if not creation_time:
                    creation_time = getLesserDateAsCreateDt(file)
        else:
            # pathlib.Path(file).suffix.lower() == '.mpg':
            creation_time = vid.get('format', {}).get('tags', {}).get('creation_time', {})
            if not creation_time:
                creation_time = getLesserDateAsCreateDt(file)
    except  Exception as ex:
        # print(traceback.format_exc())
        # print("Exception on processing file:", file,creation_time, traceback.format_exc())
        logger.error("Exception on processing file:", file, creation_time, traceback.format_exc())
        creation_time = getLesserDateAsCreateDt(file)
    return creation_time


def get_media_type(file_name):
    file_extension = pathlib.Path(file_name).suffix
    file_extension = file_extension[1:]
    if file_extension.lower() in photo_ext:
        return Media_Type.PHOTO
    elif file_extension.lower() in video_ext:
        return Media_Type.VIDEO
    else:
        return Media_Type.NON_MEDIA


def getLikelyCreateDate(file):
    media_type = get_media_type(file)
    try:
        media_type = get_media_type(file)
        if media_type == Media_Type.PHOTO:
            creation_time = getImageCreateDate(file)
        elif media_type == Media_Type.VIDEO:
            creation_time = getVideoCreateDate(file)
        else:
            creation_time = getLesserDateAsCreateDt(file)
        return creation_time

    except Exception as ex:
        print('Exception:', ex, '\nFile:', file)
        print(traceback.format_exc())
        # traceback.print_exc(limit=None, file=None, chain=True)




def get_file_metadata(file, counter):
    output = dict()
    # print("Getting metadata for file:{}...".format(file))

    media_type = get_media_type(file)
    creation_time = getLikelyCreateDate(file)
    file_extension = pathlib.Path(file).suffix
    input_file_name = os.path.basename(file)
    file_size = os.path.getsize(file)
    input_dir = os.path.dirname(file)
    signature = get_file_signature(file)

    output['run_id'] = RUN_ID
    output['row_id'] = counter
    output['media_type'] = media_type
    output['input_file_name'] = input_file_name
    output['signature'] = signature
    output['creation_time'] = creation_time
    output['file_size'] = file_size
    output['input_dir'] = input_dir
    #     output['input_dir']=  os.path.normpath(input_dir)
    output['file_extension'] = file_extension
    output['creation_time'] = creation_time
    output['file_type'] = 'File'
    return output


def get_dir_metadata(file, counter):
    output = dict()
    # print("Getting metadata for file:{}...".format(file))

    media_type = ""
    creation_time = getLikelyCreateDate(file)
    file_extension = ""
    input_file_name = os.path.basename(file)
    file_size = os.path.getsize(file)
    input_dir = os.path.dirname(file)
    signature = ""

    output['run_id'] = RUN_ID
    output['row_id'] = counter
    output['media_type'] = media_type
    output['input_file_name'] = input_file_name
    output['signature'] = signature
    output['creation_time'] = creation_time
    output['file_size'] = file_size
    output['input_dir'] = input_dir
    #     output['input_dir']=  os.path.normpath(input_dir)
    output['file_extension'] = file_extension
    output['creation_time'] = creation_time
    output['file_type'] = 'Directory'
    return output



def create_files_metadata_list(root_dir):
    pattern_root_dir = os.path.join(root_dir, WILDCARD_FILES_PATTERN)
    tree_metadata = []
    files = glob.glob(pattern_root_dir, recursive=True)
    counter = 0
    files_count = len(files)
    logger.info('Gathering files metadata for directory:{}, that has {} files'.format(root_dir, files_count))
    modulator = get_print_modulator(files_count)
    for file in (files):
        if os.path.isfile(file):
            file_metadata = get_file_metadata(file, counter)
            counter += 1
            if counter % modulator == 0:
                logger.debug(
                    'Metadata for {} of {}, file:{}:{}'.format(counter, files_count, file, file_metadata['signature']))
            tree_metadata.append(file_metadata)

    return tree_metadata


def write_backed_up_file_status_to_file(meta_data_filename, files_metadata):
    logger.info('Invoking : write_tree_metadata_to_file()')
    logger.debug(files_metadata)
    first_time = True
    with open(meta_data_filename, 'w') as f:
        for file_metadata in files_metadata:
            if first_time:
                header = "|".join(str(key) for key in file_metadata.keys())
                # print(header)
                f.write(header + '\n')
                first_time = False

            row = "|".join(str(value) for value in file_metadata.values())
            # print(row)
            f.write(row + '\n')




def get_hours_minutes_seconds(td):
    return int(td.total_seconds() / 3600), int(td.total_seconds() / 60), int(td.seconds)


logger = setup_custom_logger("gafp")

# Final run
# input_root_dir ="D:\\Ruby Iphone\\103APPLE\\**"

def process(input_root_dir, output_root_dir):
    logger.info("Invoking process() : Input folder:" + str(input_root_dir))
    start_time = datetime.now()
    gafp_status_filename = os.path.join(output_root_dir, FILES_ATTRIBUTE_NAME)
    files_metadata_list = create_files_metadata_list(input_root_dir)
    if (len(files_metadata_list) != 0):
        write_backed_up_file_status_to_file(gafp_status_filename, files_metadata_list)

    delta = datetime.now() - start_time
    logger.info('Files meta data scan:{}, total time taken for the run in {}'.format(gafp_status_filename, delta))


logger.info('****** JOB STARTED... ******')
RUN_ID = round((datetime.now() - datetime(2023, 1, 1)).total_seconds() / RUN_ID_PROMOTER)

# input_root_dir = r'D:\Korou IPhone X\IMG_3914.JPG'
# input_root_dir = r'D:\my_xps\my_vista\my_pic\2012\07\Jul 20, 2012\IMG_3914.JPG'
# input_root_dir = r'D:\my_xps\my_vista\my_pic\2012\07'
# input_root_dir = r'D:\amazon_drive\Amazon Photos Downloads\my_vista\my_pic\2012\07\Jul 20, 2012\IMG_3914.JPG'
# input_root_dir = r'D:\my_xps\my_vista\my_pic\2012\**\*.*'
# input_root_dir ="D:\\Ruby Iphone\\"
# input_root_dir =r"D:\my_xps\**\*.*"
# input_root_dir =r'D:/my_xps/Dropbox/d_doc/atiya/'
# input_root_dir =r'D:/Korou IPhone 6/'
# input_root_dir =r'D:/02_Ruby_Iphone/'

# input_root_dir ='z:\\test\\atiya_chagumba\\'
# input_root_dir =r'D:/amazon_photo_download/'
# input_root_dir ='D:\\amazon_photo_download\\Amazon Photos Downloads\\Backup\\XPS\\D\\amazon_drive\\Amazon Photos Downloads\\Pictures\\Korou\'s iPhone\\'
#input_root_dir = r'D:\\my_xps\\my_vista\\my_pic\\2012\\08'
# input_root_dir = r'D:\my_xps\my_vista\my_pic\\'
# input_root_dir = r'D:\my_xps\my_vista\\'
# input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\Backup\XPS\D\amazon_drive\Amazon Photos Downloads\2016-08-07\\'
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\2016-08-07\\'
#input_root_dir = r'E:\foss_backup\\'

input_root_dir = r'E:\foss_backup\\'

output_root_dir = r'D:/temp/'
process(input_root_dir, output_root_dir)
logger.info('****** JOB COMPLETED. ******\n')

# files = glob.glob('d:/temp/**/', recursive=True)
# for file in files:
#     print(file)
#     dir_metadata = get_dir_metadata(file,0)
#     print(dir_metadata)
# ['temp/', 'temp/dir/', 'temp/dir/sub_dir1/', 'temp/dir/sub_dir2/']