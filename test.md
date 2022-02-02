To test darknet_images.py
```
python ./*darknet_images.py --input ~/farmbot/img --weights ~/farmbot/darknet/backup/yolov3-vattenhallen_best.weights --dont_show --ext_output --save_labels --config_file ~/farmbot/darknet/cfg/yolov3-vattenhallen-test.cfg --data_file ~/farmbot/darknet/data/vattenhallen.data
```
Default values are used for the rest. 

save label去了哪里？ 存到了和img同一个路径下 同名.txt文件，所以可以给一folder的图片同时检测

最好修改一下save label的地址，单独放一个folder

darkent_unproperly 可以删掉

mushroom x=87 y=24
carrot x=86 y=52

To test darknet_images.py
```
python ./*darknet_images.py --input ~/farmbot/img --weights ~/farmbot/weights/yolov3-vattenhallen_best.weights --dont_show --ext_output --save_labels --config_file ~/farmbot/cfg/yolov3-vattenhallen-test.cfg --data_file ~/farmbot/data/vattenhallen.data
```
Default values are used for the rest. 