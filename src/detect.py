'''
load images taken by the camera, return bounding boxes

customized based on Alexy/darknet_images.py
'''
from argparse import ArgumentParser, Namespace
import os
import glob
import random
# from typing_extensions import final
import darknet  # darknet.py
import time
import cv2
import numpy as np


def check_arguments_errors(args):
    assert 0 < args.thresh < 1, "Threshold should be a float between zero and one (non-inclusive)"
    if not os.path.exists(args.config_file):
        raise(ValueError("Invalid config path {}".format(os.path.abspath(args.config_file))))
    if not os.path.exists(args.weights):
        raise(ValueError("Invalid weight path {}".format(os.path.abspath(args.weights))))
    if not os.path.exists(args.data_file):
        raise(ValueError("Invalid data file path {}".format(os.path.abspath(args.data_file))))
    if args.input and not os.path.exists(args.input):
        raise(ValueError("Invalid image path {}".format(os.path.abspath(args.input))))


def load_images(images_path):
    """
    If image path is given, return it directly
    For txt file, read it and return each line as image path
    In other case, it's a folder, return a list with names of each
    jpg, jpeg and png file
    """
    input_path_extension = images_path.split('.')[-1]
    if input_path_extension in ['jpg', 'jpeg', 'png']:
        # single image
        return [images_path]
    elif input_path_extension == "txt":
        with open(images_path, "r") as f:
            return f.read().splitlines()
    else:
        # folders
        return glob.glob(
            os.path.join(images_path, "*.jpg")) + \
            glob.glob(os.path.join(images_path, "*.png")) + \
            glob.glob(os.path.join(images_path, "*.jpeg"))


def image_detection(image_path, network, class_names, class_colors, thresh):
    # Darknet doesn't accept numpy images.
    # Create one with image we reuse for each detect
    # add image.shape as the output 
    width = darknet.network_width(network)
    height = darknet.network_height(network)
    darknet_image = darknet.make_image(width, height, 3)

    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_resized = cv2.resize(image_rgb, (width, height),
                               interpolation=cv2.INTER_LINEAR)

    darknet.copy_image_from_bytes(darknet_image, image_resized.tobytes())
    detections = darknet.detect_image(network, class_names, darknet_image, thresh=thresh)
    darknet.free_image(darknet_image)
    resized_image = darknet.draw_boxes(detections, image_resized, class_colors)

    return image.shape, cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB), detections


def convert2relative(image, bbox):
    """
    YOLO format use relative coordinates for annotation
    """
    x, y, w, h = bbox
    height, width, _ = image.shape
    return x/width, y/height, w/width, h/height


def save_annotations(original_size, name, image, detections, class_names):
    """
    Files saved with image_name.txt and relative coordinates
    oringinal_size is Ziliang's improvement
    """
    height, width, _ = original_size
    img_name = os.path.basename(name)
    file_name = os.path.splitext(img_name)[0] + ".txt"
    final_file_name = os.path.dirname(name) + '/annotations/' + file_name
    with open(final_file_name, "w") as f:
        for label, confidence, bbox in detections:
            x, y, w, h = convert2relative(image, bbox)
            label = class_names.index(label)
            f.write("{} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f}\n".format(label, x*width, y*height, w*width, h*height, float(confidence)))


def detect(args: Namespace)-> None:
    check_arguments_errors(args)

    random.seed(3)  # deterministic bbox colors
    network, class_names, class_colors = darknet.load_network(
        args.config_file,
        args.data_file,
        args.weights,
        batch_size=args.batch_size
    )

    images = load_images(args.input)

    index = 0
    while True:
        # loop asking for new image paths if no list is given
        if args.input:
            if index >= len(images):
                break
            image_name = images[index]
        else:
            image_name = input("Enter Image Path: ")
        prev_time = time.time()
        original_size, resized_image, detections = image_detection(
            image_name, network, class_names, class_colors, args.thresh
            )
        if args.save_labels:
            save_annotations(original_size, image_name, resized_image, detections, class_names)
        darknet.print_detections(detections, args.ext_output)
        fps = int(1/(time.time() - prev_time))
        print("FPS: {}".format(fps))
        index += 1


if __name__ == "__main__":
    parser = ArgumentParser(description="YOLO Object Detection")
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
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode')
    arguments = parser.parse_args()

    detect(arguments)
