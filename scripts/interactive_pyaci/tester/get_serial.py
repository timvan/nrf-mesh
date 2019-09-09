import datetime
import serial
port = '/dev/cu.usbmodem14201'
ser = serial.Serial(port, 96000, timeout=0)
while True:
    
    msg = ser.readline()
    # msg = ser.read(ser.inWaiting())
    if msg != b'':
        dt = datetime.datetime.now().isoformat()
        print("{} {}".format(dt, msg))