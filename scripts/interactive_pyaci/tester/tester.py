import time
import sys
import json
import os
import threading
import datetime
import serial



class Tester(object):
    
    def __init__(self, pins, uuids, mesh, test_type, test_id):
        self.pins = pins
        self.uuids = uuids
        self.mesh = mesh
        self.test_type = test_type
        self.test_id = test_id
        self.ack_failed = 0
        setattr(self.mesh.gc, "_GenericOnOffClient__client_set_ack_failed_cb", self.log_ack_failed)
        self.keeprunning = True

    def log_ack_failed(self, *args):
        self.ack_failed += 1

    def setup(self, asInput):
        for uuid in self.uuids:
            for pin in self.pins:
                self.mesh.configureGPIO(asInput, pin, uuid)
                time.sleep(0.05)

    def reset(self, asInput):
        for uuid in self.uuids:
            for pin in self.pins:
                self.mesh.setGPIO(asInput, pin, uuid)
                time.sleep(0.05)


    def run(self, x_send=5, delay=1):
        self.ack_failed = 0

        results = {
            'sent': 0
        }

        config = {
            'uuids': self.uuids,
            'pins': self.pins,
            # 'test_length_seconds': test_time,
            'message_delay': delay,
            'test_number': self.test_id,
            'ACK_TIMER_TIMEOUT': self.mesh.gc.ACK_TIMER_TIMEOUT,
            'RETRANSMISSION_LIMIT': self.mesh.gc.RETRANSMISSION_LIMIT,
        }

        while(results['sent'] < x_send):

            # send On command to each element on each device then send off
            if results['sent'] // (len(self.uuids) * len(self.pins)) % 2:
                value = True
            else:
                value = False

            # alternate between devices
            uuid = self.uuids[results['sent'] % len(self.uuids)]
            
            # progrssively work through each element for each device 
            pin_i = (results['sent'] // len(self.uuids)) % len(self.pins)
            pin = self.pins[pin_i]

            print("sending {} {} ".format(uuid, pin))

            self.mesh.setGPIO(value, pin, uuid)
            results['sent'] += 1
            time.sleep(delay)
            
            if(results['sent']):
                value = not value
            
        results['ack_failed'] = self.ack_failed
        test = {
            'setup': config,
            'results': results
        }

        test_flile = "test_{}_{}".format(self.test_type, self.test_id)
        test_dir = "tester/test_{}/setup/".format(self.test_type)
        os.makedirs(test_dir, exist_ok=True)
        with open(test_dir + test_flile, 'w') as f:
            f.write(json.dumps(test))

        self.test_id += 1

    
    def standup_standdown(self, x_send=5, delay_between_messages=0, interval_between_group_set=1):
        self.ack_failed = 0

        results = {
            'sent': 0
        }

        config = {
            'test': 'standup_standdown',
            'test_number': self.test_id,
            'uuids': self.uuids,
            'pins': self.pins,
            'ACK_TIMER_TIMEOUT': self.mesh.gc.ACK_TIMER_TIMEOUT,
            'delay_between_messages': delay_between_messages,
            'interval_between_group_set': interval_between_group_set
        }

        i = 0
        value = True        
        t_start = time.time()
        while(i < x_send * 2):
            while t_start + i * interval_between_group_set > time.time():
                pass

            for pin in self.pins:
                for uuid in self.uuids:
                    self.mesh.setGPIO(value, pin, uuid)
                    results['sent'] += 1
                    time.sleep(delay_between_messages)
            
            value = not value
            i += 1
                
        results['ack_failed'] = self.ack_failed
        test = {
            'setup': config,
            'results': results
        }

        test_flile = "test_{}_{}".format(self.test_type, self.test_id)
        test_dir = "tester/test_{}/setup/".format(self.test_type)
        os.makedirs(test_dir, exist_ok=True)
        with open(test_dir + test_flile, 'w') as f:
            f.write(json.dumps(test))

        self.test_id += 1

    def run2(self, number_messages=50, delays=[0.5], repeats=1):
        
        for uuid in self.uuids:
            for pin in self.pins:
                self.mesh.configureGPIO(False, pin, uuid)

        for i in range(repeats):
            for d in delays:
                print("----------------")
                for uuid in self.uuids:
                    for pin in self.pins:
                        self.mesh.setGPIO(False, pin, uuid)
                print("----------------")
                id = self.test_id
                print("HIT ENTER TO START TEST {}".format(id))

                while(sys.stdin.readline() != '\n'):
                    pass
                self.run(number_messages, d)

                print("----------------")
                print("FINISHED TEST {}".format(id))
                while(sys.stdin.readline() != '\n'):
                    pass
                print("----------------")

    def run3(self, test):
        setattr(self.mesh.gc, "ACK_TIMER_TIMEOUT", 0.025)

        delay = 0.05
        x = 50
    

    def run4(self, timeout=2, run_times=10, value=True):
        # sends on and off set signals on timed intervals to all devices for run_times
        # value is starting signal

        if self.keeprunning and run_times > 0:
            print(datetime.datetime.now().isoformat())
            for pin in self.pins: 
                for uuid in self.uuids: 
                    self.mesh.setGPIO(value, pin, uuid)
            
            threading.Timer(timeout, self.run4, (timeout, run_times-1, not value)).start()


    def run5(self, timeout=2, run_times=10, value=True, downtime_mulitplyer=1):
        # test4 however differences between on and off timer

        if self.keeprunning and run_times > 0:
            print(datetime.datetime.now().isoformat())
            for pin in self.pins: 
                for uuid in self.uuids: 
                    self.mesh.setGPIO(value, pin, uuid)
        
            if value:
                threading.Timer(timeout, self.run4, (timeout, run_times-1, not value)).start()
            else:
                threading.Timer(timeout, self.run4, (downtime_mulitplyer * timeout, run_times-1, not value)).start()
            


    def run6(self, timeout=2, run_times=10, value=True):
        # run4 with serial reading - i.e full loop

        thread = threading.Thread(target=self.read_from_port, args=(None,))
        thread.start()
        self.run4(timeout, run_times, value)


    def read_from_port(self, args):
        port = '/dev/cu.usbmodem14201'
        arduino = serial.Serial(port, 96000)
        while self.keeprunning:
            msg = arduino.readline().decode()
            print(">>>>>>>>>>>> {}".format(msg))