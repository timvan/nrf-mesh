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
        
        self.db_path = db
        self.db = MeshDB(self.db_path)
        
        self.iaci = interactive_device
        self.iaci.event_filter_disable()

        self.logger = self.iaci.logger

        self.address_stack = list()
        self.devkey_handle_stack = list()
        self.message_que = list()
        
        self.p = Provisioner(self.iaci, self.db, provisioning_complete_cb=self.provisioning_complete)
        self.cc = MeshConfigurer(self.db, self.iaci, self.composition_data_status, self.add_app_keys_complete)
        self.iaci.model_add(self.cc)
        self.add_event_handlers()
        self.tid_found = True

        if len(self.db.models) > 0:
            self.load_models()
        else:
            self.add_models()


        self.iaci.acidev.add_packet_recipient(self.deviceStarted)
        # self.iaci.send(cmd.RadioReset())
        self.setup()

        if self.QUICK_SETUP:
            self.onNewUnProvisionedDevice = lambda device : self.provision(device["uuid"])
            self.onProvisionComplete = lambda uuid : self.configure(uuid) 
            self.onCompositionDataStatus = lambda uuid, compositionData : self.add_app_keys(uuid)
            self.onAddAppKeysComplete = lambda uuid : self.provisionScanStart()

    def setup(self):
        # setup is called when the serial device is booted
        # self.p.resend_key_pair
        self.p.load(self.p.prov_db)
        if len(self.db.nodes) > 0:
            self.add_address_handles_to_serial()
            self.add_devkey_handles_to_serial()
            self.cc.send_next_command()
        
        # self.find_tid()

    def add_address_handles_to_serial(self):
        for node in self.db.nodes:
            self.cc.add_node_addresses_to_serial(node)
    
    def add_devkey_handles_to_serial(self):
        for node in self.db.nodes:
            self.cc.add_devkey_to_serial(node)
    
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

    def add_event_handlers(self):
        add_event = self.iaci.acidev.add_packet_recipient
        add_event(self.newUnProvisionedDeviceEventHandler)
        add_event(self.cmd_rsp_handler)

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


    def cmd_rsp_handler(self, event):
        if self.tid_found:
            return

        if event._opcode != evt.Event.CMD_RSP:
            return
            
        if event._data["status"] != 0:
            return

        rsp_packet = cmd.response_deserialize(event)

        if rsp_packet is None or isinstance(rsp_packet, str):
            return
    
        if rsp_packet._opcode == 0x8201:
            self.tid_found = True
        
    """""""""""""""""""""""""""""""""""""""""""""
    MESH EVENTS
    """""""""""""""""""""""""""""""""""""""""""""

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
    
    def provisioning_complete(self):
        if hasattr(self, "onProvisionComplete"):
            uuid = self.db.nodes[-1].UUID.hex()
            threading.Timer(10, self.onProvisionComplete, args=(uuid,)).start()

    """ CONFIGURATION """

    def configure(self, uuid):
        self.cc.configure(uuid)
    
    def add_app_keys(self, uuid, groupAddrId=0):
        self.cc.add_app_keys(uuid)

    def composition_data_status(self, uuid, compositionData={}):
        if hasattr(self, "onCompositionDataStatus"):
            self.onCompositionDataStatus(uuid, compositionData)
    
    def add_app_keys_complete(self, uuid):
        if hasattr(self, "onAddAppKeysComplete"):
            self.onAddAppKeysComplete(uuid)

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
        node = self.db.uuid_to_node_index(uuid)
        self.db.nodes[node].name = name
    
    def genericOnOffServerSetUnackEvent(self, value, src):
        node, element = self.db.src_address_to_node_element_index(src)
        uuid = self.db.nodes[node].UUID
        self.setEventGPIO(value, self.element_index_to_pin(element), uuid)
        self.db.store()

    def genericOnOffClientStatusEvent(self, value, src):
        node, element = self.db.src_address_to_node_element_index(src)
        uuid = self.db.nodes[node].UUID
        self.statusEventGPIO(value, self.element_index_to_pin(element), uuid)

    def setAckFailed(self, address_handle):
        src = self.db.address_handle_to_src(address_handle)
        node, element = self.db.src_address_to_node_element_index(src)
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
    EXPERIMENTAL
    """""""""""""""""""""""""""""""""""""""""""""

    def find_tid(self):
        self.tid_found = False
        self.find_again()
    
    def find_again(self):
        address_handle = self.db.nodes[0].elements[0].address_handle
        self.gc.publish_set(0, address_handle)
        if not self.tid_found:
            self.gc.get()
            threading.Timer(0.1, self.find_again).start()

    """""""""""""""""""""""""""""""""""""""""""""
    HELPERS / CONVERTERS
    """""""""""""""""""""""""""""""""""""""""""""

    def get_address_handle(self, pin, uuid):
        element = self.pin_to_element_index(pin)
        node = self.db.uuid_to_node_index(uuid)

        if node != None and element != None:
            address = self.db.nodes[node].unicast_address + element
            return self.db.src_to_address_handle(address)
        
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

class MeshConfigurer(ConfigurationClient):

    def __init__(self, prov_db, iaci, configure_complete_cb, add_app_keys_complete_cb):
        super(MeshConfigurer, self).__init__(prov_db)
        
        self.opcode_update_list = [
            (self._COMPOSITION_DATA_STATUS          , self.__composition_data_status_handler_mesh),
            (self._APPKEY_STATUS                    , self.__appkey_status_handler_mesh),
            (self._MODEL_PUBLICATION_STATUS         , self.__model_publication_status_handler_mesh),
            (self._MODEL_SUBSCRIPTION_STATUS        , self.__model_subscription_status_handler_mesh),
            (self._MODEL_APP_STATUS                 , self.__model_app_status_handler_mesh)
        ]
        self.update_opcode_handlers()

        self.iaci = iaci

        self.command_que = list()
        self.last_message = None
        self._add_app_keys_complete_cb = add_app_keys_complete_cb
        self._configure_complete_cb = configure_complete_cb
        self.timer = None
        
        self.iaci.acidev.add_command_recipient(self.cmd_handler)
        self.iaci.acidev.add_packet_recipient(self.event_handler)


    def que_command(self, command, *args):
        self.command_que.append(
            functools.partial(command, *args)
        )
    
    def send_next_command(self):
        try:
            if hasattr(self.timer, "cancel"):
                self.timer.cancel()

            if len(self.command_que) != 0:
                self.logger.info("\n")
                self.logger.info("Sending next message")
                func = self.command_que.pop(0)
                self.last_message = func
                func()
                
                self.timer = threading.Timer(4, self.send_last_message)
                self.timer.start()
            else:
                self.logger.info("No Messages remaining")
        except Exception as e:
            self.logger.error("Error trying next message function: {}".format(e))
    
    def send_last_message(self):
        self.logger.info("Timout handler timeout")
        if len(self.command_que) != 0:
            self.last_message()
            self.timer = threading.Timer(4, self.send_last_message)
            self.timer.start()


    def configure(self, uuid):
        node = self.prov_db.uuid_to_node_index(uuid)
        address = self.prov_db.nodes[node].unicast_address
        address_handle = self.prov_db.src_to_address_handle(address)
        devkey_handle = self.prov_db.find_devkey_handle(address)
        self.logger.info("Configure {} {}".format(devkey_handle, address_handle))

        self.publish_set(devkey_handle, address_handle)
        self.que_command(self.composition_data_get)
        self.que_command(self.appkey_add, 0)
        self.send_next_command()
             
    def add_app_keys(self, uuid, groupAddrId=0):
        node = self.prov_db.uuid_to_node_index(uuid)
        
        self.add_node_addresses_to_serial(self.prov_db.nodes[node])

        for e, element in enumerate(self.prov_db.nodes[node].elements):
            element_address = self.prov_db.nodes[node].unicast_address + e

            for model in element.models:
                
                # Generic OnOff Server
                if str(model.model_id) == "1000":
                    self.que_command(self.model_app_bind, element_address, 0, mt.ModelId(0x1000))
                    
                # Generic OnOff Client
                if str(model.model_id) == "1001":
                    self.que_command(self.model_app_bind, element_address, 0, mt.ModelId(0x1001))
                    publish = mt.Publish(self.prov_db.groups[groupAddrId].address, index=0, ttl=1)
                    self.que_command(self.model_publication_set, element_address, mt.ModelId(0x1001), publish)

                # Simple OnOff Server
                if str(model.model_id) == "00590000":
                    self.que_command(self.model_app_bind, element_address, 0, mt.ModelId(0x0000, company_id=0x0059))

        # self.que_command(self.addAppKeysComplete, uuid)
        self.que_command(self.__add_app_keys_complete, uuid)

        self.send_next_command()
    
    def add_node_addresses_to_serial(self, node, groupAddrId=0):
        command = cmd.AddrSubscriptionAdd(self.prov_db.groups[groupAddrId].address)
        self.que_command(self.iaci.send, command)
        for e, element in enumerate(node.elements):
            # Add each element to the serial device's pubusb list
            element_address = node.unicast_address + e
            command = cmd.AddrPublicationAdd(element_address)
            self.que_command(self.iaci.send, command)
        
    def add_devkey_to_serial(self, node):
        command = cmd.DevkeyAdd(node.unicast_address, 0, node.device_key)
        self.que_command(self.iaci.send, command)

    # -----------------------------------
    def cmd_handler(self, command):
    
        # AddrPublicationAdd - collect outgoing address to be matched with incoming handle
        if command._opcode == 0xA4:
            address = struct.unpack("<H", command._data[0:2])[0]
            self._temp_address = address
        
        # DeveyAdd - collect outgoing address to be matched with incoming handle
        if command._opcode == 0x9C:
            self._temp_device_addres = struct.unpack("<H", command._data[0:2])[0]


    def event_handler(self, event):
        if event._opcode != evt.Event.CMD_RSP:
            return
            
        if event._data["status"] != 0:
            return

        rsp_packet = cmd.response_deserialize(event)

        if rsp_packet is None or isinstance(rsp_packet, str):
            return

        if rsp_packet._command_name == "AddrPublicationAdd":
            node, element = self.prov_db.src_address_to_node_element_index(self._temp_address)
            self.prov_db.nodes[node].elements[element].address_handle = rsp_packet._data["address_handle"]
            self._temp_address = None
            self.send_next_command()

        if rsp_packet._command_name == "AddrSubscriptionAdd":
            self.send_next_command()

        if rsp_packet._command_name == "DevkeyAdd":
            node, element = self.prov_db.src_address_to_node_element_index(self._temp_device_addres)
            self.prov_db.nodes[node].devkey_handle = rsp_packet._data["devkey_handle"]
            self._temp_device_addres = None
            self.send_next_command()

        if rsp_packet._command_name in ["AddrSubscriptionRemove", "AddrPublicationRemove", "DevkeyDelete"]:
            self.prov_db.store()
            self.send_next_command()


    # -----------------------------------
    def update_opcode_handlers(self):
        for opcode, handler in self.opcode_update_list:
            self.handlers[str(opcode)] = handler

    def __composition_data_status_handler_mesh(self, opcode, message):
        self._ConfigurationClient__composition_data_status_handler(opcode, message)
        node = self.node_get(message.meta["src"])
        self._configure_complete_cb(node.UUID.hex())

    def __appkey_status_handler_mesh(self, opcode, message):
        self._ConfigurationClient__appkey_status_handler(opcode, message)
        self.send_next_command()

    def __model_publication_status_handler_mesh(self, opcode, message):
        self._ConfigurationClient__model_publication_status_handler(opcode, message)
        self.send_next_command()

    def __model_subscription_status_handler_mesh(self, opcode, message):
        self._ConfigurationClient__model_subscription_status_handler(opcode, message)
        self.send_next_command()

    def __model_app_status_handler_mesh(self, opcode, message):
        self._ConfigurationClient__model_app_status_handler(opcode, message)
        self.send_next_command()

    def __add_app_keys_complete(self, uuid):
        self.logger.info("Adding app keys complete")
        self.timer.cancel()
        self._add_app_keys_complete_cb(uuid)


    def remove_node(self, uuid):
        self.logger.error("Remove node {} from database".format(uuid))
        node = self.prov_db.get_node(uuid)

        # unprovision node
        address_handle = node.elements[0].address_handle
        devkey_handle = node.devkey_handle
        self.publish_set(devkey_handle, address_handle)
        self.node_reset()

        
        # TODO - subscription list lost...
        # command = cmd.AddrSubscriptionRemove(node.elements[0].address_handle)
        # self.que_command(self.iaci.send, command)
        
        for element in node.elements: 
            command = cmd.AddrPublicationRemove(element.address_handle)
            self.que_command(self.iaci.send, command)

        # remove device handle
        command = cmd.DevkeyDelete(devkey_handle)
        self.que_command(self.iaci.send, command)

        # ADD a function that waps this function and adds send next message
        self.que_command(self.prov_db.nodes.remove, node)
        
        self.send_next_command()

