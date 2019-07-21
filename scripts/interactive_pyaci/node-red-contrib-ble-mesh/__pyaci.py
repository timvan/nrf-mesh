import sys
import json

class Pyaci:

    def __init__(self):
        self.keep_running = True
        self.input_channel = sys.stdin

    def run(self):
        while self.keep_running:
            self.process_input()

    """ STD INPUTS """

    def log(self, msg):
        print["[__pyaci.py] " + msg]

    def process_input(self):

        msg_in = self.input_channel.readline().strip("\n")
        
        try:
            msg = json.loads(msg_in)
            self.log("Received: " + msg_in)
        except Exception as e:
            self.log("Error parsing: " + e)

        
        INPUT_LISTNERS = {
            "Disconnect": self.disconnect,
            "Echo": self.echo,
            "ProvisionScanStart": self.provisionScanStart,
            "Provision": self.provision,
            "GetProvisionedDevices": self.getProvisionedDevices,
            "Configure": self.configure,
            "AddAppKeys": self.addAppKeys,
            "ConfigureGPIO": self.configureGPIO,
            "SetGPIO": self.setGPIO,
            "SetName": self.setName,
        }
        
        try:
            op = msg["op"]
            if "data" in msg:
                data = msg["data"]
            else: 
                data = None

            INPUT_LISTNERS[op](data)

        except Exception as e:
            self.log("Error trying func: " + e)

    def disconnect(self, data):
        self.keep_running = False
        # raise SystemExit(0)

    def echo(self, data):
        self.echoRsp(data)

    def provisionScanStart(self, data):
        # TODO add provisionScanStart
        pass

    def provision(self, data):
        # TODO add provision
        pass

    def getProvisionedDevices(self, data):
        # TODO add getProvisionedDevices // change to connect???
        pass

    def configure(self, data):
        # TODO add configure
        pass

    def addAppKeys(self, data):
        # TODO add addAppKeys
        pass

    def configureGPIO(self, data):
        # TODO add configureGPIO
        pass
    
    def setGPIO(self, data):
        # TODO add setGPIO
        pass

    def setName(self, data):
        # TODO add setName
        pass

    """ STD OUTPUTS """

    def send(self, op, data=None):
        msg = {
            'op': op,
            'data': data
        }
        self.log("Sending {}".format(json.dumps(msg)))
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

    def setEventGPIO(self, data):
        op = "SetEventGPIO"
        self.send(op, data)

    def getProvisionedDevicesRsp(self, data):
        op = "GetProvisionedDevicesRsp"
        self.send(op, data)


if __name__ == "__main__":
    p = Pyaci()
    p.run()
