import sys
import json

class Pyaci:

    def __init__(self, mesh):
        self.keep_running = True
        self.input_channel = sys.stdin

        self.mesh = mesh

        setattr(self.mesh, "onNewUnProvisionedDevice", self.newUnprovisionedDevice)
        setattr(self.mesh, "onProvisionComplete", self.provisionComplete)
        setattr(self.mesh, "onCompositionDataStatus", self.compositionDataStatus)
        setattr(self.mesh, "onAddAppKeysComplete", self.addAppKeysComplete)
        setattr(self.mesh, "onSetEventGPIO", self.setEventGPIO)
        setattr(self.mesh, "onStatusEventGPIO", self.statusEventGPIO)
        setattr(self.mesh, "onSetAckFailedEventGPIO", self.setAckFailedEventGPIO)

    def run(self):
        while self.keep_running:
            self.process_input()

    """ STD INPUTS """

    def log(self, msg):
        print("[js_pyaci_interface.py] {}".format(msg))

    def logio(self, msg):
        # print("[js_pyaci_interface.py] {}".format(msg))
        pass

    def process_input(self):

        msg_in = self.input_channel.readline().strip("\n")
        
        try:
            msg = json.loads(msg_in)
            self.logio("Received: {}".format(msg_in))
        except Exception as e:
            self.log("Error parsing: {}".format(msg_in))
            self.log("{}".format(e))
            return

        
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
            "GetGPIO": self.getGPIO,
            "SetName": self.setName,
            "RemoveNode": self.removeNode
        }
        
        try:
            op = msg["op"]
            if "data" in msg:
                data = msg["data"]
            else: 
                data = None

            INPUT_LISTNERS[op](data)

        except Exception as e:
            self.log("Error trying func: {}".format(e))

    def disconnect(self, data):
        # add exit()
        self.keep_running = False
        # raise SystemExit(0)

    def echo(self, data):
        self.echoRsp(data)

    def provisionScanStart(self, data):
        self.mesh.provisionScanStart()

    def provision(self, data):
        uuid = data["uuid"]
        if "name" in data:
            self.mesh.provision(uuid, data["name"])
        else:
            self.mesh.provision(uuid)

    def getProvisionedDevices(self, data):
        devices = self.mesh.getProvisionedDevices()
        for dev in devices:
            self.getProvisionedDevicesRsp(dev)

    def configure(self, data):
        uuid = data["uuid"]
        self.mesh.configure(uuid)

    def addAppKeys(self, data):
        uuid = data["uuid"]
        self.mesh.addAppKeys(uuid)

    def configureGPIO(self, data): 
        self.mesh.configureGPIO(data["asInput"], data["pin"], data["uuid"])
    
    def setGPIO(self, data):
        self.mesh.setGPIO(data["value"], data["pin"], data["uuid"])
        
    def getGPIO(self, data):
        self.mesh.getGPIO(data["pin"], data["uuid"])

    def setName(self, data):
        self.mesh.setName(data["name"], data["uuid"])

    def removeNode(self, data):
        self.mesh.remove_node(data["uuid"])

    """ STD OUTPUTS """

    def send(self, op, data=None):
        msg = {
            'op': op,
            'data': data
        }
        self.logio("Sending {}".format(json.dumps(msg)))
        print(json.dumps(msg))
        sys.stdout.flush()
        return True

    def echoRsp(self, data):
        op = "EchoRsp"
        self.send(op, data)
    
    def newUnprovisionedDevice(self, device):
        op = "NewUnprovisionedDevice"
        self.send(op, device)

    def provisionComplete(self, uuid):
        op = "ProvisionComplete"
        data = {
            "uuid": uuid
        }
        self.send(op, data)
    
    def compositionDataStatus(self, uuid, compositionData):
        op = "CompositionDataStatus"
        data = {
            "uuid": uuid,
            "compositionData": compositionData
        }
        self.send(op, data)

    def addAppKeysComplete(self, uuid):
        op = "AddAppKeysComplete"
        data = {
            "uuid": uuid,
        }
        self.send(op, data)

    def setEventGPIO(self, value, pin, uuid):
        op = "SetEventGPIO"
        data = {
            "value": value,
            "pin": pin,
            "uuid": uuid
        }
        self.send(op, data)
    
    def statusEventGPIO(self, value, pin, uuid):
        op = "StatusEventGPIO"
        data = {
            "value": value,
            "pin": pin,
            "uuid": uuid
        }
        self.send(op, data)
    
    def setAckFailedEventGPIO(self, pin, uuid):
        op = "SetAckFailedEventGPIO"
        data = {
            "pin": pin,
            "uuid": uuid
        }
        self.send(op, data)

    def getProvisionedDevicesRsp(self, data):
        op = "GetProvisionedDevicesRsp"
        self.send(op, data)