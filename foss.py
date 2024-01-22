#!/usr/bin/env python
#!/usr/bin/env python
#!/usr/bin/env python
# coding: utf-8

import re
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
TRAIL_RUN_MAX = 100


FILE_LOGGER_LEVEL = logging.INFO
CONSOLE_LOGGER_LEVEL = logging.INFO

class Media_Type(Enum):
    PHOTO = 1
    VIDEO = 2
    NON_MEDIA = 9

BACKUP_STATUS_FILENAME = 'backup.status.csv'
QUARANTINE_FILENAME = 'quarantine.status.csv'

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
             "psd","pdd","psp","px","pxm","pxr","qfx","raw","rle","sct","sgi","rgb","int","bw","tga","tiff","tif","vtf",
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
    INCOMING_JUST_HYPHEN_DATE="%Y-%m-%d"
    OUTPUT_FOLDER_FORMAT="%Y" + os.path.sep + "%m" + os.path.sep
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


def get_media_type(file_name):
    file_extension = pathlib.Path(file_name).suffix
    file_extension = file_extension[1:]
    if file_extension.lower() in photo_ext:
        return Media_Type.PHOTO
    elif file_extension.lower() in video_ext:
        return Media_Type.VIDEO
    else:
        return Media_Type.NON_MEDIA


# For each file we will use the CRC32 checksum as part of the file signature. The combination of the crc32 checksum along with the file size in byte should ensure the uniqueness of the file signature.

def crc32(filename, chunksize=65536):
    with open(filename, "rb") as f:
        checksum = 0
        while (chunk := f.read(chunksize)) :
            checksum = zlib.crc32(chunk, checksum)
        return checksum



def get_file_signature(file):
    file_size = os.path.getsize(file)
    crc = crc32(file)
    signature  = str(crc) + '#' + str(file_size)
    #logger.debug("File:" + file  + ", signature:" + signature)
    return signature


# Some of the media file does not have the created time, either they were strip by applications like WhatsApp or IPhone Messanger,
# so, we try to get the last time where the inode was altered or file content was changed and we use the lessor of the two.

def getLesserDateAsCreateDt(file):
    if os.path.getctime(file) < os.path.getmtime(file):
        creation_time = datetime.fromtimestamp(os.path.getctime(file)).strftime(FOSS_DATE_FORMAT.STANDARD)
    else:
        creation_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime(FOSS_DATE_FORMAT.STANDARD)
    return creation_time




def get_file_pattern_from_folder( input_root_dir ):
    if not os.path.exists(input_root_dir):
        #print(input_root_dir , " NOT EXISTS...")
#        logger.error(str(input_root_dir), ":NOT EXISTS...")
        #TODO: we need to throw an error.Test this
        raise Exception("Invalid input folder. Check your path")
        #return input_root_dir
    elif os.path.exists(input_root_dir) and os.path.isfile(input_root_dir):
        #returning the file. In some cases the input might already be the file.
        return input_root_dir
    else:
        return os.path.join(input_root_dir, WILDCARD_FILES_PATTERN)





def get_print_modulator( counter ):
    if counter < 10:
        return 1
    elif counter < 100 :
        return 10
    elif counter < 1000:
        return 100
    elif counter < 5000:
        return 500
    elif counter < 10000:
        return 1000
    else:
        return 1000


#from pillow_heif import register_heif_opener
date_regex = re.compile(r'\d{4}[/.-]\d{2}[/.-]\d{2}')
#date_regex = re.compile(r'\d{4}[/.-]\d{2}[/.-]\d{2}[/._-]\d{2}[/._-]\d{2}[/._-]\d{2}')
def get_createtime_from_filename( filename ):
        match = date_regex.search(filename)
        if match:
            date_from_file = match.group(0)
            date_obj = datetime.strptime(date_from_file, FOSS_DATE_FORMAT.INCOMING_JUST_HYPHEN_DATE)
            creation_time = date_obj.strftime(FOSS_DATE_FORMAT.STANDARD)
            return creation_time
        else:
            return None


def getImageCreateDate( file ):
    file_ext = pathlib.Path(file).suffix.lower()
    #print("incoming file:{}".format(file))
    try:
        #if file_ext.lower() in [".heic",".png"]:
        readMeta = False
        creation_time = ""
        if file_ext.lower() in [".heic"]:
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
            #lets try the new approach using file name
            creation_time =  get_createtime_from_filename(file)
            if creation_time != None:
                logger.warning(
                    "Did not find true media capture time for image {}. Used filename to derive: {} ".format(file,creation_time))
            if creation_time == None :
                creation_time = AD_START_TIME
                quarantine_file.append(file)
                logger.warning("Did not find true media capture time for image {}. Taking assumptions as: {} ".format(file,
                                                                                                                  AD_START_TIME))

    except  Exception as ex:
        #print("Exception on processing file:", file, creation_time, traceback.format_exc())
        logger.error("Exception on processing file:" + file + "," +  creation_time +", " + traceback.format_exc())
        quarantine_file.append(file)
        creation_time = getLesserDateAsCreateDt(file)
    return creation_time

def getVideoCreateDate(file):
    try:
        creation_time = ""
        readMeta  = False
        vid = ffmpeg.probe(file)
        if vid:
                creation_time = vid.get('format',{}).get('tags',{}).get('creation_time',{})
                if creation_time :
                    if pathlib.Path(file).suffix.lower() == '.avi':
                        creation_time = datetime.strptime(creation_time,FOSS_DATE_FORMAT.INCOMING_HYPHEN_DATE_FORMAT).strftime(FOSS_DATE_FORMAT.STANDARD)
                    else:
                        creation_time = datetime.strptime(creation_time, FOSS_DATE_FORMAT.INCOMING_HYPHEN_TZ_DATE_FORMAT ).strftime(FOSS_DATE_FORMAT.STANDARD)
                    readMeta = True

        if readMeta == False:
            # lets try the new approach using file name
            creation_time = get_createtime_from_filename(file)
            if creation_time != None:
                logger.warning(
                    "Did not find true media capture time for image {}. Used filename to derive: {} ".format(file,
                                                                                                             creation_time))
            if creation_time == None:
                creation_time = AD_START_TIME
                quarantine_file.append(file)
                logger.warning(
                    "Did not find true media capture time for image {}. Taking assumptions as: {} ".format(file,
                                                                                                           AD_START_TIME))
    except  Exception as ex:
        #print(traceback.format_exc())
        #print("Exception on processing file:", file,creation_time, traceback.format_exc())
        logger.error("Exception on processing file:" + file + "," + creation_time +"," +  traceback.format_exc())
        quarantine_file.append(file)
        creation_time = getLesserDateAsCreateDt(file)
    return creation_time



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
        #traceback.print_exc(limit=None, file=None, chain=True)



# Gather the file meta data to be written out as a record into the backup status file

# In[13]:


def get_file_metadata(file):
    output = dict()
    #print("Getting metadata for file:{}...".format(file))

    media_type = get_media_type(file)
    creation_time = getLikelyCreateDate(file)
    file_extension = pathlib.Path(file).suffix
    input_file_name = os.path.basename(file)
    file_size = os.path.getsize(file)
    input_dir = os.path.dirname(file)
    signature = get_file_signature(file)

    output['run_id']=RUN_ID
    output['row_id']=  0
    output['media_type']=media_type
    output['input_file_name']=  input_file_name
    output['signature']=  signature
    output['creation_time']=  creation_time
    output['file_size']=  file_size
    output['input_dir']=  input_dir
#     output['input_dir']=  os.path.normpath(input_dir)
    output['file_extension']=  file_extension
    output['creation_time']=  creation_time
    return output


# Create a list of all the files metadata under the root folder
def create_output_files_metadata_list(root_dir):
    logger.info('Invoking create_output_files_metadata_list()...')
    return create_files_metadata_list(root_dir)

def create_input_files_metadata_list(root_dir):
    logger.info('Invoking create_input_files_metadata_list()...')
    return create_files_metadata_list(root_dir)
#Create a list of all the files metadata under the folder
def create_files_metadata_list(root_dir):
        pattern_root_dir = get_file_pattern_from_folder(root_dir)
        tree_metadata = []
        files = glob.glob(pattern_root_dir, recursive = True)
        counter = 0
        files_count = len(files)
        logger.info('Gathering files metadata for directory:{}, that has {} files'.format( root_dir,files_count))
        modulator = get_print_modulator(files_count)
        for file in (files):
            #KM: Take out afterwards
            if TRAIL_RUN and counter > TRAIL_RUN_MAX:
                break

            if os.path.isfile(file):
                file_metadata = get_file_metadata(file)
                counter +=1
                if counter % modulator == 0:
                    logger.info('Metadata for {} of {}, file:{}, signature: {} , creation time: {}'.format(counter, files_count, file,file_metadata['signature'], file_metadata['creation_time']))
                tree_metadata.append(file_metadata)
        return tree_metadata



#Write out the list of file metadata to a file with header
def write_backed_up_file_status_to_file(meta_data_filename, tree_metadata):
    logger.info('Invoking : write_tree_metadata_to_file()')
    if os.path.exists(meta_data_filename):
        with open(meta_data_filename, 'a') as f:
            for media in tree_metadata:
                row = "|".join( str(value) for value in media.values())
                #print(row)
                f.write(row + '\n')

    else:
        first_time = True
        with open(meta_data_filename, 'w') as f:
            for media in tree_metadata:
                if first_time:
                    header = "|".join( str(key) for key in media.keys())
                    #print(header)
                    f.write(header + '\n')
                    first_time = False

                row = "|".join( str(value) for value in media.values())
                #print(row)
                f.write(row + '\n')


def write_quarantine_file():
    logger.info('Invoking : write_quarantine_file()')
    meta_data_filename = os.path.join(output_root_dir, QUARANTINE_FILENAME)
    if os.path.exists(meta_data_filename):
        with open(meta_data_filename, 'a') as f:
            for media in quarantine_file:
                f.write(media + '\n')

    else:
        with open(meta_data_filename, 'w') as f:
            for media in quarantine_file:
                f.write(media + '\n')

#Read a list of file metadata from a file : foss.ini
#BACKUP_STATUS_FILENAME : backup_status_file
def read_backup_status_metadata_from_file(backup_status_file):
    with open(backup_status_file, 'r') as f:
        header = f.readline()
        tree_metadata =[]
        for line in f:
            media = {}
            for key, value in zip(header.split('|'), line.split('|')):
                media[key.strip()] = value.strip()
            tree_metadata.append(media)
    return tree_metadata


#Create a map of signature:list of files metadata  from a list of file metadata
def create_file_metadata_map(file_metadata_list):
    file_metadata_map = defaultdict(int)
    tree_metadata_count = len(file_metadata_list)
    modulator = get_print_modulator(tree_metadata_count)
    for file_metadata in file_metadata_list:
        signature = file_metadata.get('signature')
        input_file_name = file_metadata.get('input_file_name')
        file_metadata_map[signature] = file_metadata

    # if len(file_metadata_list) > len(tree_metadata_map):
    #     #print("Number of file on the folder:{}, Number of files on the hashmap:{}".format(len(file_metadata_list), len(tree_metadata_map)))
    #     logger.info("Number of file on the folder:{}, Number of files on the hashmap:{}".format(len(file_metadata_list), len(tree_metadata_map)))
    #     #print('Number of duplicates files detected:{}'.format(len(file_metadata_list) - len(tree_metadata_map)))
    #     logger.info('Number of duplicates files detected:{}'.format(len(file_metadata_list) - len(tree_metadata_map)))
    return file_metadata_map



def create_prior_backup_metadata_map(output_root_dir):
    prior_backup_status_file = os.path.join(output_root_dir, BACKUP_STATUS_FILENAME)
    local_start_time =  datetime.now()
    logger.info('Reading prior backup status file:' + str(prior_backup_status_file))
    if os.path.exists(prior_backup_status_file):
        # print('status_file:',prior_backup_status_file)
        prior_backup_metadata_list = read_backup_status_metadata_from_file(prior_backup_status_file)
        logger.info('Number of files in the the prior backup status file:' + str(len(prior_backup_metadata_list)))
        prior_backup_metadata_map = create_file_metadata_map(prior_backup_metadata_list)
    else:
        prior_backup_metadata_map = create_file_metadata_map(create_output_files_metadata_list(output_root_dir))
        logger.info('NO PRIOR BACKUP STATUS FILE. Number of files from the backup folder:' + str(
            len(prior_backup_metadata_map)))

    delta = datetime.now() - local_start_time
    logger.info('Time taken to read  create_prior_backup_metadata_map:{}'.format( delta))
    return prior_backup_metadata_map

def create_input_folder_medata_map(input_root_dir):
    logger.info('create_input_folder_medata_map():' + str(input_root_dir))
    return create_file_metadata_map(create_files_metadata_list(input_root_dir))

def find_new_files_metadata_dict( input_root_dir,output_root_dir ):
    logger.info("Invoking : find_new_files()")
    prior_backup_metadata_map = create_prior_backup_metadata_map(output_root_dir)
    input_tree_medata_map = create_input_folder_medata_map(input_root_dir)
    output_keys = set(prior_backup_metadata_map.keys())
    input_keys = set(input_tree_medata_map.keys())
    logger.info("len(output_keys):" + str(len(output_keys)))
    logger.info("len(input_keys):" + str(len(input_keys)))
    to_be_copied_keys = input_keys.difference(output_keys)
    logger.info('Number of new files to be copied:' + str(len(to_be_copied_keys)))
    return dict((k, input_tree_medata_map[k]) for k in to_be_copied_keys if k in input_tree_medata_map)


def copy_files(to_copy_map, output_dir ):
    copied_files_metadata = []
    counter = 0
    files_to_copy_count = len(to_copy_map)
    logger.info('Total number of files to copy:{}'.format(files_to_copy_count))

    counter = 0
    modulator = get_print_modulator(files_to_copy_count)


    for signature, file_metadata in  (to_copy_map.items()):

        if TRAIL_RUN and counter > TRAIL_RUN_MAX:
            break

        input_file = os.path.join(file_metadata.get('input_dir'), file_metadata.get('input_file_name'))
        try:
            date_string = file_metadata.get('creation_time')
            file_date = dateutil.parser.parse(date_string)
            year = file_date.strftime(FOSS_DATE_FORMAT.OUTPUT_FOLDER_FORMAT)
            #KM: New
            year_month_date_list = date_string[0:10].split('/')
        except Exception as ex:
            print("Exception happened on file_metadata:{} and the stack trace:\n{}".format(file_metadata,traceback.format_exc()))
            print("Using file_metadata.get('creation_time')[:4]", file_metadata.get('creation_time')[:4] )
            year = file_metadata.get('creation_time')[:4]
        output_folder = output_dir +  year
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        #To take care if the the same file name already exists
        output_file = os.path.join(output_folder , file_metadata.get('input_file_name'))
        if  os.path.exists(output_file):
            new_output_file = os.path.join(output_folder , (signature + "_"  + file_metadata.get('input_file_name')))
            logger.debug("Output file names clash for {},{} renaming as {}"
                  .format(
                      file_metadata.get('input_dir'),
                      file_metadata.get('input_file_name'),
                      new_output_file )
                 )
            shutil.copy2(input_file, new_output_file)
        else:
            shutil.copy2(input_file, output_folder)

        counter+=1
        if counter % modulator == 0:
            logger.info('Copied {} of {}, file:{} to {}'.format(counter,files_to_copy_count, input_file,output_folder ))

        file_metadata['row_id']=  counter
        file_metadata['output_folder'] = os.path.normpath(output_folder)

        #KM: Added
        file_metadata['year'] = year_month_date_list[0]
        file_metadata['month'] = year_month_date_list[1]
        file_metadata['day'] = year_month_date_list[2]

        file_metadata['output_filename'] = file_metadata.get('input_file_name')
        file_metadata['active_flag']=  'Y'
        file_metadata['status']=  'Copied'
        file_metadata['create_dt']= datetime.now()
        file_metadata['create_user_id']= os.getlogin()
        file_metadata['update_dt']= datetime.now()
        file_metadata['update_user_id']= os.getlogin()

        copied_files_metadata.append(file_metadata)

    return copied_files_metadata


def get_hours_minutes_seconds(td):
    return int(td.total_seconds()/3600), int(td.total_seconds()/60), int(td.seconds)

logger = setup_custom_logger("foss")

def process(input_root_dir,output_root_dir ):
    logger.info("Invoking process() : Input folder:" +  str(input_root_dir) + ", Output folder:" + str(output_root_dir) + ")")
    start_time = datetime.now()
    foss_backup_status_filename = os.path.join(output_root_dir, BACKUP_STATUS_FILENAME)
    to_copy_map = find_new_files_metadata_dict(input_root_dir , output_root_dir)
    if ( len(to_copy_map) != 0 ):
        copied_files_metadata = copy_files(to_copy_map,output_root_dir)
        write_backed_up_file_status_to_file(foss_backup_status_filename, copied_files_metadata)
    delta = datetime.now() - start_time
    write_quarantine_file()
    logger.info('Backup audit file:{}, total time taken for the run in {}'.format(foss_backup_status_filename, delta))

logger.info('****** JOB STARTED... ******')
RUN_ID = round((datetime.now() - datetime(2023, 1, 1)).total_seconds() / RUN_ID_PROMOTER )
quarantine_file = []
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\Backup\\'
#Done 12/28/2023
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\my_vista\\'
#Done 12/28/2023
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\Pictures\\'

#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\Pictures\\'
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\2016-08-07\\'
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\greece\\'

#For temp testing
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\Backup\XPS\D\amazon_drive\Amazon Photos Downloads\my_vista\my_doc\korou\download\IMG_0943-1.png'
#input_root_dir = r'D:\foss_backup\1111\11\MorganStanley-Brokrage -5.jpg'
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\Backup\XPS\D\amazon_drive\Amazon Photos Downloads\my_vista\my_pic\2007\07_july\4_july_fireworks\MVI_9747.avi'

#input_root_dir = r'D:\foss_backup\1111\01\2016-08-08_160407000_B6F08_iOS.png'
#input_root_dir = r'D:\amazon_photo_download\\'
#input_root_dir = r'D:\amazon_photo_download\Amazon Photos Downloads\greece\\'
input_root_dir = r'G:\photo_backup_before20051015\\'
output_root_dir =r'E:/foss_backup/'

# #Final destination
# input_root_dir = r'D:\amazon_photo_download\\'
# #Done on 1/4/2024
# input_root_dir = r'E:\foss_backup\1111\1\\'
# output_root_dir =r'E:/foss_backup/'

process(input_root_dir,output_root_dir)

#logger.info('List of files where we copied into quarantine folder:\n' + "\n".join(str(x) for x in quarantine_file))
logger.info("Completed process() : Input folder:" +  str(input_root_dir) + ", Output folder:" + str(output_root_dir) + ")")
logger.info('****** JOB COMPLETED. ******\n')
