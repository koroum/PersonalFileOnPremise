#Check if the file name pattern matches
# yyyy-MM-dd-*
import glob
import re
from datetime import datetime

files = glob.glob(r'D:\foss_backup\1111\11\\**.*', recursive=True)
date_regex = re.compile(r'\d{4}[/.-]\d{2}[/.-]\d{2}')
#date_regex = re.compile(r'\d{4}[/.-]\d{2}[/.-]\d{2}[/._-]\d{2}[/._-]\d{2}[/._-]\d{2}')
#date_regex = re.compile(r'\d{4}[-]\d{2}[-]\d{2}')

STANDARD = "%Y/%m/%d %H:%M:%S"
matching = []
unmatch = []
for file in files:
    print(file)
    match = date_regex.search(file)

    if match:
        print('Matching found', file, match)
        date_from_file = match.group(0)
        print("matching pattern:", date_from_file)
        date_obj = datetime.strptime(date_from_file, "%Y-%m-%d")
        creation_time = date_obj.strftime(STANDARD)
        print("Create time:" , creation_time)
        matching.append(file)
    else:
        unmatch.append(file)

#print(matching)
#print(matching)
print('Match count:', str(len(matching)))
print('Unmatch count:',str(len(unmatch)))


