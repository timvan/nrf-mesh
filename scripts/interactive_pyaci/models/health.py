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

class Health(Model):
    HEALTH_CURRENT_STATUS               = Opcode(0x04, None, "Health Current Status")
    HEALTH_FAULT_STATUS          = Opcode(0x05, None, "HEALTH FAULT_STATUS")
    HEALTH_ATTENTION_GET         = Opcode(0x8004, None, "HEALTH ATTENTION_GET")
    HEALTH_ATTENTION_SET         = Opcode(0x8005, None, "HEALTH ATTENTION_SET")
    HEALTH_ATTENTION_SET_UNACKED = Opcode(0x8006, None, "HEALTH ATTENTION_SET_UNACKED")
    HEALTH_ATTENTION_STATUS      = Opcode(0x8007, None, "HEALTH ATTENTION_STATUS")
    HEALTH_FAULT_CLEAR           = Opcode(0x802f, None, "HEALTH FAULT_CLEAR")
    HEALTH_FAULT_CLEAR_UNACKED   = Opcode(0x8030, None, "HEALTH FAULT_CLEAR_UNACKED")
    HEALTH_FAULT_GET             = Opcode(0x8031, None, "HEALTH FAULT_GET")
    HEALTH_FAULT_TEST            = Opcode(0x8032, None, "HEALTH FAULT_TEST")
    HEALTH_FAULT_TEST_UNACKED    = Opcode(0x8033, None, "HEALTH FAULT_TEST_UNACKED")
    HEALTH_PERIOD_GET            = Opcode(0x8034, None, "HEALTH PERIOD_GET")
    HEALTH_PERIOD_SET            = Opcode(0x8035, None, "HEALTH PERIOD_SET")
    HEALTH_PERIOD_SET_UNACKED    = Opcode(0x8036, None, "HEALTH PERIOD_SET_UNACKED")
    HEALTH_PERIOD_STATUS         = Opcode(0x8037, None, "HEALTH PERIOD_STATUS")

    def __init__(self, tid=0):
        self.opcodes = [
            (self.HEALTH_CURRENT_STATUS, self.__health_current_status_handler),
            (self.HEALTH_FAULT_STATUS, self.__health_current_status_handler),
            (self.HEALTH_ATTENTION_GET, self.__health_current_status_handler),
            (self.HEALTH_ATTENTION_SET, self.__health_current_status_handler),
            (self.HEALTH_ATTENTION_SET_UNACKED, self.__health_current_status_handler),
            (self.HEALTH_ATTENTION_STATUS, self.__health_current_status_handler),
            (self.HEALTH_FAULT_CLEAR, self.__health_current_status_handler),
            (self.HEALTH_FAULT_CLEAR_UNACKED, self.__health_current_status_handler),
            (self.HEALTH_FAULT_GET, self.__health_current_status_handler),
            (self.HEALTH_FAULT_TEST, self.__health_current_status_handler),
            (self.HEALTH_FAULT_TEST_UNACKED, self.__health_current_status_handler),
            (self.HEALTH_PERIOD_GET, self.__health_current_status_handler),
            (self.HEALTH_PERIOD_SET, self.__health_current_status_handler),
            (self.HEALTH_PERIOD_SET_UNACKED, self.__health_current_status_handler),
            (self.HEALTH_PERIOD_STATUS, self.__health_current_status_handler)
        ]

        self.__tid = tid
        super(Health, self).__init__(self.opcodes)

    def get_status(self):
        self.send(self.HEALTH_CURRENT_STATUS)

    def period_set(self, fast_period_divisor):
        message = bytearray()
        message += struct.pack("<B", int(fast_period_divisor))
        self.send(self.HEALTH_PERIOD_SET, message)

    @property
    def _tid(self):
        tid = self.__tid
        self.__tid += 1
        if self.__tid >= 255:
            self.__tid = 0
        return tid

    def __health_current_status_handler(self, opcode, message):
        self.logger.info("Health status got this: %s", message)

    def __str__(self):
        return json.dumps({"model": "Health", "tid": self.__tid})

    def to_json(self):
        return {"model": "Health", "tid": self.__tid}