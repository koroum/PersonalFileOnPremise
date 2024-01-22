import os

def get_directory_size(path):
    #print('path:', path)
    my_files  = os.listdir(path)

    total_size = 0
    #files = [f for f in os.listdir(path) if os.path.isfile(f)]
    #for dirpath, dirnames, filenames in os.walk(path):
    for filename in my_files:
        file_path = os.path.join(path, filename)
        #print('file_path:{}'.format(file_path))
        file_size = os.path.getsize(file_path)
        total_size += file_size
        files_and_sizes.append(('file',file_path, file_size))

    #print('my_files:{}, total size:{}'.format(my_files, total_size))
    return total_size



def get_subdirectory_sizes(root_directory):
    subdirectory_sizes = []

    for dirpath, dirnames, filenames  in os.walk(root_directory):
#        print('dirpath:{} , dirname{}, filenames:{}'.format(dirpath, dirnames , filenames ))
        if dirpath != root_directory:
            #directory_name = os.path.basename(dirpath)
            size = get_directory_size(dirpath)
            subdirectory_sizes.append(('dir',(dirpath), size))
        #     #test_subdirectory_sizes.append((directory_name, size))

    return subdirectory_sizes

def main():

    root_directory = r'D:\temp'  # Replace with the root directory you want to start from
    subdirectory_sizes = get_subdirectory_sizes(root_directory)

    # Sort the subdirectories by size
    #sorted_subdirectories = subdirectory_sizes.sort( key=lambda x: x[2], reverse=True)

    for  tup in subdirectory_sizes:
        print("Directory:{}, Size:{} ".format( tup[1], tup[2] ))

    #print('files_and_sizes:',files_and_sizes)
    for tup in files_and_sizes:
        print('file:{}, size:{}'.format(tup[1],tup[2]))

files_and_sizes = []
if __name__ == "__main__":
    main()


