import sys
import json

class PyaciJsTest:

    def __init__(self):
        self.keep_running = True
        self.input_channel = sys.stdin

    def run(self):
        while self.keep_running:
            self.process_input()

    """ STD INPUTS """

    def process_input(self):

        msg_in = self.input_channel.readline().strip("\n")
        
        try:
            msg = json.loads(msg_in)
            print("[pyaci_test.py] Received: ", msg_in)
        except Exception as e:
            print("[pyaci_test.py] Error parsing: ", e)

        
        INPUT_LISTNERS = {
            "Disconnect": self.disconnect,
            "Echo": self.echo,
            "ProvisionScanStart": self.provisionScanStart,
            "Provision": self.provision,
            "Configure": self.configure,
            "TestSetEventGPIO": self.testSetEventGPIO,
            "AddAppKeys": self.addAppKeys
        }
        
        try:
            op = msg["op"]
            if "data" in msg:
                data = msg["data"]
            else: 
                data = None

            INPUT_LISTNERS[op](data)
        except Exception as e:
            print("[pyaci_test.py] Error trying func: ", e)

    def disconnect(self, data):
        raise SystemExit(0)

    def echo(self, data):
        self.echoRsp(data)

    def provisionScanStart(self, data):
        self.newUnprovisionedDevice({
            'uuid': "FOOO"
        })

    def provision(self, data):
        self.provisionComplete(data)

    def configure(self, data):
        self.compositionDataStatus(data)

    def addAppKeys(self, data):
        self.addAppKeysComplete(data)
    
    def testSetEventGPIO(self, data):
        op = "SetEventGPIO"
        data = {
            "uuid": "FOOO",
            "pin": 18,
            "value": 1
        }
        self.send(op, data)

    """ STD OUTPUTS """

    def send(self, op, data=None):
        msg = {
            'op': op,
            'data': data
        }
        print("[pyaci_test.py] Sending {}".format(json.dumps(msg)))
        print(json.dumps(msg))
        sys.stdout.flush()
        return True

    def echoRsp(self, data):
        op = "EchoRsp"
        self.send(op, data)
    
    def newUnprovisionedDevice(self, data):
        op = "NewUnprovisionedDevice"
        self.send(op, data)

    def provisionComplete(self, data):
        op = "ProvisionComplete"
        self.send(op, data)
    
    def compositionDataStatus(self, data):
        op = "CompositionDataStatus"
        self.send(op, data)

    def addAppKeysComplete(self, data):
        op = "AddAppKeysComplete"
        self.send(op, data)


if __name__ == "__main__":
    p = PyaciJsTest()
    p.run()