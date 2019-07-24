var PyAci = require('../node-red-contrib-ble-mesh/ble-mesh/Pyaci')
var pyaci = new PyAci().getInstance();

var p = require('process')
p.on('SIGINT', () => {pyaci.kill()});
p.on('uncaughtException', () => {pyaci.kill()});

var bleNodes = {};
var unProvisionedBleNodes = [];

pyaci.setEventsCbs = bleNodes;

function onCompositionDataStatus(data) {
    console.log(`Node configuration `, JSON.stringify(data));
    uuid = data.uuid;
    bleNodes[uuid] = {};
    console.log(bleNodes);
    pyaci.addAppKeys(uuid);
};

function onProvisionComplete() {
    pyaci.configure(onCompositionDataStatus);
    var nodeId = 0;
};

function provision() {
    var uuid = unProvisionedBleNodes.pop().uuid;
    pyaci.provision(onProvisionComplete, uuid);
};

function provision_by_uuid(uuid) {
    
    unProvisionedBleNodes = unProvisionedBleNodes.filter((value) => {
        value.uuid != uuid;
    })

    pyaci.provision(onProvisionComplete, uuid);
}

function onDiscover(data) {

    var inList = unProvisionedBleNodes.filter(o => {return o.uuid === data.uuid});
    if(inList.length === 0){
        unProvisionedBleNodes.push(data);
    }

    if(Object.keys(bleNodes).includes(data.uuid)){
        console.log(`[ble-mesh.js] ERROR Deivce is unprovisioned but in node is provisioned `)
    }
    
    console.log(`[ble-mesh.js] Current Unprovisioned Nodes:`, JSON.stringify(unProvisionedBleNodes));
};

function getProvisionedDevicesRsp(data) {
    console.log(`[ble-mesh.js] Recevied provisioned devices:`, JSON.stringify(data));
    bleNodes[data.uuid] = {};
}

setTimeout(() => {
    pyaci.provisionScanStart(onDiscover);
    pyaci.getProvisionedDevices(getProvisionedDevicesRsp);
}, 1000);
