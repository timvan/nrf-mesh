var PyAci = require('./PyAci')
var pyaci = new PyAci().getInstance();

var p = require('process')
p.on('SIGINT', () => {pyaci.kill()});


var bleNodes = {};
var unProvisionedBleNodes = [];

pyaci.setEventsCbs = bleNodes;

function onCompositionDataStatus(data) {
    console.log(`Node configuration `, JSON.stringify(data));
    bleNodes[data.uuid] = {};
    console.log(bleNodes);
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

/*************************************/
/*                                   */
/*************************************/

module.exports = function(RED) {

    /*************************************/
    /* OUTPUT NODE                       */
    /*************************************/

    function BleMeshNodeOutput(config) {

        RED.nodes.createNode(this, config);

        var node = this;
        this.uuid = "9db77a0526b8734988639509c242d107";
        this.pin = 12;
        
        pyaci.configureGPIO(false, this.pin, this.uuid);

        node.on('input', function(msg) {
            console.log(msg);
            var value = msg.payload;
            pyaci.setGPIO(value, this.pin, this.uuid);
        });
    }
    RED.nodes.registerType("ble-mesh-output", BleMeshNodeOutput);

    /*************************************/
    /* INPUT NODE                        */
    /*************************************/

    function BleMeshNodeInput(config) {

        RED.nodes.createNode(this, config);

        var node = this;
        this.uuid = "9db77a0526b8734988639509c242d107";
        this.pin = 13;

        pyaci.configureGPIO(true, this.pin, this.uuid);

        bleNodes[this.uuid][this.pin] = function(value) {
            node.send({
                payload: value
            });
        };
        console.log(bleNodes);

        node.on('input', function(msg) {
            console.log(msg);
        });

    }

    RED.nodes.registerType("ble-mesh-input", BleMeshNodeInput);

    /*************************************/
    /* GENERIC NODE                      */
    /*************************************/

    // function BleMeshNode(config) {

    //     RED.nodes.createNode(this, config);
    // }

    // RED.nodes.registerType("ble-mesh", BleMeshNode);


    /*************************************/
    /* NODE-RED                          */
    /*************************************/

    RED.events.on('runtime-event', (ev) => {
        RED.log.info(`[BleMesh] <runtime-event> ${JSON.stringify(ev)}`);
    });

    RED.httpAdmin.get('/__bleMeshUnProveDevList', (req, res) => {
        body = unProvisionedBleNodes;
        RED.log.info('/__bleMeshUnProveDevList', JSON.stringify(body));
        res.json(body);
    });
}