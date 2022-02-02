'''
Author: Ziliang Xiong
This script loads intrinsci camera matrix, which has been determined by calibration with MATLAB.
It reads YOLO's bounding boxes and calculate their global 2D coordinate on the planting bed accodring to 
coordinate transform. See details in README.md 
'''

from argparse import ArgumentParser, Namespace
from logging import basicConfig, DEBUG, INFO, getLogger
from pathlib import Path
from numpy import array, ndarray, dot, squeeze
from numpy.linalg import inv
from os import listdir
from os.path import join, isfile
from scipy.io import loadmat
from typing import Tuple, Optional


"""Logger for log file"""
_LOG = getLogger(__name__)

"""Type alias"""
CameraPosition = Tuple[float, float, float]
BoundingBox = Tuple[float, float, float, float]
KMatrix = ndarray(shape=(3, 3))

"""Allowed input and output file formats."""
_CAM_EXTENSIONS = 'mat'
_ANNOTATION_EXTENSIONS = 'txt'
_LOCATIONS_EXTENSIONS = 'txt'
_OFFSET_EXTENSIONS = 'txt'


"""Constant sweeping height"""
SWEEP_Z = 575 # change according to the setting, z=-100, height is 57.5cm


def read_offsets(offset_path: Path) -> Optional[Tuple[int, int]]:
    '''
    Load the offsets file, for coordinate transformation

    :param offset_path: file path
    :return cam_offset: distance of the camera centroid to z axis of Farmbot (dx, dy)
            gripper_offset: distance of the gripper centroid to z axis of Farmbot (dx, dy)
    '''
    if not offset_path.is_file():
        _LOG.error('{} is not a file or does not exist'.format(offset_path))
        return None
    
    if not offset_path.suffix.lstrip('.') in _OFFSET_EXTENSIONS:
        _LOG.error('{} must have an legal\
             extension: {}'.format(offset_path, _OFFSET_EXTENSIONS))
        return None

    try:
        with open(offset_path, 'r') as f:
            offsets = f.readlines()
    except IOError:
        _LOG.error('Unable to open input file {}.'.format(offset_path))
        return None

    cam_offset = (int(offsets[1]), int(offsets[2]))
    gripper_offset = (int(offsets[4]), int(offsets[5]))
    _LOG.info('Load the gripper offset\n{}\n and the camera offset \n{}'.format(gripper_offset, cam_offset))
    return cam_offset, gripper_offset


def load_cam_matrix(cam_path: Path) -> Optional[ndarray]: 
    '''
    load the mat file that contains camera calibration result, read the intrinsic matrix of the camera
    :param cam_path: path of the mat file 
    :return intrinsic_matrix: K matrix of the camera
    '''
    if not cam_path.suffix.lstrip('.') == _CAM_EXTENSIONS:
        _LOG.error('{} has an illegal extension'.format(cam_path))
        return None

    try:
        data = loadmat(cam_path)
    except FileNotFoundError:
        _LOG.error(' No such file')
        return None
        
    intrinsic_matrix = data['camera_no_distortion'][0, 0][11] 
    _LOG.info('Load intrinsic_matrix of the camera \n{}'.format(intrinsic_matrix))
    return intrinsic_matrix


def read_locations(locations_path: Path) -> Optional[ndarray]:
    '''
    read the locations of farmbot that corresponds to each photo

    param: locations_path: the path of folder locations
    return: list that contains locations
    '''
    if not locations_path.is_dir():
        _LOG.error('{} is not a directory or does not exist'.format(locations_path))
        return None

    number_files = len(listdir(locations_path))
    if number_files != 1:
        _LOG.error('More than one file of locations found the {}'.format(locations_path))
        return None

    locations_file = Path(locations_path, [file for file in listdir(locations_path)][0])    
    if not locations_file.suffix.lstrip('.') in _LOCATIONS_EXTENSIONS:
        _LOG.error('{} must have an legal\
             extension: {}'.format(locations_path, _LOCATIONS_EXTENSIONS))
        return None

    try:
        with open(locations_file, 'r') as f:
            locations = f.readlines()
    except IOError:
        _LOG.error('Unable to open input file {}.'.format(locations_path))
        return None

    list_location = []
    for location in locations:
        X, Y, Z = location.split()
        list_location.append([int(X), int(Y), int(Z)])  # integer？？？

    _LOG.info('Load all the locations \n {}'.format(list_location))
    return array(list_location)


def cam_coordinate(pixel_x: int, pixel_y: int, cam_matrix) -> Tuple[float, float]:
    '''
    Project one object's pixel coordinate into  the camera coordinate system

    Input: detection: a bounding box <x, y, w, h>
           inner_matrix: matrix K that contains focal length and other inner parameters
    Output: object's centroid location in camera coordinate
    '''
    normalized_coordinate = dot(inv(cam_matrix.transpose()), array([pixel_x, pixel_y, 1], dtype=float).reshape((3, 1)))
    camera_coordinate = squeeze(normalized_coordinate)
    ratio = float(SWEEP_Z / camera_coordinate[2])
    local_position = (ratio*camera_coordinate[0], ratio*camera_coordinate[1])
    _LOG.debug('Transfer from pixel coordinate to Camera coordinate. \n {}'.format(local_position))
    return local_position


def global_coordinate(cam_coordinate: Tuple[float, float], 
                      cam_location: Tuple[float, float, float], 
                      cam_offset: Tuple[int, int], 
                      gripper_offset: Tuple[int, int]) -> Tuple[float, float]:
    '''
    Calculate an object's locaiton in the globale coordinate(see definition in README.md) 
    by coordinate transform. 

    Input: cam_coordinate: object's centroid location in camera coordinate
           cam_location: camera's location reading from the encoder <x, y, z>
           cam_offset: cam_offset: distance of the camera centroid to z axis of Farmbot (dx, dy)
           gripper_offset: distance of the gripper centroid to z axis of Farmbot (dx, dy)
    Output: global location of a box
    '''
    global_x = -cam_coordinate[1] + cam_location[0] + cam_offset[0] + gripper_offset[0]
    global_y = cam_coordinate[0] + cam_location[1] + cam_offset[1] + gripper_offset[1]
    return (global_x, global_y)


def cal_location(args: Namespace) -> ndarray:
    '''
    main function for this script
    '''
    cam_offset, gripper_offset = read_offsets(args.offset)
    K_matrix = load_cam_matrix(args.camera_matrix)
    list_location = read_locations(args.locations) 
    # iterate over each annotation file
    _LOG.info('Global coordinate calculation begins.')
    list_annotations = listdir(args.annotations)
    # sort by chronological order  / specific for the filename on Ziliang's PC, change if other names
    list_annotations.sort() 
    # read annotations
    for index_photo, annotation_file in enumerate(list_annotations):
        filepath = Path(args.annotations, annotation_file)

        if not isfile(filepath):
            _LOG.error('{} is not a file or does not exist'.format(annotation_file))
            return None

        if not filepath.suffix.lstrip('.') in _ANNOTATION_EXTENSIONS:
            _LOG.error('{} must have an legal\
            extension: {}'.format(filepath, _ANNOTATION_EXTENSIONS))
            return None

        try:
            with open(filepath, 'r') as f:
                annotations = f.readlines()
        except IOError:
            _LOG.error('Unable to open input file {}.'.format(filepath))
            return None
        _LOG.debug('Load annotation {}'.format(annotations))

        list_global_coordinate = []
        for annotation in annotations:
            detection = annotation.split()
            # read the center_x center_y and class
            center_x = detection[1]
            center_y = detection[2]
            category = detection[0]
            confidence = detection[5]
            # pixel coordinate to camera coordinate
            local_coordinate = cam_coordinate(center_x, center_y, K_matrix)
            print(local_coordinate)

            # camera coordinate to global coordinate
            global_x, global_y = global_coordinate(local_coordinate, 
                                list_location[index_photo], cam_offset, gripper_offset)
            list_global_coordinate.append([category, global_x, global_y, confidence])     
            _LOG.debug(list_global_coordinate[-1])   
    
    _LOG.info('Global coordinate calculation is done.')
    return array(list_global_coordinate)


if __name__ == '__main__':
    parser = ArgumentParser(description='Transfer bounding boxes to real world coordinates')
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
        default='../log/location.log',
        help='Path to the log file'
    )

    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode')
    arguments = parser.parse_args()

    if arguments.verbose:
        basicConfig(filename=arguments.log, level=DEBUG)
    else:
        basicConfig(filename=arguments.log, level=INFO)

    cal_location(arguments)

    