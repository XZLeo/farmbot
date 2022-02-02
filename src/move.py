'''
Author: Ziliang Xiong
This script is for all the functions that drive Farmbot to Move, including:
1. Taking Photos 2. Move to an assigned point (x, y, z)
3. Sweep the planting bed 4. Grip a target
Note: it is for remote server, can ben replaced by a local script
'''
from argparse import ArgumentParser
from logging import getLogger
from os import path, makedirs, system
from time  import sleep, strftime, time
#from serial import Serial, PARITY_NONE, STOPBITS_ONE, EIGHTBITS 
from requests.api import delete
from typing import List
from pathlib import Path
from logging import basicConfig, DEBUG, INFO, error, getLogger
from urllib import request

from datetime import timezone, datetime
from dateutil.parser import parse
from requests import get, delete

import creds
from client import FarmbotClient


_SWEEEP_HEIGHT = 0

Logger = getLogger(__name__)

class Opts:
    def __init__(self, min_x, max_x, min_y, max_y, delta, offset, flag):
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self.delta = delta
        self.offset = offset
        self.flag = flag
    

def scan(img_path: Path, location_path: Path, # smaller delta
         min_x=0, max_x=1300, min_y=0, max_y=1000, delta=1000, offset=0, flag=True) -> List: #里面的数字需要重新测量
    '''
    scan the bed at a certain height, first move along x axis, then y, like a zig zag;
    Taking pictures and record the location of the camera that corresponds to the picture
    The default value of x, y should be from the measurement of Farmbot
    Input: min_x: left most point on x axis
           max_x: right most point on x axis
           min_y: front most point on y axis
           max_y: back most point on y axis
           delta: the interval for scaning
           offset:
           flag: for degging, if true, don't actually drive FarmBot
    Output: none
    '''
    opts = Opts(min_x, max_x, min_y, max_y, delta, offset, flag)

    pts = []
    sweep_y_negative = False
    for x in range(opts.min_x, opts.max_x, opts.delta):
        y_range = range(opts.min_y, opts.max_y, opts.delta)
        if sweep_y_negative:
            y_range = reversed(y_range)
        sweep_y_negative = not sweep_y_negative
        for y in y_range:
            pts.append((x+opts.offset, y+opts.offset))

    Logger.info('Moving pattern generated')

    if opts.flag:
        Logger.info('Run without sweep')
        exit()

    client = FarmbotClient(creds.device_id, creds.token)
    client.move(0, 0, _SWEEEP_HEIGHT) # ensure moving from original 
    for x, y in pts:
        client.move(x, y, _SWEEEP_HEIGHT) # move camera
        take_photo(img_path)
    client.shutdown()
    # write to img/location
    with open(path.join(location_path, "location.txt"), 'w') as f:
        for postion in pts:
            f.write('{} {} {}\n'.format(postion[0], postion[1], _SWEEEP_HEIGHT))
    return None 


def take_photo(img_path: Path):
    HERE = path.dirname(__file__)
    IMG_DIR = path.join(HERE, img_path)

    with request.urlopen('http://localhost:8080/?action=snapshot') as photo:
        filename = datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + ".jpg"
        with open(path.join(IMG_DIR, filename), mode="wb") as save_file:
            save_file.write(photo.read())


def simple_move(x: int, y: int, z: int) -> None: 
    '''
    Move to a place, if flag is true, take a picture
    Input: x, y,z: destination point
           photo: take a pic or not
    '''
    client = FarmbotClient(creds.device_id, creds.token)
    client.move(x, y, z)  
    client.shutdown()
    return None


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '-m',
        '--mode',
        type=int,
        help='Mode for FarmBot, 1 for simple move with an assigned detination, 2 for scaning' 
    )
    parser.add_argument(
        '-l',
        '--log',
        type=Path,
        default='../log/move.log',
        help='Path to the log file'
    )
    parser.add_argument(
        '-p',
        '--photo',
        type=Path,
        default="../img",
        help='Mode for FarmBot, 1 for simple move with an assigned detination, 2 for scaning' 
    )
    parser.add_argument(
        '-loc',
        '--locations',
        type=Path,
        default='../img/locations/',
        help='the path to txt files contains locations from encoders corresponds to each photo'
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode')
    arguments = parser.parse_args()
    

    if arguments.mode == 1:
        Logger.info('Input the destination:')
        destination_x = int(input('X:'))
        destination_y = int(input('Y:'))
        destination_z = int(input('Z:'))
        photo = True if input('Take a photo or not?[Y/N]:') == 'Y' else False 
        simple_move_start = time()
        simple_move(destination_x, destination_y, destination_z, photo)
        Logger.info(f'time cost {time()-simple_move_start}')
    elif arguments.mode == 2:
        scan(arguments.photo, arguments.locations, flag=False)
    else:
        Logger.error('Wrong mode number {arguments.mode}')


