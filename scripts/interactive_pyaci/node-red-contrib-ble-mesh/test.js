var PyAci = require('./PyAci')
var pyaci = new PyAci().getInstance();

process.on('SIGINT', () => {pyaci.exit()});

pyaci.setup();

const bleNodes = [];
const unprovisionedBleNodes = [];

function onDiscover(data) {
    unprovisionedBleNodes.push(data);
    console.log(`Nodes ${unprovisionedBleNodes}`, unprovisionedBleNodes)
}

setTimeout(() => {
    pyaci.provisionScanStart(onDiscover);
}, 10000);