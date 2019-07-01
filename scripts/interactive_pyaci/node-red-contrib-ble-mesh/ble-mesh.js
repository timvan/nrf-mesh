var PyAci = require('./PyAci')
var pyaci = new PyAci().getInstance();

var p = require('process')
p.on('SIGINT', () => {pyaci.kill()});

pyaci.setup();

const bleNodes = [];
const unProvisionedBleNodes = [];

function onCompositionDataStatus(data) {
    console.log(`Node configuration `, JSON.stringify(data));
    pyaci.addAppKeys();
    // setTimeout(() => {
    //     pyaci.addGroupPublicationAddresses();
    // }, 10000);
}


function onDiscover(data) {
    unProvisionedBleNodes.push(data);
    console.log(`Nodes ${unProvisionedBleNodes}`, JSON.stringify(unProvisionedBleNodes));
    pyaci.provision();
    
    setTimeout(() => {
        pyaci.configure(onCompositionDataStatus);
    }, 20000);
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
        // this.localName = config.localName;
        // this.uuid = config.uuid;
        // this.pin = config.pin;

        pyaci.addGenericClientModel();

        node.on('input', function(msg) {    
            
            console.log(msg);
            var value = msg.payload.value;

            // var msg_out = {
            //     op: "SET",
            //     uuid: this.uuid,
            //     pin: this.pin,
            //     value: this.value
            // };

            pyaci.genericClientSet(value)
        });
    }
    RED.nodes.registerType("ble-mesh-output", BleMeshNodeOutput);

    /*************************************/
    /* INPUT NODE                        */
    /*************************************/

    function BleMeshNodeInput(config) {

        RED.nodes.createNode(this, config);

        var node = this;
        // this.localName = config.localName;
        // this.uuid = config.uuid;
        // this.pin = config.pin;

        this.onGenericOnOffServerSetUnack = function(data) {
            node.send({
                payload: data
            });
        };

        pyaci.addGenericServerModel(this.onGenericOnOffServerSetUnack);

        node.on('input', function(msg) {    
            
            console.log(msg);
            // var value = msg.payload.value;

            // pyaci.genericClientSet(value)
        });

        pyaci.set
    }

    RED.nodes.registerType("ble-mesh-input", BleMeshNodeInput);

    /*************************************/
    /* GENERIC NODE                      */
    /*************************************/

    function BleMeshNode(config) {

        RED.nodes.createNode(this, config);
    }

    RED.nodes.registerType("ble-mesh", BleMeshNode);


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