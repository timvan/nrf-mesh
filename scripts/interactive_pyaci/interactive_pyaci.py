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
import aci.aci_evt as evt

from mesh import access
from mesh.provisioning import Provisioner, Provisionee  # NOQA: ignore unused import
from mesh import types as mt                            # NOQA: ignore unused import
from mesh.database import MeshDB                        # NOQA: ignore unused import
from models.config import ConfigurationClient           # NOQA: ignore unused import
from models.generic_on_off import GenericOnOffClient    # NOQA: ignore unused import
from models.generic_on_off import GenericOnOffServer

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

    def __init__(self, interactive_device):
        self.keep_running = True
        self.db_path = "database/example_database.json"
        self.iaci = interactive_device
        self.n = 0
        self.setup_received = False;
        self.iaci.acidev.add_packet_recipient(self.__event_handler)

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


        if event._opcode == evt.Event.MESH_MESSAGE_RECEIVED_UNICAST or event._opcode == evt.Event.MESH_MESSAGE_RECEIVED_SUBSCRIPTION:
            message = access.AccessMessage(event)
            opcode = message.opcode_raw.hex()
        

            if opcode == str(ConfigurationClient._COMPOSITION_DATA_STATUS):
                data = message.data[1:]
                data = mt.CompositionData().unpack(data)
                self.compositionDataStatus(data)


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
            self.provision()
        
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


    def echo(self, msg):
        op = "EchoRsp"
        self.process_stdout(op, msg["data"])

    def setup(self):
        if not self.setup_received:
            subprocess.call(["cp", "database/example_database.json.backup", "database/example_database.json"])
            self.db = MeshDB(self.db_path)
            self.p = Provisioner(self.iaci, self.db)
            self.setup_received = True;
            self.process_stdout("SetupRsp")
    
    def exit(self):
        self.keep_running = False
        raise SystemExit(0)

    def provisionScanStart(self):
        self.p.scan_start()

    def provisionScanStop(self):
        self.p.scan_stop()


    def newUnProvisionedDevice(self, data):
        op = "NewUnProvisionedDevice";
        self.process_stdout(op, data)

    def provision(self):

        self.p.scan_stop()
        self.p.provision(name="Server")

        while not self.p.provisioning_open:
            pass

        self.process_stdout("ProvisionComplete")
        
    def configure(self, groupAddrId=0):
        self.cc = ConfigurationClient(self.db)
        self.iaci.model_add(self.cc)
        self.cc.publish_set(8, 0)
        self.cc.composition_data_get()
        self.cc.appkey_add(0)
        self.iaci.send(cmd.AddrPublicationAdd(self.db.groups[groupAddrId].address))

    def compositionDataStatus(self, data):
        op = "CompositionDataStatus"
        self.process_stdout(op, data)
        
    def addAppKeys(self, node=0, groupAddrId=0):
        for e, element in enumerate(self.db.nodes[node].elements):
            
            # Add each element to the serial device's pubusb list
            # TODO here I should log each device into address book
            self.iaci.send(cmd.AddrPublicationAdd(self.db.nodes[node].unicast_address + e))
            self.iaci.send(cmd.AddrSubscriptionAdd(self.db.nodes[node].unicast_address + e))

            for model in element.models:
                if str(model.model_id) == "1000":
                    self.cc.model_app_bind(self.db.nodes[node].unicast_address + e, 0, mt.ModelId(0x1000))
                    # self.cc.model_subscription_add(self.db.nodes[node].unicast_address + e, self.db.groups[groupAddrId].address, mt.ModelId(0x1000))
                if str(model.model_id) == "1001":
                    self.cc.model_app_bind(self.db.nodes[node].unicast_address + e, 0, mt.ModelId(0x1001))
                    time.sleep(1)
                    self.cc.model_publication_set(self.db.nodes[node].unicast_address + e, mt.ModelId(0x1001), mt.Publish(self.db.groups[groupAddrId].address, index=0, ttl=1))
                time.sleep(1)



    def addGroupSubscriptionAddresses(self, node=0, groupAddrId=0):
        for e, element in enumerate(self.db.nodes[node].elements):
            for model in element.models:
                if str(model.model_id) == "1000":
                    self.cc.model_subscription_add(self.db.nodes[node].unicast_address + e, self.db.groups[groupAddrId].address, mt.ModelId(0x1000))
                
                time.sleep(1)

    def addGroupPublicationAddresses(self, node=0, groupAddrId=0):
        self.iaci.send(cmd.AddrSubscriptionAdd(self.db.groups[groupAddrId].address))

        for e, element in enumerate(self.db.nodes[node].elements):
            for model in element.models:
                if str(model.model_id) == "1001":
                    self.cc.model_publication_set(self.db.nodes[node].unicast_address + e, mt.ModelId(0x1001), mt.Publish(self.db.groups[groupAddrId].address, index=0, ttl=1))
                time.sleep(1)

    def addGenericClientModel(self):
        self.gc = GenericOnOffClient()
        self.iaci.model_add(self.gc)
    
    def genericClientSet(self, value):
        self.gc.publish_set(0, 0)
        self.gc.set(value)

    def addGenericServerModel(self):
        self.gs = GenericOnOffServer()
        self.gs.set_generic_on_off_server_set_unack_cb(self.genericOnOffServerSetUnackEvent)
        self.iaci.model_add(self.gs)

    def genericOnOffServerSetUnackEvent(self, message):
        value = message[1]
        self.process_stdout("GenericOnOffServerSetUnack", value)


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