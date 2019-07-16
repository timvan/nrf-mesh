var PyAci = require('./PyAci')
var pyaci = new PyAci().getInstance();

var p = require('process')
p.on('SIGINT', () => {pyaci.kill()});
p.on('uncaughtException', () => {pyaci.kill()});

var bleNodes = {};
var unProvisionedBleNodes = [];

pyaci.setEventsCbs = bleNodes;

function onAddAppKeysComplete(uuid) {
    unProvisionedBleNodes = unProvisionedBleNodes.filter(o => {
        o.uuid != uuid;
    })
}

function onCompositionDataStatus(data) {
    console.log(`[ble-mesh.js] Recevied Node composition `, JSON.stringify(data));
    uuid = data.uuid;
    bleNodes[uuid] = {};
};

function onProvisionComplete(uuid) {
    // setTimeout(() => {
    //     pyaci.configure(uuid, onCompositionDataStatus);
    // }, 2000);
};

function provision() {
    var uuid = unProvisionedBleNodes.pop().uuid;
    pyaci.provision(uuid, onProvisionComplete);
};

function provision_by_uuid(uuid) {
    pyaci.provision(uuid, onProvisionComplete);
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
    console.log(`[ble-mesh.js] Recevied provisioned devices:`, JSON.stringify(data.uuid));
    bleNodes[data.uuid] = {};
}

setTimeout(() => {
    pyaci.provisionScanStart(onDiscover);
    pyaci.getProvisionedDevices(getProvisionedDevicesRsp);
}, 1000);

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
        this.confignode = RED.nodes.getNode(config.confignode);
        this.uuid = String(this.confignode.uuid);
        this.pin = config.pin;
        
        if(this.uuid !== "" && Object.keys(bleNodes).includes(this.uuid)){
            
            if(this.pin != ""){
                pyaci.configureGPIO(false, this.pin, this.uuid);
            }
        }

        node.on('input', function(msg) {
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
        this.confignode = RED.nodes.getNode(config.confignode);
        this.uuid = String(this.confignode.uuid);
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
            };
        };

    }

    RED.nodes.registerType("ble-mesh-input", BleMeshNodeInput);

    /*************************************/
    /* GENERIC NODE                      */
    /*************************************/

    function BleMeshNodeConfig(config) {

        RED.nodes.createNode(this, config);
        var node = this;
        this.uuid = String(config.uuid);
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
        RED.log.info(`/__bleMeshUnProveDevList ${JSON.stringify(body)}`);
        res.json(body);
    });

    RED.httpAdmin.get('/__bleMeshDevList', (req, res) => {
        var body = bleNodes;
        RED.log.info(`/__bleMeshDevList ${JSON.stringify(body)}`);
        res.json(body);
    });

    RED.httpAdmin.get('/__bleMeshAvailableDevices', (req, res) => {

    })

    RED.httpAdmin.get('/__bleMeshProvision', (req, res) => {
        
        RED.log.info(`/__bleMeshProvision ${JSON.stringify(req.query)}`);
        
        var uuid  = req.query.uuid;
        
        if(uuid != "" && uuid != null){    
            provision_by_uuid(uuid);
        }

        res.send();
    })

    RED.httpAdmin.get('/__bleMeshConfigure', (req, res) => {
        
        RED.log.info(`/__bleMeshConfigure ${JSON.stringify(req.query)}`);
        
        var uuid  = req.query.uuid;
        
        if(uuid != "" && uuid != null){    
            pyaci.configure(uuid, onCompositionDataStatus);
        }

        res.send();
    })


    RED.httpAdmin.get('/__bleMeshAddAppKeys', (req, res) => {
        
        RED.log.info(`/__bleMeshAddAppKeys ${JSON.stringify(req.query)}`);
        
        var uuid  = req.query.uuid;
        
        if(uuid != "" && uuid != null){    
            pyaci.addAppKeys(uuid, onAddAppKeysComplete);
        }

        res.send();
    })
}