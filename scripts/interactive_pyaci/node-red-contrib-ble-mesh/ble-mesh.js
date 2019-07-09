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

function provision() {
    var uuid = unProvisionedBleNodes.pop().uuid;
    pyaci.provision(onProvisionComplete, uuid);
};

function provision_by_uuid(uuid) {
    pyaci.provision(onProvisionComplete, uuid);
}

function onDiscover(data) {
    unProvisionedBleNodes.push(data);
    console.log(`Nodes ${unProvisionedBleNodes}`, JSON.stringify(unProvisionedBleNodes));
    // provision();
};

function getProvisionedDevicesRsp(data) {
    console.log("Recevied devices:", JSON.stringify(data));
    bleNodes[data.uuid] = {};
}

setTimeout(() => {
    pyaci.provisionScanStart(onDiscover);
    pyaci.getProvisionedDevices(getProvisionedDevicesRsp);
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
        this.uuid = String(config.uuid);
        this.pin = config.pin;
        
        if(this.uuid !== "" && Object.keys(bleNodes).includes(this.uuid)){
            
            if(this.pin != ""){
                pyaci.configureGPIO(false, this.pin, this.uuid);
            }
        }

        node.on('input', function(msg) {
            console.log(msg);
            var value = msg.payload.value;
            
            if(this.uuid !== "" && Object.keys(bleNodes).includes(this.uuid)){
                pyaci.setGPIO(value, this.pin, this.uuid);
            }
        });
    }
    RED.nodes.registerType("ble-mesh-output", BleMeshNodeOutput);

    /*************************************/
    /* INPUT NODE                        */
    /*************************************/

    function BleMeshNodeInput(config) {

        RED.nodes.createNode(this, config);
        
        var node = this;    
        this.uuid = String(config.uuid);
        this.pin = config.pin;
        if(this.uuid !== "" && Object.keys(bleNodes).includes(this.uuid)){
            
            if(this.pin != ""){
                pyaci.configureGPIO(true, this.pin, this.uuid);
                bleNodes[this.uuid][this.pin] = function(value, address) {
                    node.send({
                        payload: {
                            address: address,
                            value: parseInt(value)
                        }
                    });
                };
                console.log(bleNodes);
            };
        };

        node.on('input', function(msg) {
            console.log(msg);
        });

    }

    RED.nodes.registerType("ble-mesh-input", BleMeshNodeInput);

    /*************************************/
    /* GENERIC NODE                      */
    /*************************************/

    function BleMeshNodeConfig(config) {

        RED.nodes.createNode(this, config);
        this.uuid = config;
        this.registered_pins = [];

    }

    RED.nodes.registerType("ble-mesh-config", BleMeshNodeConfig);


    /*************************************/
    /* NODE-RED                          */
    /*************************************/

    RED.events.on('runtime-event', (ev) => {
        RED.log.info(`[BleMesh] <runtime-event> ${JSON.stringify(ev)}`);
    });

    RED.httpAdmin.get('/__bleMeshUnProveDevList', (req, res) => {
        var body = unProvisionedBleNodes;
        RED.log.info('/__bleMeshUnProveDevList', JSON.stringify(body));
        res.json(body);
    });

    RED.httpAdmin.get('/__bleMeshDevList', (req, res) => {
        var body = bleNodes;
        RED.log.info('/__bleMeshDevList', JSON.stringify(body));
        res.json(body);
    });

    RED.httpAdmin.get('/__bleMeshProvision', (req, res) => {
        var uuid  = req.body.uuid;
        console.log(req.body);
        // provision_by_uuid(uuid);
        res.send();
    })
}