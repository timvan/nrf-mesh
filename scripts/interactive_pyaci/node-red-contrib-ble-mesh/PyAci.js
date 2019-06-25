const cp = require('child_process');

class PyAci {
    constructor() {

        this.pyscript = {
            filename: 'interactive_pyaci.py',
            working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/'
        }

        this.child = cp.spawn('python'
            , [this.pyscript.working_dir + this.pyscript.filename, "--log-level", "0"]
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

    provisionScanStart() {
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

    configure() {
        this.send({
            op: "Configure",
        });

    }

    /* RECEIVED */

    handle_message(msg_in) {

        var msg = JSON.parse(msg_in);
        var op = msg.op;

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
    }

    echoRsp(msg) {
        var data = msg.data;
        console.log(`EchoRsp: ${data}`);
    }

    setupRsp() {
        console.log(`SetupRsp`);
    }

    newUnProvisionedDevice(msg) {
        var data = msg.data.toString();
        console.log(`NewUnProvisionedDevice: ${data}`);
    }

    provisionComplete() {
        console.log(`ProvisionComplete`);
        pyaci.configure();
    }
}



pyaci = new PyAci();
process.on('exit', () => {pyaci.exit()});
process.on('SIGINT', () => {pyaci.exit()});
pyaci.echo("hi")
pyaci.setup();
setTimeout(() => {
    pyaci.provisionScanStart();
    setTimeout(() => {
        pyaci.provision();
    }, 3000);
}, 3000);
// pyaci.provision();
