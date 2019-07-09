const cp = require('child_process');

class PyAci {
    constructor() {

        this.pyscript = {
            filename: 'interactive_pyaci.py',
            working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/'
        }

        this.child = cp.spawn('python'
            , [this.pyscript.working_dir + this.pyscript.filename, "--log-level", "3"]
            , {
                cwd: this.pyscript.working_dir,
                stdio: ['pipe', 'pipe', 2]
            }
        );

        this.messages_received = 0;
        this.messages_sent = 0;

        this.child.stdout.on('data', (data) => {
            var msgs = data.toString().trim().split("\n");
            msgs.forEach((m) => {
                this.handle_message(m);  
            })
        });

        /* callbacks */
        this.onDiscover;
        this.onCompositionDataStatus;
    };

    /* COMMANDS */

    send(cmd) {
        cmd["nodeMessageId"] = this.messages_sent
        this.messages_sent += 1
        var msg = JSON.stringify(cmd)
        console.log(`Sending ${msg}`);
        this.child.stdin.write(msg + '\n');
    };

    kill() {
        this.child.kill();
    }

    exit() {
        this.send({op: "Exit"})
    }

    echo(msg) {
        this.send({
            op: "Echo",
            data: msg
        });
    };

    /* Sets database and creates a Provisioner  */
    setup() {
        this.send({
            op: "Setup"
        });
    };

    provisionScanStart(onDiscoverCb) {
        this.onDiscover = onDiscoverCb;
        
        this.send({
            op: "ProvisionScanStart"
        });
    }

    // provisionScanStop() {
    //     this.send({
    //         op: "ProvisionScanStop"
    //     });
    // }

    provision(onProvisionCompleteCb, uuid) {
        this.onProvisionComplete = onProvisionCompleteCb;
        this.send({
            op: "Provision",
            data: {
                uuid: uuid
            }
        });
    }

    configure(onCompositionDataStatusCb) {
        this.onCompositionDataStatus = onCompositionDataStatusCb;
        this.send({
            op: "Configure",
        });
    }

    addAppKeys() {
        this.send({
            op: "AddAppKeys",
        });
    }

    // addGroupSubscriptionAddresses() {
    //     this.send({
    //         op: "AddGroupSubscriptionAddresses",
    //     });
    // }

    // addGroupPublicationAddresses() {
    //     this.send({
    //         op: "AddGroupPublicationAddresses",
    //     });
    // }

    // addGenericClientModel() {
    //     this.send({
    //         op: "AddGenericClientModel",
    //     });
    // }

    // addGenericServerModel(onGenericOnOffServerSetUnackCb) {
    //     this.onGenericOnOffServerSetUnack = onGenericOnOffServerSetUnackCb;
    //     this.send({
    //         op: "AddGenericServerModel",
    //     });
    // }

    // genericClientSet(onoff) {
    //     this.send({
    //         op: "GenericClientSet",
    //         data : {
    //             value: onoff
    //         }
    //     });
    // }

    configureGPIO(asInput, pin, uuid) {
        if(pin == "" || pin == null){
            console.log("Input error configureGPIO - pin");
            return;
        }
        if(uuid == "" || uuid == null){
            console.log("Input error configureGPIO - uuid");
            return; 
        }
        
        this.send({
            op: "ConfigureGPIO",
            data: {
                value: asInput,
                pin: pin,
                uuid: uuid               
            }
        });
    }

    setGPIO(onoff, pin, uuid) {
        
        if(pin == "" || pin == null){
            console.log("Input error setGPIO - pin");
            return;
        }
        if(uuid == "" || uuid == null){
            console.log("Input error setGPIO - uuid");
            return; 
        }
        
        this.send({
            op: "SetGPIO",
            data: {
                value: onoff,
                pin: pin,
                uuid: uuid
            }
        });
    }

    getProvisionedDevices(getProvisionedDevicesCb){
        this.onGetProvisionedDevices = getProvisionedDevicesCb;
        this.send({
            op: "GetProvisionedDevices"
        });
    }
    
    /* RECEIVED */

    handle_message(msg_in) {

        if("PYA" == msg_in.split(0,3)){
            // console.log(msg_in);
            return;
        }

        try {
            var msg = JSON.parse(msg_in);
            var op = msg.op;
            console.log(`[BleMesh] RX${this.messages_received} ${msg_in}`);
            this.messages_received += 1;
        } catch(err) {
            console.log("Failed passing message: ", msg_in)
            return;
        }

        if(op == "EchoRsp"){
            this.echoRsp(msg)
        }

        if(op == "SetupRsp"){
            this.setupRsp();
        }

        if(op == "NewUnProvisionedDevice"){
            this.newUnProvisionedDevice(msg)
        }

        if(op == "ProvisionComplete"){
            this.provisionComplete();
        }

        if(op == "CompositionDataStatus"){
            this.compositionDataStatus(msg);
        }

        if(op == "AddAppKeysComplete"){
            this.addAppKeysComplete();
        }

        // if(op == "GenericOnOffServerSetUnack"){
        //     this.genericOnOffServerSetUnack(msg);
        // }

        if(op == "SetEventGPIO"){
            this.setEventGPIO(msg);
        }

        if(op == "GetProvisionedDevicesRsp"){
            this.getProvisionedDevicesRsp(msg);
        }
    }

    echoRsp(msg) {
        var data = msg.data;
        console.log(`EchoRsp: ${data}`);
    }

    setupRsp() {
        console.log(`SetupRsp`);
    }

    newUnProvisionedDevice(msg) {
        var data = msg.data;
        console.log(`NewUnProvisionedDevice: ${data}`, data.toString());
        this.onDiscover(data);
    }

    provisionComplete() {
        console.log(`ProvisionComplete`);
        this.onProvisionComplete();
    }

    compositionDataStatus(msg) {
        var data = msg.data
        console.log(`CompositionDataStatus: ${data}`);
        this.onCompositionDataStatus(data);
    }

    addAppKeysComplete() {
        console.log(`AddAppKeysComplete`);
    }

    // genericOnOffServerSetUnack(msg) {
    //     var data = msg.data;
    //     console.log(`GenericOnOffServerSetUnack: ${data}`);
    //     this.onGenericOnOffServerSetUnack(data)
    // }

    setEventGPIO(msg) {
        var data = msg.data;
        console.log(`SetEventGPIO: ${data}`);
        this.onSetEventGPIO(data)
    }

    onSetEventGPIO(data) {
        var uuid = data.uuid;
        var pin = data.pin;

        try {
            var fcn = this.setEventsCbs[uuid][pin];
            fcn(data.value, `${uuid}_${pin}`);
        } catch (error) {
            console.log(this.setEventsCbs);
            console.log("Error onSetEventGPIO ", error);
        }
    }

    getProvisionedDevicesRsp(msg){
        try{
            this.onGetProvisionedDevices(msg.data);
        } catch (error) {
            console.log("Error onGetProvisionedDevices cb", error)
        }
    }
}

class Singleton {

    constructor() {
        if (!Singleton.instance) {
            Singleton.instance = new PyAci();
        }
    }
  
    getInstance() {
        return Singleton.instance;
    }
  
  }
  

module.exports = Singleton;
