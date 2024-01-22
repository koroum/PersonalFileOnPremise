import uuid

# printing the value of unique MAC
# address using uuid and getnode() function
# print(hex(uuid.getnode()))
#
#
# print ("The MAC address in formatted way is : ", end="")
# print (':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
# for ele in range(0,8*6,8)][::-1]))

import wmi
c = wmi.WMI()
for item in c.Win32_PhysicalMedia():
    print(item)

# import wmi
#
# c = wmi.WMI()
# drive_letter = "D:"
# for physical_disk in c.Win32_DiskDrive():
#     for partition in physical_disk.associators("Win32_DiskDriveToDiskPartition"):
#         for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
#             if logical_disk.Caption == drive_letter:
#                 print(physical_disk.Caption, partition.Caption, logical_disk.Caption)