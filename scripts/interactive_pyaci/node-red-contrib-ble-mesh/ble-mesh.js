const cp = require('child_process');
const pyaci = cp.spawn('python'
    , ['/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/node-red-contrib-ble-mesh/stdio-test.py']
    , {stdio: ['pipe', 'pipe', 2]}
);

pyaci.stdout.on('data', (data) => {
    console.log(`[BleMesh] stdout ${data}`);
});

module.exports = function(RED) {

    function BleMeshNode(config) {
        RED.nodes.createNode(this,config);
        var node = this;
        node.on('input', function(msg) {
            node.send("hellooo");
        });
    }
    RED.nodes.registerType("ble-mesh",BleMeshNode);

    RED.events.on('runtime-event', (ev) => {
        RED.log.info(`[BleMesh] <runtime-event> ${JSON.stringify(ev)}`);
        // pyaci.stdin.write("echo\n");
    });
}