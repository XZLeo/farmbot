#!/usr/bin/env python3
import serial
def gripper_open():
    ser = serial.Serial('/dev/ttyUSB0')
    ser.write(str.encode("o"))
    ser.close

def gripper_close():
    ser = serial.Serial('/dev/ttyUSB0')
    ser.write(str.encode("c"))
    ser.close