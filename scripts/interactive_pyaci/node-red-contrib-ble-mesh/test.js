var PyAci = require('./PyAci')
var pyaci = new PyAci().getInstance();

var p = require('process')
p.on('SIGINT', () => {pyaci.kill()});


var bleNodes = {};
var unProvisionedBleNodes = [];


function onCompositionDataStatus(data) {
    console.log(`Node configuration `, JSON.stringify(data));
    bleNodes[data.uuid] = {};
    pyaci.addAppKeys();
};

function onProvisionComplete() {
    pyaci.configure(onCompositionDataStatus);
    var nodeId = 0;
};

function onDiscover(data) {
    unProvisionedBleNodes.push(data);
    console.log(`Nodes ${unProvisionedBleNodes}`, JSON.stringify(unProvisionedBleNodes));

    var uuid = unProvisionedBleNodes.pop().uuid;
    pyaci.provision(onProvisionComplete, uuid);
};

setTimeout(() => {
    pyaci.provisionScanStart(onDiscover);
}, 10000);
