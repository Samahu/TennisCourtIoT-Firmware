import time
import sys
sys.path.append('/home/pi/.local/lib/python3.5/site-packages')
starttime =time.time()
from time import sleep
from picamera.array import PiRGBArray
from picamera import PiCamera
import cv2
import datetime
import json
import urllib.request,urllib.error
import RPi.GPIO as GPIO
import os
import uuid

def get_mac():
  mac_num = hex(uuid.getnode()).replace('0x', '').upper()
  mac = '-'.join(mac_num[i: i + 2] for i in range(0, 11, 2))
  return mac

url = "http://23.98.144.240:8080/postDeviceEvent"

#Check if offline json exists.
file = "data/offline.json"
exists = os.path.isfile(file)
js = '{"data":[]}'

#if exists load
if exists:
	with open(file,'r') as f:
		offline = json.load(f)
#if not load the default template		
else:
	offline = json.loads(js)
	

# Pretrained classes in the model
classNames = {0: 'background',
              1: 'person', 2: 'bicycle', 3: 'car', 4: 'motorcycle', 5: 'airplane', 6: 'bus',
              7: 'train', 8: 'truck', 9: 'boat', 10: 'traffic light', 11: 'fire hydrant',
              13: 'stop sign', 14: 'parking meter', 15: 'bench', 16: 'bird', 17: 'cat',
              18: 'dog', 19: 'horse', 20: 'sheep', 21: 'cow', 22: 'elephant', 23: 'bear',
              24: 'zebra', 25: 'giraffe', 27: 'backpack', 28: 'umbrella', 31: 'handbag',
              32: 'tie', 33: 'suitcase', 34: 'frisbee', 35: 'skis', 36: 'snowboard',
              37: 'sports ball', 38: 'kite', 39: 'baseball bat', 40: 'baseball glove',
              41: 'skateboard', 42: 'surfboard', 43: 'tennis racket', 44: 'bottle',
              46: 'wine glass', 47: 'cup', 48: 'fork', 49: 'knife', 50: 'spoon',
              51: 'bowl', 52: 'banana', 53: 'apple', 54: 'sandwich', 55: 'orange',
              56: 'broccoli', 57: 'carrot', 58: 'hot dog', 59: 'pizza', 60: 'donut',
              61: 'cake', 62: 'chair', 63: 'couch', 64: 'potted plant', 65: 'bed',
              67: 'dining table', 70: 'toilet', 72: 'tv', 73: 'laptop', 74: 'mouse',
              75: 'remote', 76: 'keyboard', 77: 'cell phone', 78: 'microwave', 79: 'oven',
              80: 'toaster', 81: 'sink', 82: 'refrigerator', 84: 'book', 85: 'clock',
              86: 'vase', 87: 'scissors', 88: 'teddy bear', 89: 'hair drier', 90: 'toothbrush'}


def id_class_name(class_id, classes):
    for key, value in classes.items():
        if class_id == key:
            return value

# Configure GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(21,GPIO.OUT)

# Loading model
model = cv2.dnn.readNetFromTensorflow('models/frozen_inference_graph.pb',
                                      'models/Class.pbtxt')

camera = PiCamera()
camera.resolution = (1920,1080)

# allow the camera to warmup
time.sleep(0.1)
 
# grab an image from the camera
Counts = dict()
loops = 10.0
for i in range(int(loops)):
 rawCapture = PiRGBArray(camera,size=(1920,1080))
 camera.capture(rawCapture, format="bgr")
 image = rawCapture.array
 image_height, image_width, _ = image.shape

 model.setInput(cv2.dnn.blobFromImage(image, size=(300, 300), swapRB=False))
 output = model.forward()
# print(output[0,0,:,:].shape)
 Json  = dict()
 for detection in output[0, 0, :, :]:
     confidence = detection[2]
     class_id = detection[1]
     class_name=id_class_name(class_id,classNames)
     # print(class_name+":"+str(confidence))
     if confidence > .5:
         #class_id = detection[1]
         #class_name=id_class_name(class_id,classNames)
         #print(class_name+":"+str(confidence))
         Counts[class_name] = Counts.get(class_name, 0) + 1
         box_x = detection[3] * image_width
         box_y = detection[4] * image_height
         box_width = detection[5] * image_width
         box_height = detection[6] * image_height
         cv2.rectangle(image, (int(box_x), int(box_y)), (int(box_width), int(box_height)), (23, 230, 210), thickness=1)
         cv2.putText(image,class_name ,(int(box_x), int(box_y+.05*image_height)),cv2.FONT_HERSHEY_SIMPLEX,(.0005*image_width),(0, 0, 255))
 timecost = time.time()-starttime

for i in Counts:
 if Counts[i]>1:
    Counts[i] = Counts[i]/loops

Json['DeviceId'] = get_mac()
Json['DeviceName'] = "Test01"
Json['DateTime']  = str(datetime.datetime.now().isoformat())
Json['Classes'] = Counts

req = urllib.request.Request(url)
req.add_header('Content-Type', 'application/json; charset=utf-8')
jsondata = json.dumps(Json)
#Append jsondata to json array
offline["data"].append(jsondata)

#Load default json template to catch exceptions
backup = json.loads(js)

#Loop through each previous captures. If posts correctly, dont add to backup. If error load capture to backup.
for i in range(len(offline["data"])):
	try:
		jsondataasbytes = offline["data"][i].encode('utf-8')   # needs to be bytes
		req.add_header('Content-Length', len(jsondataasbytes))
		response = urllib.request.urlopen(req, jsondataasbytes)		
	except urllib.error.URLError as e:
		backup["data"].append(offline["data"][i])
		print(str(e))

#Overwrite offline.js file with captures that errored out.
with open(file,'w') as f:
	json.dump(backup,f)
	


cv2.waitKey(0)
cv2.destroyAllWindows()

from subprocess import call
#GPIO.output(21,1)
#sleep(.5)
GPIO.cleanup()
#call("sudo shutdown -h now",shell=True)
call("gpio -g mode 4 out",shell=True)
