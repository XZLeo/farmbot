# A YOLO-based fruit picking system for FarmBot
## Brief introduction
https://pjreddie.com/darknet/yolo/
## YOLO, implemented by Darknet
Darknet is a deep learning framework created by the author of YOLO. It is written in C and provides nessary Python APIs for object detection. 



### Detector Training
Check the [instruction](https://github.com/AlexeyAB/darknet#how-to-train-to-detect-your-custom-objects) for how to train the YOLO detector.

## Camera Calibartion
Think YOLO as a black box, it consumes photos that contains objects or not and outputs objects' positions in the pixel coordinate. However, we want to know their positions on the planting bed, namely global coordinate. That is why we need camera calibration. This step was done seperately on MATLAB and offered us the intrinsic matrix of the camera. You **do not need to redo** this unless you want to change to a new model of camera. Check MATLAB [instruction](https://ww2.mathworks.cn/help/vision/ug/using-the-single-camera-calibrator-app.html;jsessionid=1a474c11e3e6063620885c4ae708) for how to use the camera calibration app.

**Note**: The result have to be transferred to `struct`, a MATLAB data type, before saving.  

If you follow the instruction above, you will end up with a MATLAB object, `cameraParameters`. If you save this to a .mat file and read it by Scipy, you will unfortunately end up with an empty dictionary. You should always use the function `toStruct` to convert it to a struct, which is close to Python dictionary, before saving it to a .mat file. Check the function [here](https://ww2.mathworks.cn/help/vision/ref/tostruct.html).

## Coordinate Tranform
Pixel Coordinate $\Rightarrow^{1}$ Camera Coordinate $\Rightarrow^{2}$ Global Coordinate  
- Pixel coordinate: Output bounding boxes from YOLO in the form of $<x, y, w,h>$. Here we only use $<x, y>$ currently. $w, h$ might be useful for estmating the size of obnjects in the future.
- Camera coordinate: The coordinate system determined by the camera, whose original point is at the camera pin hole.
- Gloabl coordinate: The coordinate system for Farmbot. The original point is at the upper right corner of the planting bed.  

Note: Due to mechanical limitation, the orginal point of global coordinate system does not perfectly align with the planting bed's corner.

### 1. From Pixel to Camera Coordinate

### 2. From Pixel to Camera Coordinate
The camera coordinate can be transformed to the gloabl one via a transistion and a rotation. From the picture, we can easily write the formula
$$

$$ 

## Install, Compile
1. `git clone *link* --recurse-submodules` this repo along with the submodule, Darknet;
2. Go to the path of the submodule `cd ./darknet`;
3. 
3. Change Makefile;
4. Compile Darknet;
5. Go back to the main path and `conda create --name <env> --file requirements.txt`, this will install all relied python packages. Change the enviroment name to whatever you like. 

**Note**: I assume conda, a package management software, has been installed before.

### Compile Darknet
Check the [instruction](https://github.com/AlexeyAB/darknet#how-to-compile-on-linux-using-make) for how to use `Make` to compile on Linux. 

**Note**: Change `LIBSO=1` in Makefile. This will ensure libdarknet.so be generated, which will be used in darknet.py.

## Before starting the system
**Always calibrate the position before using!**  
The purpose is to reset the zero positions of x, y, z axis. This step should be done manually first and then use the webapp, i.e., the user should push the grantry and z axis to the upper right corner. Check the [official instruction](https://software.farm.bot/v14/FarmBot-Software/how-to-guides/axis-setup) for how to use the web app to set zeros. 

## How to run this system?
The software has three main modules: 
1. `move.py`: drive FarmBot to move, take photos, and open/close the gripper
2. `detection.py`: run darknet as a dynamic library for detecting, output bounding boxes
3. `location.py`: input bounding boxes, transfer to real-world coordinate  

We also provide `main.py` as a warpper for all the modules above. By runing it, you can make Farmbot automatically conduct the whole process. The three modules can also be run sperately, mostly for debugging purpose.

First go to `/src/` and `conda activate <env>` to run the following scripts. `<env>` is the same as the one you created in *Install, Compile*
### Move Famrbot, take photos, and open/close the gripper
### YOLO detection
All the arguments for file path are set to default. 
```
python ./detect.py --dont_show --ext_output --save_labels --input ../img --weights ../weights/yolov3-vattenhallen_best.weights  --config_file ../cfg/yolov3-vattenhallen-test.cfg --data_file ../data/vattenhallen.data
```
### Calculate location
```
python location.py -v -cam ../static/camera_no_distortion.mat -loc ../img/locations/ -a ../img/annotations -o ../static/distance.txt -l ../log/location.log
```
All the arguments has default values, which means they can be all omitted if you don't change the document tree structure.

### Scan the bed and pick

重新生成requirement！！

