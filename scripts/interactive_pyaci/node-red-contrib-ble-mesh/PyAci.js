const cp = require('child_process');

class PyAci {
    constructor() {

        this.pyscript = {
            filename: 'interactive_pyaci.py',
            working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/'
        }

        this.child = cp.spawn('python'
            , [this.pyscript.working_dir + this.pyscript.filename, "--log-level", "4"]
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
                console.log(`[BleMesh] RX${this.messages_received} ${m}`);
                this.messages_received += 1;
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

    provisionScanStop() {
        this.send({
            op: "ProvisionScanStop"
        });
    }

    provision() {
        this.send({
            op: "Provision",
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

    addGroupAddress() {
        this.send({
            op: "AddGroupAddress",
        });
    }

    addGenericModels() {
        this.send({
            op: "AddGenericModels",
        });
    }

    genericClientSet(onoff) {
        this.send({
            op: "GenericClientSet",
            data : {
                value: onoff
            }
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
            this.compositionDataStatus(msg.data);
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
    }

    compositionDataStatus(data) {
        console.log(`CompositionDataStatus: ${data}`, data.toString());
        this.onCompositionDataStatus(data);
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
