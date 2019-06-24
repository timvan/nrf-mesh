const { spawn } = require('child_process');

const pyaci = spawn('python', ['interactive_pyaci.py']);


pyaci.stdout.on('data', (data) => {
    console.log(data.toString());
});

pyaci.stdin.write('db = MeshDB("database/example_database.json")\n');
pyaci.stdin.write('p = Provisioner(device, db)\n');

setTimeout(() => {
    pyaci.stdin.write('p.scan_start()\n')
    setTimeout(() => {pyaci.stdin.write('p.scan_stop()\n')}, 10000);

}, 10000);




// pyaci.stdin.write('p.provision(name="Server")\n')
// pyaci.stdin.write('cc = ConfigurationClient(db)\n')
// pyaci.stdin.write('device.model_add(cc)\n')
// pyaci.stdin.write('cc.publish_set(8, 0)\n')

// pyaci.stdin.write('cc.composition_data_get()\n')

// pyaci.stdin.write('cc.appkey_add(0)\n')
// pyaci.stdin.write('cc.model_app_bind(db.nodes[0].unicast_address, 0, mt.ModelId(0x1000))\n')

// pyaci.stdin.write('d[0].send(cmd.AddrPublicationAdd(db.groups[0].address))\n')

// pyaci.stdin.write('cc.model_subscription_add(db.nodes[0].unicast_address, db.groups[0].address, mt.ModelId(0x100))\n')

// pyaci.stdin.write('gc = GenericOnOffClient()\n')
// pyaci.stdin.write('device.model_add(gc)\n')
// pyaci.stdin.write('gc.publish_set(0, 1)\n')
// pyaci.stdin.write('gc.set(True)\n')
