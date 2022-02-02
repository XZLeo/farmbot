from os import listdir, remove
from os.path import join
from pathlib import Path

def remove_temp(path: Path)-> None:
    # list file
    for filename in listdir(path):
        file =Path(join(path, filename))
        if file.is_file():
            remove(file)
    return

path = '../img'
remove_temp(path)