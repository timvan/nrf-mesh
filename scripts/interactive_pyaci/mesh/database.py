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

import json
import datetime
import re

from mesh import types as mt

from models.generic_on_off import GenericOnOffClient
from models.generic_on_off import GenericOnOffServer
from models.simple_on_off import SimpleOnOffClient


def snakeify(name):
    all_cap_re = re.compile('([a-z0-9])([A-Z]+)')
    return all_cap_re.sub(lambda m: "%s_%s" % (
        m.group(1), m.group(2).lower() if len(m.group(2)) == 1 else m.group(2)), name)


def snakeify_type(din):
    d = {}
    for k, v in din.items():
        if isinstance(v, dict):
            d[snakeify(k)] = snakeify_type(v)
        elif isinstance(v, list):
            d[snakeify(k)] = [snakeify_type(i) if isinstance(i, dict) else i
                              for i in v]
        else:
            d[snakeify(k)] = v
    return d


class MeshDB(object):
    def __init__(self, path):
        self.__path = path
        self.__schema = ""
        self.mesh_name = ""
        self.mesh_UUID = None
        self.net_keys = []
        self.app_keys = []
        self.provisioners = []
        self.nodes = []
        self.groups = []
        self.iv_index = 0
        self.iv_update = 0

        self.models = []

        self.load()

    @property
    def timestamp(self):
        return datetime.datetime.now().isoformat(' ')

    def load(self, path=None):
        if not path:
            path = self.__path
        with open(path, "r") as f:
            data = snakeify_type(json.load(f))

        self.__schema = data["$schema"]
        self.mesh_name = data["mesh_name"]
        self.mesh_UUID = mt._UUID(data["mesh_UUID"])
        self.net_keys = [mt.Netkey(**key) for key in data["net_keys"]]
        self.app_keys = [mt.Appkey(**key) for key in data["app_keys"]]
        self.provisioners = [mt.Provisioner(**p) for p in data["provisioners"]]

        if "nodes" in data:
            self.nodes = [mt.Node(**n) for n in data["nodes"]]
        if "groups" in data:
            self.groups = [mt.Group(**g) for g in data["groups"]]
        if "iv_index" in data:
            self.iv_index = data["iv_index"]
        if "iv_update" in data:
            self.iv_update = data["iv_update"]

        if "models" in data:
            self.models = data["models"]

    def store(self, path=None):
        data = mt.camelify_object(self)
        data["$schema"] = self.__schema
        data["timestamp"] = self.timestamp

        if not path:
            path = self.__path
        with open(path, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def find_appkey(self, key_index):
        for key in self.app_keys:
            if key.index == key_index:
                return key

        return None

    def find_netkey(self, key_index):
        for key in self.net_keys:
            if key.index == key_index:
                return key

        return None

    def src_to_address_handle(self, src):
        for node in self.nodes:
            for element in node.elements:
                if node.unicast_address + element.index == src:
                    return element.address_handle

    def address_handle_to_src(self, address_handle):
        for node in self.nodes:
            for element in node.elements:
                if element.address_handle == address_handle:
                    return element.unicast_address

    
    def find_devkey_handle(self, address):
        for node in self.nodes:
            if node.unicast_address == address:
                return node.devkey_handle
        
        return None

    def get_node(self, uuid):
        nodes = [n for n in self.nodes if n.UUID.hex() == uuid]
        if len(nodes) > 1:
            raise Exception("Error multiple instances on node with uuid: {}".format(uuid))

        return nodes[0]
        
    # def remove_address_handle(self, address_handle):
    #     self.address_handles = [x for x in self.address_handles if x["address_handle"] != address_handle]

    # def remove_devkey_handle(self, devkey_handle):
    #     self.devkey_handles = [x for x in self.devkey_handles if x["devkey_handle"] != devkey_handle]

    
    def uuid_to_node_index(self, uuid):
        for n, node in enumerate(self.nodes):
            if uuid == node.UUID.hex():
                return n
        
        return None


    def src_address_to_node_element_index(self, src_address):
        for node_index, node in enumerate(self.nodes):
            for element_index, element in enumerate(node.elements):
                
                if int(node.unicast_address + element_index) == src_address:
                    return node_index, element_index



