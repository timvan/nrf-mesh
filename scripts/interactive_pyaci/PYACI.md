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



cc.model_publication_set(db.appKeys[0].key, mt.ModelId(0x1001), mt.Publish(db.groups[0].address, index=0, ttl=1))