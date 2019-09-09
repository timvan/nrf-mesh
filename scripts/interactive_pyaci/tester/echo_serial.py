import datetime
import serial
import threading
port = '/dev/cu.usbmodem14201'
ser = serial.Serial(port, 96000, timeout=0)


def write_msg(i):
    dt = datetime.datetime.now().isoformat()
    print("{} out: {}".format(dt, i))
    msg = bytearray(i)
    ser.write(msg)
    if i > 0:
        threading.Timer(1, write_msg, args=(i-1,)).start()

threading.Timer(1, write_msg, args=(30,)).start()
while True:
    
    msg = ser.readline()
    # msg = ser.read(ser.inWaiting())
    if msg != b'':
        dt = datetime.datetime.now().isoformat()
        print("{} in: {}".format(dt, msg))