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

from interactive_pyaci import Manager
m = Manager(d[0])
m.provisionScanStart()
m.provision("9db77a0526b8734988639509c242d107")
m.configure()
m.addAppKeys()
<!-- m.addModels() -->
m.genericClientSet(True, 0)

m.iaci.send(cmd.AddrPublicationAdd(m.db.nodes[0].unicast_address + e))
m.cc.model_app_bind(m.db.nodes[0].unicast_address + e, 0, mt.ModelId(0x1000))
m.cc.model_app_bind(m.db.nodes[0].unicast_address + e, 0, mt.ModelId(0x1001))
m.cc.model_publication_set(m.db.nodes[0].unicast_address + e, mt.ModelId(0x1001), mt.Publish(#prov-unicast-address#, index=0, ttl=1))

m.addGenericServerModel()
m.addGenericClientModel()
m.addSimpleServer()

# 2 is 12
m.genericClientSet(True, 0, 2)
m.simpleServerSet(True, 0, 2)

{"op": "ConfigureGPIO", "data": {"value": "0", "uuid": "9db77a0526b8734988639509c242d107", "pin": 12}}

{"op": "SetGPIO", "data": {"value": "1", "uuid": "9db77a0526b8734988639509c242d107", "pin": 12}}