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
import struct
import json

class SimpleOnOffClient(Model):
    SIMPLE_ON_OFF_STATUS = Opcode(0xc4, 0x59, "Simple OnOff Status")
    SIMPLE_ON_OFF_SET = Opcode(0xc1, 0x59, "Simple OnOff Set")
    SIMPLE_ON_OFF_GET = Opcode(0xc2, 0x59, "Simple OnOff Get")
    SIMPLE_ON_OFF_SET_UNACKNOWLEDGED = Opcode(0xc3, 0x59, "Simple OnOff Set Unacknowledged")

    def __init__(self):
        self.opcodes = [
            (self.SIMPLE_ON_OFF_STATUS, self.__simple_on_off_status_handler)]
        self.__tid = 0
        super(SimpleOnOffClient, self).__init__(self.opcodes)

    def set(self, state):
        message = bytearray()
        message += struct.pack("<BB", int(state), self._tid)
        self.send(self.SIMPLE_ON_OFF_SET, message)

    def get(self):
        self.send(self.SIMPLE_ON_OFF_GET)

    def unacknowledged_set(self, state):
        message = bytearray()
        message += struct.pack("<BB", int(state), self._tid)
        self.send(self.SIMPLE_ON_OFF_SET_UNACKNOWLEDGED, message)

    @property
    def _tid(self):
        tid = self.__tid
        self.__tid += 1
        if self.__tid >= 255:
            self.__tid = 0
        return tid

    def __simple_on_off_status_handler(self, opcode, message):
        on_off = "on" if message.data[0] > 0 else "off"
        self.logger.info("Present value is %s", on_off)

    def __str__(self):
        return json.dumps({"model": "SimpleOnOffClient", "tid": self.__tid})

    def to_json(self):
        return {"model": "SimpleOnOffClient", "tid": self.__tid}