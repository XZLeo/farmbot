'''
Author: Ziliang
The main script of the project, it calls scripts for movement, detection, and coordinate calculation.

'''
from argparse import ArgumentParser, Namespace
from logging import StringTemplateStyle
from os import listdir, remove
from os.path import join
from pathlib import Path
from typing import Tuple
from numpy import sqrt
from pandas import DataFrame
from gripper import gripper_close, gripper_open

from move import *
from detect import *
from location import *

_LOG = getLogger(__name__)

GRIP_Z = 468 # measure!
SCAN_Z = 0
ORIGIN_X = 0
ORIGIN_Y = 0
ORIGIN_Z = 0

def remove_overlap(table_coordinate:DataFrame, tolerance=50.00)->DataFrame:
    '''
    compare every two coordinates, if their Euclidean distance is smaller than tolerance
    , delete the one with lower probability

    Choose a reasonable tolerance!!
    :param table_coordinate: pandas dataframe that each row corresponds to a target [class, x, y, confidence]
    :param tolerance: a distance threshold
    '''
    num_coordinates, num_col = table_coordinate.shape
    for i in range(num_coordinates-1):
        x, y, confidence = table_coordinate.loc[i, ['x','y', 'confidence']]
        for j in range(i+1, num_coordinates):
                x_j, y_j, confidence_j = table_coordinate.loc[j, ['x','y', 'confidence']]
                distance = sqrt((float(x)-float(x_j))*(float(x)-float(x_j)) + (float(y)-float(y_j))*(float(y)-float(y_j)))  
                if distance <= tolerance:
                    if confidence < confidence_j:
                        table_coordinate.drop(i)
                    else:
                        table_coordinate.drop(j)
    return table_coordinate              



def remove_temp(path: Path)-> None:
    '''
    Clean temporary files, i.e., photos, location.txt, annotations
    '''
    for filename in listdir(path):
        file =Path(join(path, filename))
        if file.is_file():
            remove(file)
    return


def main(args: Namespace):
    # clean temporary files
    remove_temp(args.input)
    remove_temp(args.locations)
    remove_temp(args.annotations)
    # start from the origin
    simple_move(ORIGIN_X, ORIGIN_Y, ORIGIN_Z)
    _LOG.info("Go back to the origin")
    # scan
    scan(args.photo, args.locations, flag=False)
    _LOG.info("Scan the planting bed")
    # detect
    detect(args)
    _LOG.info("Detection is done")
    # calculate locations
    list_global_coordinate = cal_location(args)
    _LOG.info("Global coordinate calculation is done.")
    # choose class
    table_global_coordinate = DataFrame(list_global_coordinate, columns=['class', 'x', 'y', 'confidence'])
    # remove overlap
    print(table_global_coordinate)
    table_global_coordinate = remove_overlap(table_global_coordinate)
    goal_class = table_global_coordinate[table_global_coordinate['class']==args.category]
    _LOG.info("Choose {}".format(args.category))
    # if there is no desiered class of plants
    if goal_class.empty:
        _LOG.info("There is no {}".format(args.category))
    # move and grip
    num_goals, num_col = goal_class.shape
    for i in range(num_goals):
        x, y = goal_class.loc[i, ['x','y']]
        simple_move(x, y, GRIP_Z, False)
        open()
        gripper_open() # to make sure the gripper is open before gripping
        gripper_close()
        # go back to the orgin
        simple_move(x, y, GRIP_Z, False)
        gripper_open()
    return


    

if __name__ == '__main__':
    parser = ArgumentParser(description="YOLOv3 detection on Farmbot")
    # parsers for move
    parser.add_argument(
        '-p',
        '--photo',
        type=Path,
        default="../img",
        help='Mode for FarmBot, 1 for simple move with an assigned detination, 2 for scaning' 
    )
    # parsers for detect
    parser.add_argument("--input", type=str, default="../img",
                        help="image source. It can be a single image, a"
                        "txt with paths to them, or a folder. Image valid"
                        " formats are jpg, jpeg or png."
                        "If no input is given, ")
    parser.add_argument("--batch_size", default=1, type=int,
                        help="number of images to be processed at the same time")
    parser.add_argument("--weights", default="../weights/yolov3-vattenhallen_best.weights",
                        help="yolo weights path")
    parser.add_argument("--ext_output", action='store_true', default=True,
                        help="display bbox coordinates of detected objects")
    parser.add_argument("--save_labels", action='store_true', default=True,
                        help="save detections bbox for each image in yolo format")
    parser.add_argument("--config_file", default="../cfg/yolov3-vattenhallen-test.cfg",
                        help="path to config file")
    parser.add_argument("--data_file", default="../data/vattenhallen.data",
                        help="path to data file")
    parser.add_argument("--thresh", type=float, default=.25,
                        help="remove detections with lower confidence")
    # arguemtns for grip
    parser.add_argument(
        '-ca',
        '--category',
        type=int,
        help='Choose the class of fruits to be picked up. There are tomato, mushroom,\
        potato, carrot, beetroot, zucchini, hand'
    )
    # arguments for location
    parser.add_argument(
        '-cam',
        '--camera_matrix',
        type=Path,
        default='../static/camera_no_distortion.mat',
        help='Path to mat file that contains intrinsic camera matrix K'
    )
    parser.add_argument(
        '-loc',
        '--locations',
        type=Path,
        default='../img/locations/',
        help='the path to txt files contains locations from encoders corresponds to each photo'
    )
    parser.add_argument(
        '-a',
        '--annotations',
        type=Path,
        default='../img/annotations',
        help='the path to txt files contains annotations for each photo'
    )
    parser.add_argument(
        '-o',
        '--offset',
        type=Path,
        default='../static/distance.txt',
        help='the txt contains distance offset for camera and gripper'
    )
    parser.add_argument(
        '-l',
        '--log',
        type=Path,
        default='../log/main.log',
        help='Path to the log file'
    )    
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode.')
    arguments = parser.parse_args()

    if arguments.verbose:
        basicConfig(filename=arguments.log, level=DEBUG)
    else:
        basicConfig(filename=arguments.log, level=INFO)
    main(arguments)