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
import os
import time
import json
import subprocess
import struct
import functools
import signal
import threading

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

    def __init__(self, acidev, logger):
        self.acidev = acidev
        self._event_filter = []
        self._event_filter_enabled = True
        self._other_events = []

        self.logger = logger
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

class Mesh(object):

    NRF52_DEV_BOARD_GPIO_PINS = [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25]
    NRF52_STARTING_ELEMENT_INDEX = 1

    QUICK_SETUP = True

    def __init__(self, interactive_device, db="database/example_database.json"):
        signal.signal(signal.SIGALRM, self.timeout_handler)
        
        self.db_path = db
        self.db = MeshDB(self.db_path)
        
        self.iaci = interactive_device
        self.iaci.event_filter_disable()

        self.logger = self.iaci.logger

        self.address_stack = list()
        self.devkey_handle_stack = list()
        self.message_que = list()
        
        self.iaci.acidev.add_packet_recipient(self.deviceStarted)
        self.iaci.send(cmd.RadioReset())

        if self.QUICK_SETUP:
            self.onNewUnProvisionedDevice = lambda device : self.provision(device["uuid"])
            self.onProvisionComplete = lambda uuid : self.configure(uuid) 
            self.onCompositionDataStatus = lambda uuid, compositionData : self.addAppKeys(uuid.hex())
            self.onAddAppKeysComplete = lambda uuid : self.provisionScanStart()

    def setup(self):
        # setup is called when the serial device is booted
        self.p = Provisioner(self.iaci, self.db)
        self.cc = ConfigurationClient(self.db)
        self.iaci.model_add(self.cc)

        self.init_event_handlers()
        self.iaci.acidev.add_command_recipient(self.cmd_handler)

        # subprocess.call(["cp", "database/example_database.json.backup", "database/example_database.json"])
        
        self.load_address_handles()
        self.load_devkey_handles()

        if len(self.db.models) > 0:
            self.load_models()
        else:
            self.add_models()

        # TODO add dummy func to clear steup..?
        self.send_next_message()
        
    def load_address_handles(self):        
        address_handles = self.db.address_handles.copy()
        self.db.address_handles = []
        self.db.store()
        
        for item in address_handles:

            address = item["address"]
            opcode = item["opcode"]

            if RESPONSE_LUT[opcode]["name"] == "AddrSubscriptionAdd":
                command = cmd.AddrSubscriptionAdd(address)
            if RESPONSE_LUT[opcode]["name"] == "AddrSubscriptionAddVirtual":
                command = cmd.AddrSubscriptionAddVirtual(address)
            if RESPONSE_LUT[opcode]["name"] == "AddrPublicationAdd":
                command = cmd.AddrPublicationAdd(address)
            if RESPONSE_LUT[opcode]["name"] == "AddrPublicationAddVirtual":
                command = cmd.AddrPublicationAddVirtual(address)
            
            self.message_que.append(functools.partial(self.iaci.send, command))

    def load_devkey_handles(self):

        devkey_handles = self.db.devkey_handles.copy()
        self.db.devkey_handles = []
        self.db.store()
        for item in devkey_handles:
            key = bytearray.fromhex(item["key"])
            command = cmd.DevkeyAdd(item["device_address"], item["subnet_handle"], key)
            self.message_que.append(functools.partial(self.iaci.send, command))

    def load_models(self):

        db_models = self.db.models.copy()
        self.db.models = []

        for model in db_models:

            tid = model["tid"]
                
            if model["model"] == "GenericOnOffClient":
                self.addGenericClientModel()
                setattr(self.gc, "_GenericOnOffClient__tid", tid)
            
            if model["model"] == "GenericOnOffServer":
                self.addGenericServerModel()
                setattr(self.gs, "_GenericOnOffServer__tid", tid)
                
            if model["model"] == "SimpleOnOffClient":
                self.addSimpleClientModel()
                setattr(self.sc, "_SimpleOnOffClient__tid", tid)

    def add_models(self):
        self.addGenericClientModel()
        self.addGenericServerModel()
        self.addSimpleClientModel()

    """""""""""""""""""""""""""""""""""""""""""""
    PYACI EVENTS HANDLER
    """""""""""""""""""""""""""""""""""""""""""""

    def init_event_handlers(self):
        add_event = self.iaci.acidev.add_packet_recipient

        add_event(self.newUnProvisionedDeviceEventHandler)
        add_event(self.provisionCompleteEventHandler)
        add_event(self.compositionDataStatusEventHandler)
        add_event(self.modelAddressStatusEventHandler)
        add_event(self.cmdRsp_handler)

    def deviceStarted(self, event):
        if event._opcode != evt.Event.DEVICE_STARTED:
            return

        self.setup()

    def newUnProvisionedDeviceEventHandler(self, event):
        if event._opcode != evt.Event.PROV_UNPROVISIONED_RECEIVED:
            return

        uuid = event._data["uuid"]
        rssi = event._data["rssi"]

        if uuid not in self.p.unprov_list:
            return

        device = {
            "uuid": uuid.hex(),
            "rssi": rssi
        }

        if hasattr(self, "onNewUnProvisionedDevice"):
            self.onNewUnProvisionedDevice(device)

    def provisionCompleteEventHandler(self, event):
        if event._opcode != evt.Event.PROV_COMPLETE:
            return

        address = int(event._data["address"])
        node, element = self.src_address_to_node_element_index(address)
        uuid = self.db.nodes[node].UUID.hex()
        
        if hasattr(self, "onProvisionComplete"):
            threading.Timer(10, self.onProvisionComplete, args=(uuid,)).start()

    def compositionDataStatusEventHandler(self, event):
        if event._opcode != evt.Event.MESH_MESSAGE_RECEIVED_UNICAST:
            if event._opcode != evt.Event.MESH_MESSAGE_RECEIVED_SUBSCRIPTION:
                return
            
        message = access.AccessMessage(event)
        opcode = message.opcode_raw.hex()
    
        if opcode != str(ConfigurationClient._COMPOSITION_DATA_STATUS):
            return

        data = message.data[1:]
        compositionData = mt.CompositionData().unpack(data)

        src = message.meta["src"]
        node, element = self.src_address_to_node_element_index(src)
        uuid = self.db.nodes[node].UUID

        if hasattr(self, "onCompositionDataStatus"):
            self.onCompositionDataStatus(uuid, compositionData)

    def modelAddressStatusEventHandler(self, event):
        if event._opcode != evt.Event.MESH_MESSAGE_RECEIVED_UNICAST:
            if event._opcode != evt.Event.MESH_MESSAGE_RECEIVED_SUBSCRIPTION:
                return
            
        message = access.AccessMessage(event)
        opcode = message.opcode_raw.hex()

        if opcode == str(ConfigurationClient._MODEL_PUBLICATION_STATUS) or \
            opcode == str(ConfigurationClient._MODEL_SUBSCRIPTION_STATUS) or \
            opcode == str(ConfigurationClient._MODEL_APP_STATUS):
            
                self.send_next_message()

    def cmdRsp_handler(self, event):

        if event._opcode != evt.Event.CMD_RSP:
            return
            
        if event._data["status"] != 0:
            return

        rsp_packet = cmd.response_deserialize(event)

        if rsp_packet is None or isinstance(rsp_packet, str):
            return
                
        if rsp_packet._command_name in ["AddrSubscriptionAdd", "AddrSubscriptionAddVirtual", "AddrPublicationAddVirtual", "AddrPublicationAdd"]:
            self.addrAdd(rsp_packet)

        if rsp_packet._command_name in ["DevkeyAdd"]:
            self.devkeyAdd(rsp_packet)
        
        if rsp_packet._command_name in ["AddrPublicationRemove"]:
            self.addrRemove(rsp_packet)
        
        if rsp_packet._command_name in ["DevkeyDelete"]:
            self.devKeyDelete(rsp_packet)

    def addrAdd(self, rsp_packet):
        try:
            
            new_address = self.address_stack.pop(0)
            address_handle = {
                "address": new_address["address"]
                , "address_handle": rsp_packet._data["address_handle"]
                , "opcode": rsp_packet._opcode
            }
            
            dups = [a for a in self.db.address_handles if a["address_handle"] == address_handle["address_handle"]]
            if len(dups) > 0:
                for dup in dups:
                    if dup != address_handle:
                        raise Exception("Address handle already exists")

                self.logger.debug("Got duplicate of address handle {}".format(address_handle))
            else:
                self.db.address_handles.append(address_handle)
                self.db.store()

            self.send_next_message()

        except Exception as e:
            self.logger.error("Error storing address handle: {}".format(e))
    
    def devkeyAdd(self, rsp_packet):
        try:
            new_device_address = self.devkey_handle_stack.pop(0)
            devkey_handle = rsp_packet._data["devkey_handle"]
            new_device_address["devkey_handle"] = devkey_handle
            self.db.devkey_handles.append(new_device_address)
            self.db.store()
            self.send_next_message()
        
        except Exception as e:
            self.logger.error("Error storing device handle: {}".format(e))

    def addrRemove(self, rsp_packet):
        address_handle = rsp_packet._data["address_handle"]
        self.db.remove_address_handle(address_handle)
        self.db.store()
        self.send_next_message()


    def devKeyDelete(self, rsp_packet):
        devkey_handle = rsp_packet._data["devkey_handle"]
        self.db.remove_devkey_handle(devkey_handle)
        self.db.store()
        self.send_next_message()

    """""""""""""""""""""""""""""""""""""""""""""
    MESH EVENTS
    """""""""""""""""""""""""""""""""""""""""""""

    def addAppKeysComplete(self, uuid):
        self.send_next_message()
        if hasattr(self, "onAddAppKeysComplete"):
            self.onAddAppKeysComplete(uuid)

    def setEventGPIO(self, value, pin, uuid):
        if hasattr(self, "onSetEventGPIO"):
            self.onSetEventGPIO(value, pin, uuid)

    def statusEventGPIO(self, value, pin, uuid):
        if hasattr(self, "onStatusEventGPIO"):
            self.onStatusEventGPIO(value, pin, uuid)

    def setAckFailedEventGPIO(self, pin, uuid):
        if hasattr(self, "onSetAckFailedEventGPIO"):
            self.onSetAckFailedEventGPIO(pin, uuid)

    """""""""""""""""""""""""""""""""""""""""""""
    PYACI CMD HANDLER
    """""""""""""""""""""""""""""""""""""""""""""

    def cmd_handler(self, cmd):
    
        if cmd._opcode in [0xA1, 0xA2, 0xA4, 0xA5]:
            # self.logger.info("CMD Address Handle Handler {}".format(cmd._data.hex()))

            address = struct.unpack("<H", cmd._data[0:2])[0]
            self.address_stack.append({
                "address": address,
                "opcode": cmd._opcode
            })
        
        if cmd._opcode == 0x9C:
            # self.logger.info("Adding device key {}".format(cmd._data))

            self.devkey_handle_stack.append({
                "device_address": struct.unpack("<H", cmd._data[0:2])[0]
                , "subnet_handle": struct.unpack("<H", cmd._data[2:4])[0]
                , "key": cmd._data[4:].hex()

            })
    
    def send_next_message(self):
        try:
            if len(self.message_que) != 0:
                self.logger.info("\n")
                self.logger.info("Sending next message")
                func = self.message_que.pop(0)
                self.last_message = func
                func()
                signal.setitimer(signal.ITIMER_REAL, 4)
            else:
                self.logger.info("No Messages remaining")
        except Exception as e:
            self.logger.error("Error trying next message function: {}".format(e))

    def send_last_message(self):
        if len(self.message_que) != 0:
            self.last_message()
            signal.setitimer(signal.ITIMER_REAL, 4)

    def timeout_handler(self, signum, frame):
        self.logger.info("Timout handler timeout")
        self.send_last_message()
    
    """""""""""""""""""""""""""""""""""""""""""""
     
    """""""""""""""""""""""""""""""""""""""""""""

    """ PROVISIOING """

    def provisionScanStart(self):
        self.p.scan_start()

    def provision(self, uuid, name="NONAME"):
        
        if len([n for n in self.db.nodes if n.UUID.hex() == uuid]) > 0:
            self.logger.error("uuid {} already in database".format(uuid))
            # TODO - add remove from database and then re-add deivce
            return

        self.p.scan_stop()
        self.p.provision(uuid=uuid, name=name)
    
    def getProvisionedDevices(self):
        devices = []
        for node in self.db.nodes:
            devices.append({
                "uuid" : node.UUID,
                "name" : node.name,
            })
            # TODO - add configured / provisioned fields...
        return devices
    
    """ CONFIGURATION """

    def configure(self, uuid):
        node = self.uuid_to_node_index(uuid)
        address = self.db.nodes[node].unicast_address
        address_handle = self.db.find_address_handle(address)
        devkey_handle = self.db.find_devkey_handle(address)
        self.logger.info("Configure {} {}".format(devkey_handle, address_handle))

        self.cc.publish_set(devkey_handle, address_handle)
        try:
            self.cc.composition_data_get()
            self.cc.appkey_add(0)
        except RuntimeError as e:
            self.logger.error(e)
             
    def addAppKeys(self, uuid, groupAddrId=0):
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
        node = self.uuid_to_node_index(uuid)
        command = cmd.AddrSubscriptionAdd(self.db.groups[groupAddrId].address)
        self.message_que.append(functools.partial(self.iaci.send, command))

        for e, element in enumerate(self.db.nodes[node].elements):
            
            # Add each element to the serial device's pubusb list
            element_address = self.db.nodes[node].unicast_address + e
            command = cmd.AddrPublicationAdd(element_address)
            self.message_que.append(functools.partial(self.iaci.send, command))

            for model in element.models:
                
                # Generic OnOff Server
                if str(model.model_id) == "1000":
                    self.message_que.append(functools.partial(self.cc.model_app_bind, element_address, 0, mt.ModelId(0x1000)))
                    
                # Generic OnOff Client
                if str(model.model_id) == "1001":
                    self.message_que.append(functools.partial(self.cc.model_app_bind, element_address, 0, mt.ModelId(0x1001)))
                    self.message_que.append(functools.partial(self.cc.model_publication_set, element_address, mt.ModelId(0x1001), mt.Publish(self.db.groups[groupAddrId].address, index=0, ttl=1)))

                # Simple OnOff Server
                if str(model.model_id) == "00590000":
                    self.message_que.append(functools.partial(self.cc.model_app_bind, element_address, 0, mt.ModelId(0x0000, company_id=0x0059)))

        self.message_que.append(functools.partial(self.addAppKeysComplete, uuid))

        self.send_next_message()

    """  MODELS & PINS """

    def configureGPIO(self, asInput, pin, uuid):
        address_handle = self.get_address_handle(pin, uuid)
        if address_handle is None:
            self.logger.error("Address handle not valid")
            return
            
        self.sc.publish_set(key_handle=0, address_handle=address_handle) # key_handle is app key
        self.sc.set(asInput)
        self.db.store()

    def setGPIO(self, value, pin, uuid):
        address_handle = self.get_address_handle(pin, uuid)
        if address_handle is None:
            self.logger.error("Address handle not valid")
            return

        self.gc.publish_set(key_handle=0, address_handle=address_handle)
        self.gc.set(value)
        self.db.store()

    def getGPIO(self, pin, uuid):
        address_handle = self.get_address_handle(pin, uuid)
        if address_handle is None:
            self.logger.error("Address handle not valid")
            return

        self.gc.publish_set(key_handle=0, address_handle=address_handle)
        self.gc.get()

    def setName(self, name, uuid):
        node = self.uuid_to_node_index(uuid)
        self.db.nodes[node].name = name
    
    def genericOnOffServerSetUnackEvent(self, value, src):
        node, element = self.src_address_to_node_element_index(src)
        uuid = self.db.nodes[node].UUID
        self.setEventGPIO(value, self.element_index_to_pin(element), uuid)
        self.db.store()

    def genericOnOffClientStatusEvent(self, value, src):
        node, element = self.src_address_to_node_element_index(src)
        uuid = self.db.nodes[node].UUID
        self.statusEventGPIO(value, self.element_index_to_pin(element), uuid)

    def setAckFailed(self, address_handle):
        src = self.db.address_handle_to_src(address_handle)
        node, element = self.src_address_to_node_element_index(src)
        uuid = self.db.nodes[node].UUID
        self.setAckFailedEventGPIO(self.element_index_to_pin(element), uuid)

    """  INIT MODELS """

    def addGenericClientModel(self):
        self.gc = GenericOnOffClient(self.db, self.genericOnOffClientStatusEvent, self.setAckFailed)
        self.iaci.model_add(self.gc)
        self.db.models.append(self.gc)
    
    def addGenericServerModel(self):
        self.gs = GenericOnOffServer(self.genericOnOffServerSetUnackEvent, self.db)
        self.iaci.model_add(self.gs)
        self.db.models.append(self.gs)

    def addSimpleClientModel(self):
        self.sc = SimpleOnOffClient()
        self.iaci.model_add(self.sc)
        self.db.models.append(self.sc)

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
            element_index += self.NRF52_STARTING_ELEMENT_INDEX
            return element_index
        
        return None

    def element_index_to_pin(self, element_index):
        element_index -= self.NRF52_STARTING_ELEMENT_INDEX
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
        
        return None

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

    """""""""""""""""""""""""""""""""""""""""""""
    UNUSED / EXPERIMENTAL
    """""""""""""""""""""""""""""""""""""""""""""

    def remove_node(self, uuid):
        self.logger.error("Remove node {} from database".format(uuid))
        node = self.db.get_node(uuid)

        # unprovision node
        address_handle = self.db.find_address_handle(node.unicast_address)
        self.cc.publish_set(0, address_handle)
        self.cc.node_reset();

        # TODO - should this all occur after node_reset_status occurs..?
        
        for element in node.elements: 
            unicast_address = node.unicast_address + element.index
            address_handle = self.db.find_address_handle(unicast_address)

            # delete each address handle from serial device
            # if address["opcode"] == 0xA4:
            command = cmd.AddrPublicationRemove(address_handle)
            self.message_que.append(functools.partial(self.iaci.send, command))
            # else:
                # raise Exception("Did not remove the address_hanlde {}".format(address["address_handle"]))

            # delete each address handle from db
            # TODO in response delete address_handle and send next message()
            # self.db.address_handles.remove(handle)
            # might need to remove subscription of device form serial..
            
        # remove device handle
        devkey_handle = self.db.find_devkey_handle(node.unicast_address)
        command = cmd.DevkeyDelete(devkey_handle)
        self.message_que.append(functools.partial(self.iaci.send, command))

        # ADD a function that waps this function and adds send next message
        self.message_que.append(functools.partial(self.db.nodes.remove, node))

        self.send_next_message()
