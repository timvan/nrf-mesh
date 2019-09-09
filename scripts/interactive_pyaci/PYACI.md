db = MeshDB("database/example_database.json")
p = Provisioner(device, db)
p.scan_start()
p.scan_stop()
p.provision(name="Client")
cc = ConfigurationClient(db)
device.model_add(cc)
cc.publish_set(8, 0)
cc.composition_data_get()

cc.appkey_add(0)
cc.model_app_bind(db.nodes[0].unicast_address + 1, 0, mt.ModelId(0x1001))
cc.model_app_bind(db.nodes[0].unicast_address + 1, 0, mt.ModelId(0x1000))
cc.model_app_bind(db.nodes[0].unicast_address + 2, 0, mt.ModelId(0x1001))

device.event_filter_disable()
d[0].send(cmd.AddrPublicationAdd(db.groups[0].address))
d[0].send(cmd.AddrSubscriptionAdd(db.groups[0].address)) # note sub vs pub of device address

cc.model_subscription_add(db.nodes[0].unicast_address + 1, db.groups[0].address, mt.ModelId(0x1001))
cc.model_subscription_add(db.nodes[0].unicast_address + 2, db.groups[0].address, mt.ModelId(0x1001))
cc.model_publication_set(db.nodes[0].unicast_address + 1, mt.ModelId(0x1001), mt.Publish(db.groups[0].address, index=0, ttl=1))
cc.model_publication_set(db.nodes[0].unicast_address + 2, mt.ModelId(0x1001), mt.Publish(db.groups[0].address, index=0, ttl=1))


gs = GenericOnOffServer()
device.model_add(gs)
gs.publish_set(0, 1)


gc = GenericOnOffClient()
device.model_add(gc)
gc.publish_set(0, 1)


cc.model_publication_set(db.appKeys[0].key, mt.ModelId(0x1001), mt.Publish(db.groups[0].address, index=0, ttl=1))


<!--  -->

from interactive_pyaci import Mesh
m = Mesh(d[0])
uuid = "e07f87c0e83ff2418b6e5fd50b58c2cd"

uuids = ["e07f87c0e83ff2418b6e5fd50b58c2cd", "9db77a0526b8734988639509c242d107", "8d875f5b77f9534d86aa7ce47836497c" ,"696fd66b16c91d4ebcc34a36f44920f2"]

uuid = uuids[3]

uuid = "8d875f5b77f9534d86aa7ce47836497c"

m.provisionScanStart()
m.provision(uuid, "device")
m.configure(uuid)
m.addAppKeys(uuid)


<!-- set as output -->
m.configureGPIO(False, 18, uuid)
m.setGPIO(True, 18, uuid)
m.setGPIO(False, 18, uuid)

<!-- set as input -->
m.configureGPIO(False, 18, uuid)

<!-- get -->
m.getGPIO(18, uuid)

<!-- m.addModels() -->
m.genericClientSet(True, 0)

m.iaci.send(cmd.AddrPublicationAdd(m.db.nodes[0].unicast_address + e))
m.cc.model_app_bind(m.db.nodes[0].unicast_address + e, 0, mt.ModelId(0x1000))
m.cc.model_app_bind(m.db.nodes[0].unicast_address + e, 0, mt.ModelId(0x1001))
m.cc.model_publication_set(m.db.nodes[0].unicast_address + e, mt.ModelId(0x1001), mt.Publish(#prov-unicast-address#, index=0, ttl=1))

m.addGenericServerModel()
m.addGenericClientModel()
m.addSimpleServer()

m.p.scan_stop()

# 2 is 12
m.genericClientSet(True, 0, 2)
m.simpleServerSet(True, 0, 2)

{"op": "ConfigureGPIO", "data": {"asInput": 0, "uuid": "e07f87c0e83ff2418b6e5fd50b58c2cd", "pin": 18}}

{"op": "SetGPIO", "data": {"value": 1, "uuid": "e07f87c0e83ff2418b6e5fd50b58c2cd", "pin": 18}}

{"op": "GetGPIO", "data": {"value": 1, "uuid": "e07f87c0e83ff2418b6e5fd50b58c2cd", "pin": 18}}


<!-- TEST -->
from interactive_pyaci import Mesh
m = Mesh(d[0])

uuids = ["e07f87c0e83ff2418b6e5fd50b58c2cd", "9db77a0526b8734988639509c242d107", "8d875f5b77f9534d86aa7ce47836497c" ,"696fd66b16c91d4ebcc34a36f44920f2"]
pins = [12, 13, 14 , 15]
from tester.tester import Tester
t = Tester(pins, uuids, m, 6, 0)

t.run4(timeout=1, run_times=1000, value=True)

t.run2(100, [0], 1)
t.setup(False)
t.reset(False)
t.standup_standdown(x_send=3, delay_between_messages=0, interval_between_group_set=2)

setattr(m.gc, "ACK_TIMER_TIMEOUT", 0.05)
setattr(m.gc, "RETRIES", 2)


uuid = "e07f87c0e83ff2418b6e5fd50b58c2cd"
pin = 12
value = False


for i in range(2):
    value = not value
    m.setGPIO(not value, pin, uuid)


value = not value
m.setGPIO(not value, pin, uuid)

m.gc.timers



 10
def set_all(m, uuids, pins, value, TIMEOUT, threading):
    for pin in pins: 
        for uuid in uuids: 
            m.setGPIO(value, pin, uuid)
    
    threading.Timer(TIMEOUT, set_all, (m, uuids, pins, value, TIMEOUT, threading)).start()

TIMEOUT = 1
threading.Timer(TIMEOUT, set_all, (m, uuids, pins, value, TIMEOUT, threading)).start()


t.run4(1, 10, True)

t.keeprunning = False

def retries(m):

    for i in range(10):
        print(i, len([x for x in m.gc.retry_log if x['attempt'] == i ]))

    m.gc.retry_log = []




<!-- LG STACKS -->

from interactive_pyaci import Mesh
m = Mesh(d[0])
uuids = ["9db77a0526b8734988639509c242d107", "8d875f5b77f9534d86aa7ce47836497c"]
pins = [12, 13, 14 , 15]


for pin in pins:
    for uuid in uuids:
        m.configureGPIO(False, pin, uuid)
        m.setGPIO(True, pin, uuid)
    
