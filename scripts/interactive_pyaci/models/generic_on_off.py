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

from mesh.access import Model, Opcode
from models.common import TransitionTime
import struct
import json

import threading

class GenericOnOffClient(Model):
    GENERIC_ON_OFF_SET = Opcode(0x8202, None, "Generic OnOff Set")
    GENERIC_ON_OFF_SET_UNACKNOWLEDGED = Opcode(0x8203, None, "Generic OnOff Set Unacknowledged")
    GENERIC_ON_OFF_GET = Opcode(0x8201, None, "Generic OnOff Get")
    GENERIC_ON_OFF_STATUS = Opcode(0x8204, None, "Generic OnOff Status")

    ACK_TIMER_TIMEOUT = 0.3
    RETRANSMISSIONS_LIMIT = 10

    retry_log = []

    def __init__(self, db=None, tid=0, generic_on_off_client_status_cb=None, set_ack_failed_cb=None):
        self.db = db
        self.opcodes = [
            (self.GENERIC_ON_OFF_STATUS, self.__generic_on_off_status_handler)]
        self.__tid = tid

        self.__generic_on_off_client_status_cb = generic_on_off_client_status_cb
        self.__client_set_ack_failed_cb = set_ack_failed_cb

        self.timers = {}

        super(GenericOnOffClient, self).__init__(self.opcodes)

    def set(self, value, transition_time_ms=0, delay_ms=0, ack=True):
        message = bytearray()
        message += struct.pack("<BB", int(value > 0), self._tid)

        if transition_time_ms > 0:
            message += TransitionTime.pack(transition_time_ms, delay_ms)

        if ack:
            self.send(self.GENERIC_ON_OFF_SET, message)
            self.start_timer(self.address_handle, value)

        else:
            self.send(self.GENERIC_ON_OFF_SET_UNACKNOWLEDGED, message)

    def start_timer(self, address_handle, value):
        
        if address_handle not in self.timers:
            self.timers[address_handle] = {"attempt": 0, "value": value}
        else:
            self.cancel_timer(address_handle)

        if value is not self.timers[address_handle]["value"]:
            self.timers[address_handle]["attempt"] = 0

        self.timers[address_handle]["value"] = value

        timeout = (self.timers[address_handle]["attempt"] + 1) * self.ACK_TIMER_TIMEOUT
        self.timers[address_handle]["timer"] = threading.Timer(timeout, self.set_ack_timedout, args=(address_handle, value,))
        self.timers[address_handle]["timer"].start()
        

    def cancel_timer(self, address_handle):
        if hasattr(self.timers[address_handle]["timer"], "cancel"):
            self.timers[address_handle]["timer"].cancel()


    def set_ack_timedout(self, address_handle, value):
        # SET ACK FAILED - RESET AND DO CB
        self.logger.info("Set ACK {} Timedout".format(address_handle))

        if self.timers[address_handle]["attempt"] < self.RETRANSMISSIONS_LIMIT:
            self.publish_set(0, address_handle)
            self.timers[address_handle]["attempt"] += 1
            self.set(value)
            self.logger.info("Resending SET {} attempts: {}".format(address_handle, self.timers[address_handle]["attempt"]))
            self.retry_log.append({
                "attempt": self.timers[address_handle]["attempt"],
                "address_handle": address_handle
            })
            return


        self.retry_log.append({
            "attempt": "FAILED",
            "address_handle": address_handle
        })

        self.timers[address_handle]["attempt"] = 0
        try:
            self.__client_set_ack_failed_cb(address_handle)
        except Exception as e:
            self.logger.error("Set ACK callback {} failed: {}".format(self.__client_set_ack_failed_cb, e))

    def get(self):
        self.send(self.GENERIC_ON_OFF_GET)

    @property
    def _tid(self):
        tid = self.__tid
        self.__tid += 1
        if self.__tid >= 255:
            self.__tid = 0
        return tid

    def __generic_on_off_status_handler(self, opcode, message):
        value = int(message.data.hex()[1])
        src = message.meta["src"]

        self.logger.info("Status Present OnOff: " + ("on" if value > 0 else "off"))

        # stop timer..
        address_handle = self.db.src_to_address_handle(src)
        if address_handle in self.timers:
            self.logger.info("Got status from src: {} - canceling timer".format(src))
            self.cancel_timer(address_handle)
            self.timers[address_handle]["attempt"] = 0

        try:    
            self.__generic_on_off_client_status_cb(value, src)
        except:
            self.logger.error("Failed trying generic onoff client status callback: ", self.__generic_on_off_client_status_cb)
  
    def __str__(self):
        return json.dumps({"model": "GenericOnOffClient", "tid": self.__tid})

    def to_json(self):
        return {"model": "GenericOnOffClient", "tid": self.__tid}

class GenericOnOffServer(Model):
    GENERIC_ON_OFF_SET = Opcode(0x8202, None, "Generic OnOff Set")
    GENERIC_ON_OFF_SET_UNACKNOWLEDGED = Opcode(0x8203, None, "Generic OnOff Set Unacknowledged")
    GENERIC_ON_OFF_GET = Opcode(0x8201, None, "Generic OnOff Get")
    GENERIC_ON_OFF_STATUS = Opcode(0x8204, None, "Generic OnOff Status")
    
    def __init__(self, tid=0, generic_on_off_server_set_cb=None, db=None):
        self.opcodes = [
            (self.GENERIC_ON_OFF_SET, self.__generic_on_off_server_set_event_handler),
            (self.GENERIC_ON_OFF_SET_UNACKNOWLEDGED, self.__generic_on_off_server_set_unack_event_handler),
            (self.GENERIC_ON_OFF_GET, self.__generic_on_off_server_get_event_handler)]
        self.__tid = tid
        self.__generic_on_off_server_set_cb = generic_on_off_server_set_cb
        self.db = db

        super(GenericOnOffServer, self).__init__(self.opcodes)
        
    
    @property
    def _tid(self):
        tid = self.__tid
        self.__tid += 1
        if self.__tid >= 255:
            self.__tid = 0
        return tid


    def __generic_on_off_server_set_event_handler(self, opcode, message):

        # UNPACK MESSAGE
        value = int(message.data.hex()[1])
        src = message.meta["src"]
        appkey_handle = message.meta["appkey_handle"]

        logstr = " Set ack OnOff: " + ("on" if value > 0 else "off")
        self.logger.info(logstr)

        # SEND STATUS RESPONSE
        address_handle = self.db.src_to_address_handle(src)
        self.publish_set(appkey_handle, address_handle)
        self.status(value)

        # DO ACTION
        try:
            self.__generic_on_off_server_set_cb(value, src)
        except:
            self.logger.error("Failed trying generic on off server set callback: ", self.__generic_on_off_server_set_unack_cb)


    def __generic_on_off_server_set_unack_event_handler(self, opcode, message):
        # UNPACK MESSAGE
        value = int(message.data.hex()[1])
        src = message.meta["src"]
        
        logstr = " Set unack OnOff: " + ("on" if value > 0 else "off")
        self.logger.info(logstr)

        try:
            self.__generic_on_off_server_set_cb(value, src)
        except:
            self.logger.error("Failed trying generic on off server set unack callback: ", self.__generic_on_off_server_set_unack_cb)

    def __generic_on_off_server_get_event_handler(self, opcode, message):
        self.logger.info("Server GET event {} {}".format(opcode, message.data))


    def status(self, value):
        # TODO what are transition_time_ms and delay_ms doing?

        message = bytearray()
        message += struct.pack("<?", int(value > 0))

        self.send(self.GENERIC_ON_OFF_STATUS, message)

    def __str__(self):
        return json.dumps({"model": "GenericOnOffServer", "tid": self.__tid})

    def to_json(self):
        return {"model": "GenericOnOffServer", "tid": self.__tid}