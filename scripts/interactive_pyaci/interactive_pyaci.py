# Copyright (c) 2010 - 2018, Nordic Semiconductor ASA
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of Nordic Semiconductor ASA nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL NORDIC SEMICONDUCTOR ASA OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys

if sys.version_info < (3, 5):
    print(("ERROR: To use {} you need at least Python 3.5.\n" +
           "You are currently using Python {}.{}").format(sys.argv[0], *sys.version_info))
    sys.exit(1)

import logging
import IPython
import DateTime
import os
import colorama
import time
import json
import subprocess

from argparse import ArgumentParser
import traitlets.config

from aci.aci_uart import Uart
from aci.aci_utils import STATUS_CODE_LUT
from aci.aci_config import ApplicationConfig
import aci.aci_cmd as cmd
from aci.aci_cmd import RESPONSE_LUT
import aci.aci_evt as evt

from mesh import access
from mesh.provisioning import Provisioner, Provisionee  # NOQA: ignore unused import
from mesh import types as mt                            # NOQA: ignore unused import
from mesh.database import MeshDB                        # NOQA: ignore unused import
from models.config import ConfigurationClient           # NOQA: ignore unused import
from models.generic_on_off import GenericOnOffClient    # NOQA: ignore unused import
from models.generic_on_off import GenericOnOffServer
from models.simple_on_off import SimpleOnOffClient

LOG_DIR = os.path.join(os.path.dirname(sys.argv[0]), "log")

USAGE_STRING = \
    """
    {c_default}{c_text}To control your device, use {c_highlight}d[x]{c_text}, where x is the device index.
    Devices are indexed based on the order of the COM ports specified by the -d option.
    The first device, {c_highlight}d[0]{c_text}, can also be accessed using {c_highlight}device{c_text}.

    Type {c_highlight}d[x].{c_text} and hit tab to see the available methods.
""" # NOQA: Ignore long line
USAGE_STRING += colorama.Style.RESET_ALL

FILE_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s: %(message)s"
STREAM_LOG_FORMAT = "PYACILOG %(asctime)s - %(levelname)s - %(name)s: %(message)s"
COLOR_LIST = [colorama.Fore.MAGENTA, colorama.Fore.CYAN,
              colorama.Fore.GREEN, colorama.Fore.YELLOW,
              colorama.Fore.BLUE, colorama.Fore.RED]
COLOR_INDEX = 0


def configure_logger(device_name):
    global options
    global COLOR_INDEX

    logger = logging.getLogger(device_name)
    logger.setLevel(logging.DEBUG)

    stream_formatter = logging.Formatter(
        COLOR_LIST[COLOR_INDEX % len(COLOR_LIST)] + colorama.Style.BRIGHT
        + STREAM_LOG_FORMAT
        + colorama.Style.RESET_ALL)
    COLOR_INDEX = (COLOR_INDEX + 1) % len(COLOR_LIST)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(stream_formatter)
    stream_handler.setLevel(options.log_level)
    logger.addHandler(stream_handler)

    if not options.no_logfile:
        dt = DateTime.DateTime()
        logfile = "{}_{}-{}-{}-{}_output.log".format(
            device_name, dt.yy(), dt.dayOfYear(), dt.hour(), dt.minute())
        logfile = os.path.join(LOG_DIR, logfile)
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(FILE_LOG_FORMAT)
        fh.setFormatter(file_formatter)
        logger.addHandler(fh)
    return logger


class Interactive(object):
    DEFAULT_APP_KEY = bytearray([0xAA] * 16)
    DEFAULT_SUBNET_KEY = bytearray([0xBB] * 16)
    DEFAULT_VIRTUAL_ADDRESS = bytearray([0xCC] * 16)
    DEFAULT_STATIC_AUTH_DATA = bytearray([0xDD] * 16)
    DEFAULT_LOCAL_UNICAST_ADDRESS_START = 0x0001
    CONFIG = ApplicationConfig(
        header_path=os.path.join(os.path.dirname(sys.argv[0]),
                                 ("../../examples/serial/include/"
                                  + "nrf_mesh_config_app.h")))
    PRINT_ALL_EVENTS = True

    def __init__(self, acidev):
        self.acidev = acidev
        self._event_filter = []
        self._event_filter_enabled = True
        self._other_events = []

        self.logger = configure_logger(self.acidev.device_name)
        self.send = self.acidev.write_aci_cmd

        # Increment the local unicast address range
        # for the next Interactive instance
        self.local_unicast_address_start = (
            self.DEFAULT_LOCAL_UNICAST_ADDRESS_START)
        Interactive.DEFAULT_LOCAL_UNICAST_ADDRESS_START += (
            self.CONFIG.ACCESS_ELEMENT_COUNT)

        self.access = access.Access(self, self.local_unicast_address_start,
                                    self.CONFIG.ACCESS_ELEMENT_COUNT)
        self.model_add = self.access.model_add

        # Adding the packet recipient will start dynamic behavior.
        # We add it after all the member variables has been defined
        self.acidev.add_packet_recipient(self.__event_handler)

    def close(self):
        self.acidev.stop()

    def events_get(self):
        return self._other_events

    def event_filter_add(self, event_filter):
        self._event_filter += event_filter

    def event_filter_disable(self):
        self._event_filter_enabled = False

    def event_filter_enable(self):
        self._event_filter_enabled = True

    def device_port_get(self):
        return self.acidev.serial.port

    def quick_setup(self):
        self.send(cmd.SubnetAdd(0, bytearray(self.DEFAULT_SUBNET_KEY)))
        self.send(cmd.AppkeyAdd(0, 0, bytearray(self.DEFAULT_APP_KEY)))
        self.send(cmd.AddrLocalUnicastSet(
            self.local_unicast_address_start,
            self.CONFIG.ACCESS_ELEMENT_COUNT))

    def __event_handler(self, event):
        # self.logger.info("Got " + str(event._opcode))
        

        if self._event_filter_enabled and event._opcode in self._event_filter:
            # Ignore event
            return
        if event._opcode == evt.Event.DEVICE_STARTED:
            self.logger.info("Device rebooted.")

        elif event._opcode == evt.Event.CMD_RSP:
            if event._data["status"] != 0:
                self.logger.error("{}: {}".format(
                    cmd.response_deserialize(event),
                    STATUS_CODE_LUT[event._data["status"]]["code"]))
            else:
                text = str(cmd.response_deserialize(event))
                if text == "None":
                    text = "Success"
                self.logger.info(text)
                
        else:
            if self.PRINT_ALL_EVENTS and event is not None:
                self.logger.info(str(event))
            else:
                self._other_events.append(event)

class Manager(object):

    NRF52_DEV_BOARD_GPIO_PINS = [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25]
    STARTING_ELEMENT_INDEX = 1

    def __init__(self, interactive_device):
        self.keep_running = True
        self.db_path = "database/example_database.json"
        self.iaci = interactive_device
        self.logger = self.iaci.logger
        self.n = 0

        self.iaci.event_filter_disable() 
        self.iaci.acidev.add_packet_recipient(self.__event_handler)
        self.address_stack = list()

        self.setup()

    def run(self):
        while self.keep_running:
            self.process_stdin()

    def __event_handler(self, event):

        if event._opcode == evt.Event.PROV_UNPROVISIONED_RECEIVED:
            uuid = event._data["uuid"]
            rssi = event._data["rssi"]
            
            if uuid not in self.p.unprov_list:
                self.newUnProvisionedDevice({
                    "uuid": uuid.hex(),
                    "rssi": rssi
                    })

        if event._opcode == evt.Event.PROV_COMPLETE:
            time.sleep(6)
            self.process_stdout("ProvisionComplete")

        if event._opcode == evt.Event.MESH_MESSAGE_RECEIVED_UNICAST or event._opcode == evt.Event.MESH_MESSAGE_RECEIVED_SUBSCRIPTION:
            message = access.AccessMessage(event)
            opcode = message.opcode_raw.hex()
        
            if opcode == str(ConfigurationClient._COMPOSITION_DATA_STATUS):
                data = message.data[1:]
                compositionData = mt.CompositionData().unpack(data)

                src = message.meta["src"]
                node, element = self.src_address_to_node_element_index(src)
                uuid = self.db.nodes[node].UUID

                self.compositionDataStatusRsp(uuid, compositionData)

        if event._opcode == evt.Event.CMD_RSP:
            
            opcode = event._data["opcode"]
            
            if opcode in [0xA1, 0xA2, 0xA4, 0xA5]:
                try:
                    new_address = self.address_stack.pop(0)

                    # assert(new_address["opcode"] is opcode)
                    # assert(new_address["address_handle"] is event._data["data"][0])

                    address_handle = {
                        "address": new_address["address"]
                        , "address_handle": event._data["data"][0]
                        , "opcode": opcode
                    }
                    
                    self.db.address_handles.append(address_handle)
                    self.logger.info("Address handles: {}".format(self.db.address_handles))
                    
                except Exception as e:
                    self.logger.error("Error storing address handle: {}".format(e))
                    
    def process_stdout(self, op, data=None):
        
        msg = {
            'op': op,
            'id': self.n
        }
        if data:
            msg['data'] = data
        print(json.dumps(msg));
        self.n += 1
        sys.stdout.flush()

    def process_stdin(self):
        msg = sys.stdin.readline().strip("\n")
        print("got ", msg)

        if(msg == "check"):
            self.process_stdout("running")
            self.exit()
            return
        
        if(msg == "\n"):
            return

        try:
            msg = json.loads(msg)
        except:
            print("Error parsing message: ", msg)
            self.exit()
            return
        
        op = msg["op"]
        
        if op == "Echo":
            self.echo(msg)

        if op == "Setup":
            self.setup()
        
        if op == "Exit":
            self.exit()

        if op == "ProvisionScanStart":
            self.provisionScanStart()

        if op == "ProvisionScanStop":
            self.provisionScanStop()

        if op == "Provision":
            self.provision(msg["data"]["uuid"])
        
        if op == "Configure":
            self.configure()

        if op == "AddAppKeys":
            self.addAppKeys()

        if op == "AddGroupSubscriptionAddresses":
            self.addGroupSubscriptionAddresses()

        if op == "AddGroupPublicationAddresses":
            self.addGroupPublicationAddresses()

        if op == "AddGenericClientModel":            
            self.addGenericClientModel()
        
        if op == "AddGenericServerModel":            
            self.addGenericServerModel()

        if op == "GenericClientSet":
            self.genericClientSet(value = msg["data"]["value"])

        if op == "SetGPIO":
            try:
                value = int(msg["data"]["value"])
                pin = int(msg["data"]["pin"])
                uuid = msg["data"]["uuid"]

                if not self.check_pin(pin):
                    self.process_stdout("PinError")
                    return
                if not self.check_uuid(uuid):
                    self.process_stdout("UUIDError")
                    return
                if not self.check_value(value):
                    self.process_stdout("ValueError")
                    return

                self.setGPIO(value, pin, uuid)
            except Exception as e:
                self.logger.error("Error in SetGPIO ", e)
        
        if op == "ConfigureGPIO":
            try:
                value = int(msg["data"]["value"])
                pin = int(msg["data"]["pin"])
                uuid = msg["data"]["uuid"]

                if not self.check_pin(pin):
                    self.process_stdout("PinError")
                    return
                if not self.check_uuid(uuid):
                    self.process_stdout("UUIDError")
                    return
                if not self.check_value(value):
                    self.process_stdout("ValueError")
                    return

                self.configureGPIO(value, pin, uuid)
            except Exception as e:
                self.logger.error("Error in ConfigureGPIO ", e)

        if op =="GetProvisionedDevices":
            self.getProvisionedDevices();

    def check_pin(self, pin):
        return pin in self.NRF52_DEV_BOARD_GPIO_PINS
    
    def check_uuid(self, uuid):
        if len(self.db.nodes) == 0:
            return False

        for node in self.db.nodes:
            if node.UUID.hex() == uuid:
                return True
        return False
    
    def check_value(self, value):
        return value == 1 or value == 0

    def echo(self, msg):
        op = "EchoRsp"
        self.process_stdout(op, msg["data"])

    def setup(self):
        # subprocess.call(["cp", "database/example_database.json.backup", "database/example_database.json"])
        self.db = MeshDB(self.db_path)
        self.p = Provisioner(self.iaci, self.db)
        
        self.cc = ConfigurationClient(self.db)
        self.iaci.model_add(self.cc)

        self.load_address_handles()

        if len(self.db.models) > 0:
            self.load_models()
        else:
            self.addModels()

        self.process_stdout("SetupRsp")

    def load_address_handles(self):
        sortedList = sorted(self.db.address_handles, key = lambda k: k["address_handle"])
        for i, item in enumerate(sortedList):

            assert(i == item["address_handle"])

            address = item["address"]
            opcode = item["opcode"]

            if RESPONSE_LUT[opcode]["name"] == "AddrSubscriptionAdd":
                command = cmd.AddrSubscriptionAdd
            if RESPONSE_LUT[opcode]["name"] == "AddrSubscriptionAddVirtual":
                command = cmd.AddrSubscriptionAddVirtual
            if RESPONSE_LUT[opcode]["name"] == "AddrPublicationAdd":
                command = cmd.AddrPublicationAdd
            if RESPONSE_LUT[opcode]["name"] == "AddrPublicationAddVirtual":
                command = cmd.AddrPublicationAddVirtual
            
            self.iaci.send(command(address))
            time.sleep(1)

    def load_models(self):

        db_models = self.db.models.copy()
        self.db.models = []

        for model in db_models:
                
            if model["model"] == "GenericOnOffClient":
                self.addGenericClientModel()
                self.gc.__tid = model["tid"]
            
            if model["model"] == "GenericOnOffServer":
                self.addGenericServerModel()
                self.gs.__tid = model["tid"]
                
            if model["model"] == "SimpleOnOffClient":
                self.addSimpleClientModel()
                self.sc.__tid = model["tid"]

    def exit(self):
        self.keep_running = False
        raise SystemExit(0)

    def provisionScanStart(self):
        self.p.scan_start()

    def provisionScanStop(self):
        self.p.scan_stop()

    def newUnProvisionedDevice(self, data):
        op = "NewUnProvisionedDevice"
        self.process_stdout(op, data)

    def provision(self, uuid, name="Server"):
        self.p.scan_stop()
        self.p.provision(uuid=uuid, name=name)
        
    def configure(self, device_handle=8, address_handle=0, groupAddrId=0):
        self.cc.publish_set(device_handle, address_handle)
        self.cc.composition_data_get()
        self.cc.appkey_add(0)
        

    def compositionDataStatusRsp(self, uuid, compositionData):
        op = "CompositionDataStatus"
        data = {
            "uuid": uuid,
            "compositionData": compositionData
        }
        self.process_stdout(op, data)
        
    def addAppKeys(self, node=0, groupAddrId=0):
        """ Used to:
            - subscribes the serial device to the group address
            - add publication address of each element to the serial device
            - bind app_key to each model on each element
            - set the client to publish to the group address
        
        Parameters
        ----------
            node : index of node in db
            groupAddrId : index of group address in db

        """
        self.addAddress(cmd.AddrSubscriptionAdd , self.db.groups[groupAddrId].address)

        for e, element in enumerate(self.db.nodes[node].elements):
            
            # Add each element to the serial device's pubusb list
            element_address = self.db.nodes[node].unicast_address + e
            self.addAddress(cmd.AddrPublicationAdd, element_address)

            for model in element.models:
                
                # Generic OnOff Server
                if str(model.model_id) == "1000":
                    self.cc.model_app_bind(element_address, 0, mt.ModelId(0x1000))
                    time.sleep(1)
                    
                # Generic OnOff Client
                if str(model.model_id) == "1001":
                    self.cc.model_app_bind(element_address, 0, mt.ModelId(0x1001))
                    time.sleep(1)
                    self.cc.model_publication_set(element_address, mt.ModelId(0x1001), mt.Publish(self.db.groups[groupAddrId].address, index=0, ttl=1))
                    time.sleep(1)

                # Simple OnOff Server
                if str(model.model_id) == "00590000":
                    self.cc.model_app_bind(element_address, 0, mt.ModelId(0x0000, company_id=0x0059))
                    time.sleep(1)

        self.addAppKeysComplete()
    
    def addAppKeysComplete(self):
        self.process_stdout("AddAppKeysComplete")

    def addAddress(self, command, address):
        self.logger.info("Adding address {}".format(address))
        
        new_address = {
            "address": address
            , "opcode": command
        }

        self.address_stack.append(new_address)
        
        self.iaci.send(command(address))
        time.sleep(1)

    def addGroupSubscriptionAddresses(self, node=0, groupAddrId=0):
        for e, element in enumerate(self.db.nodes[node].elements):
            for model in element.models:
                if str(model.model_id) == "1000":
                    self.cc.model_subscription_add(self.db.nodes[node].unicast_address + e, self.db.groups[groupAddrId].address, mt.ModelId(0x1000))                
                    time.sleep(1)

    def addGroupPublicationAddresses(self, node=0, groupAddrId=0):
        
        group_address = self.db.groups[groupAddrId].address
        self.addAddress(cmd.AddrSubscriptionAdd, group_address)

        for e, element in enumerate(self.db.nodes[node].elements):
            for model in element.models:
                if str(model.model_id) == "1001":
                    self.cc.model_publication_set(self.db.nodes[node].unicast_address + e, mt.ModelId(0x1001), mt.Publish(group_address, index=0, ttl=1))
                time.sleep(1)

    def addModels(self):
        self.addGenericClientModel()
        self.addGenericServerModel()
        self.addSimpleClientModel()

    def addGenericClientModel(self):
        self.gc = GenericOnOffClient()
        self.iaci.model_add(self.gc)
        self.db.models.append(self.gc)
    
    def genericClientSet(self, value, key_handle=0, address_handle=0):
        # key_handle is app key 
        self.gc.publish_set(key_handle, address_handle)
        self.gc.set(value)
        
    def addGenericServerModel(self):
        self.gs = GenericOnOffServer()
        self.gs.set_generic_on_off_server_set_unack_cb(self.genericOnOffServerSetUnackEvent)
        self.iaci.model_add(self.gs)
        self.db.models.append(self.gs)

    def genericOnOffServerSetUnackEvent(self, message):
        value = int(message.data.hex()[1])
        src = message.meta["src"]
        node, element = self.src_address_to_node_element_index(src)
        uuid = self.db.nodes[node].UUID
        self.setEventGPIO(value, self.element_index_to_pin(element), uuid)

    def setEventGPIO(self, value, pin, uuid):
        self.logger.info("Sending value:{} uuid:{} pin:{}".format(value, uuid, pin))
        data = {
            "value": value,
            "uuid": uuid,
            "pin": pin
        }
        self.process_stdout("SetEventGPIO", data)

    def addSimpleClientModel(self):
        self.sc = SimpleOnOffClient()
        self.iaci.model_add(self.sc)
        self.db.models.append(self.sc)

    def simpleClientSet(self, value, key_handle=0, address_handle=0):
        # key_handle is app key
        # False is output
        self.sc.publish_set(key_handle, address_handle)
        self.sc.set(value)

    def configureGPIO(self, asInput, pin, uuid):
        address_handle = self.get_address_handle(pin, uuid)
        self.simpleClientSet(asInput, address_handle=address_handle)

    def setGPIO(self, value, pin, uuid):
        address_handle = self.get_address_handle(pin, uuid)
        self.genericClientSet(value, address_handle=address_handle)

    def getProvisionedDevices(self):
        for node in self.db.nodes:
            self.process_stdout("GetProvisionedDevicesRsp", {
                "uuid" : node.UUID,
                "compositionData": node
            })

    """""""""""""""""""""""""""""""""""""""""""""
    HELPERS / CONVERTERS
    """""""""""""""""""""""""""""""""""""""""""""

    def get_address_handle(self, pin, uuid):
        element = self.pin_to_element_index(pin)
        node = self.uuid_to_node_index(uuid)

        if node != None and element != None:
            address = self.db.nodes[node].unicast_address + element
            return self.db.find_address_handle(address)
        
        return None

    def pin_to_element_index(self, pin):        
        if pin in self.NRF52_DEV_BOARD_GPIO_PINS:
            element_index = self.NRF52_DEV_BOARD_GPIO_PINS.index(pin)
            element_index += self.STARTING_ELEMENT_INDEX
            return element_index
        
        return None

    def element_index_to_pin(self, element_index):
        element_index -= self.STARTING_ELEMENT_INDEX
        if element_index < len(self.NRF52_DEV_BOARD_GPIO_PINS) and element_index >= 0:
            return self.NRF52_DEV_BOARD_GPIO_PINS[element_index]

        return None


    def src_address_to_node_element_index(self, src_address):
        """ Used to find the node and element index in the db from an address
        
        Parameters
        ----------
            src_address : unicast address of an element or node

        """
        for node_index, node in enumerate(self.db.nodes):
            for element_index, element in enumerate(node.elements):
                
                if int(node.unicast_address + element_index) == src_address:
                    return node_index, element_index

    def uuid_to_node_index(self, uuid):
        """ Uses to find the index of the device in the db from it's uuid

        Parameters
        ----------
            uuid : device uuid

        """
        for n, node in enumerate(self.db.nodes):
            if uuid == node.UUID.hex():
                return n



def start_ipython(options):
    comports = options.devices
    d = list()

    if not options.no_logfile and not os.path.exists(LOG_DIR):
        print("Creating log directory: {}".format(os.path.abspath(LOG_DIR)))
        os.mkdir(LOG_DIR)

    for dev_com in comports:
        d.append(Interactive(Uart(port=dev_com,
                                baudrate=options.baudrate,
                                device_name=dev_com.split("/")[-1])))

    device = d[0]
    send = device.acidev.write_aci_cmd  # NOQA: Ignore unused variable

    m = Manager(device)
    m.run()

    for dev in d:
        dev.close()
    raise SystemExit(0)

if __name__ == '__main__':
    parser = ArgumentParser(
        description="nRF5 SDK for Mesh Interactive PyACI")
    parser.add_argument("-d", "--device",
                        dest="devices",
                        nargs="+",
                        required=False,
                        default=["/dev/tty.usbmodem0006822145041"],
                        help=("Device Communication port, e.g., COM216 or "
                              + "/dev/ttyACM0. You may connect to multiple "
                              + "devices. Separate devices by spaces, e.g., "
                              + "\"-d COM123 COM234\""))
    parser.add_argument("-b", "--baudrate",
                        dest="baudrate",
                        required=False,
                        default='115200',
                        help="Baud rate. Default: 115200")
    parser.add_argument("--no-logfile",
                        dest="no_logfile",
                        action="store_true",
                        required=False,
                        default=False,
                        help="Disables logging to file.")
    parser.add_argument("-l", "--log-level",
                        dest="log_level",
                        type=int,
                        required=False,
                        default=4,
                        help=("Set default logging level: "
                              + "0=Critical Only, 1=Errors only, 2=Warnings, 3=Info, 4=Debug"))
    options = parser.parse_args()

    if options.log_level == 0:
        options.log_level = logging.CRITICAL
    elif options.log_level == 1:
        options.log_level = logging.ERROR
    elif options.log_level == 2:
        options.log_level = logging.WARNING
    elif options.log_level == 3:
        options.log_level = logging.INFO
    else:
        options.log_level = logging.DEBUG

    start_ipython(options)