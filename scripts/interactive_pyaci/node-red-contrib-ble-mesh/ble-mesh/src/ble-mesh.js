var Pyaci = require('./Pyaci.js')
var BluetoothMesh = require('./Mesh.js')
var pyaci = new Pyaci().getInstance();
var eventBus = require('./eventBus.js');

var p = require('process')
p.on('SIGINT', () => {pyaci.disconnect()});
p.on('uncaughtException', () => {pyaci.disconnect()});

// pyaci.pyscript = {
//     filename: 'pyaci_test.py',
//     working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/node-red-contrib-ble-mesh/ble-mesh/tests/',
//     args: []
// }

pyaci.connect();

var mesh = new BluetoothMesh.Mesh()

setTimeout(() => {
    pyaci.getProvisionedDevices();
    // mesh.provisionScanStart();
}, 1000);

// eventBus.on("NewUnProvisionedDevice", (data) => {
    // // TURN ON TO AUTO PROVISION
    // var device = mesh.getDevice(data.uuid);
    // device.provision();
// })

// eventBus.on("ProvisionComplete", (data) => {
//     var device = mesh.getDevice(data.uuid);
//     device.configure();
// })
// eventBus.on("CompositionDataStatus", (data) => {
//     var device = mesh.getDevice(data.uuid);
//     device.addAppKeys();
    
//     // TODO - set scanning back on after completion..
//     mesh.provisionScanStart();
// })

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
        this.pin = parseInt(config.pin);
        var confignode = RED.nodes.getNode(config.confignode);
        
        this.element = confignode.device.getElement(this.pin);
        this.element.configureGPIOasInput(false);

        node.on('input', function(msg) {
            var value = msg.payload;
            this.status({fill:"green",shape:"dot",text:value});
            this.element.setGPIO(value);
        });

        var uuid = confignode.device.uuid;

        // Set Failed
        
        this.setAckFailedListener = (data) => {
            if(data.uuid === uuid && data.pin === this.pin){
                // node.send({
                //     payload: {
                //         "error": "Set Ack Failed"
                //     }
                // });

                this.status({fill:"red",shape:"dot",text:"Set Ack Failed"});
            }
        };
        eventBus.on("SetAckFailedEventGPIO_" + uuid, this.setAckFailedListener);


        this.statusListener = (data) => {
            if(data.uuid === uuid && data.pin === this.pin){
                this.status({fill:"green",shape:"dot",text:data.value});
            }
        }

        eventBus.on("StatusEventGPIO_" + uuid, this.statusListener);

        // Clean up when closed
        node.on('close', () => {
            eventBus.removeListener("SetAckFailedEventGPIO_" + uuid, this.setAckFailedListener);
            eventBus.removeListener("StatusEventGPIO_" + uuid, this.statusListener);
        })
    }
    RED.nodes.registerType("ble-mesh-output", BleMeshNodeOutput);

    /*************************************/
    /* INPUT NODE                        */
    /*************************************/

    function BleMeshNodeInput(config) {

        RED.nodes.createNode(this, config);
        
        var node = this;
        this.pin = parseInt(config.pin);
        var confignode = RED.nodes.getNode(config.confignode);

        this.element = confignode.device.getElement(this.pin);
        this.element.configureGPIOasInput(true);
        
        if(config.getInitialState){
            setTimeout(() =>{
                this.element.getGPIO()
            }, 1000);
        }
        
        node.on('input', function(msg) {
            var value = msg.payload;
            if(value == 1){
                this.element.getGPIO();
            }
        });

        var uuid = confignode.device.uuid;
        
        
        // Set event
        this.setListener = (data) => {
            if(data.uuid === uuid && data.pin === this.pin){
                node.send({
                    payload: parseInt(data.value)
                });
                this.status({fill:"green",shape:"dot",text:data.value});
            }
        };
        eventBus.on("SetEventGPIO_" + uuid, this.setListener);


        // Status event
        this.statusListener = (data) => {
            if(data.uuid === uuid && data.pin === this.pin){
                node.send({
                    payload: parseInt(data.value)
                });
                this.status({fill:"green",shape:"dot",text:data.value});
            }
        }

        eventBus.on("StatusEventGPIO_" + uuid, this.statusListener);

        // Clean up on close
        node.on('close', () => {
            eventBus.removeListener("SetEventGPIO_" + uuid, this.setListener);
            eventBus.removeListener("StatusEventGPIO_" + uuid, this.statusListener);
        })

    }

    RED.nodes.registerType("ble-mesh-input", BleMeshNodeInput);

    /*************************************/
    /* GENERIC NODE                      */
    /*************************************/

    function BleMeshNodeConfig(config) {
        RED.nodes.createNode(this, config);
        var node = this;
        this.device = mesh.getDevice(String(config.uuid));
    }

    RED.nodes.registerType("ble-mesh-config", BleMeshNodeConfig);


    /*************************************/
    /* NODE-RED                          */
    /*************************************/

    RED.events.on('runtime-event', (ev) => {
        RED.log.info(`[BleMesh] <runtime-event> ${JSON.stringify(ev)}`);
    });

    RED.httpAdmin.get('/__bleMeshUnProveDevList', (req, res) => {
        var body = mesh.getUnProvisionedDevices();
        RED.log.info(`/__bleMeshUnProveDevList ${JSON.stringify(body)}`);
        res.json(body);
    });

    RED.httpAdmin.get('/__bleMeshDevList', (req, res) => {
        var body = mesh.devices;
        RED.log.info(`/__bleMeshDevList ${JSON.stringify(body)}`);
        res.json(body);
    });

    RED.httpAdmin.get('/__bleMeshDev', (req, res) => {
        RED.log.info(`/__bleMeshDev ${JSON.stringify(req.query)}`);
        var uuid = req.query.uuid;
        var body = mesh.getDevice(uuid);
        
        res.json(body);
    });

    RED.httpAdmin.get('/__bleMeshProvision', (req, res) => {
        
        RED.log.info(`/__bleMeshProvision ${JSON.stringify(req.query)}`);
        
        var uuid = req.query.uuid;
        var name = req.query.name;
        
        if(uuid != "" && uuid != null){    
            var device = mesh.getDevice(uuid);
            if(!device.provisioned){
                device.provision(name);
            }
        }
        res.send();
    })

    RED.httpAdmin.get('/__bleMeshConfigure', (req, res) => {
        RED.log.info(`/__bleMeshConfigure ${JSON.stringify(req.query)}`);
        var uuid  = req.query.uuid;
        if(uuid != "" && uuid != null){
            var device = mesh.getDevice(uuid);
            if(!device.configured){
                device.configure();
            }
        };
        res.send();
    })

    RED.httpAdmin.get('/__bleMeshAddAppKeys', (req, res) => {
        RED.log.info(`/__bleMeshAddAppKeys ${JSON.stringify(req.query)}`);
        var uuid  = req.query.uuid;
        if(uuid != "" && uuid != null){
            var device = mesh.getDevice(uuid);
            if(!device.appKeysAdded){
                device.addAppKeys();
            }
        }
        res.send();
    })

    RED.httpAdmin.get('/__bleMeshUpdate', (req, res) => {
        RED.log.info(`/__bleMeshUpdate ${JSON.stringify(req.query)}`);
        var uuid  = req.query.uuid;
        var name = req.query.name;
        if(uuid != "" && uuid != null){
            var device = mesh.getDevice(uuid);
            device.setName(name);
        }
        res.send();
    })

    RED.httpAdmin.get('/__bleMeshProvisionScanStart', (req, res) => {
        RED.log.info(`/__bleMeshProvisionScanStart`);
        mesh.provisionScanStart()
        res.send();
    })

    RED.httpAdmin.get('/__bleMeshRemoveNode', (req, res) => {
        RED.log.info(`/__bleMeshRemoveNode`);
        var uuid  = req.query.uuid;
        if(uuid != "" && uuid != null){
            mesh.removeDevice(uuid);
        }
        res.send();
    })
}