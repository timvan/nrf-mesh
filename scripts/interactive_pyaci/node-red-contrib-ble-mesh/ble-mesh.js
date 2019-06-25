const cp = require('child_process');

const pyscript = {
    filename: 'interactive_pyaci.py',
    working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/'
}

const pyaci = cp.spawn('python'
    , [pyscript.working_dir + pyscript.filename]
    , {
        cwd: pyscript.working_dir,
        stdio: ['pipe', 'pipe', 2]
    }
);

var n = 0;

handle_message = function(msg_in) {

    var msg = JSON.parse(msg_in);
    var op = msg.op;

    if(op == "ECHO RCVD"){
        var data = msg.data;
        console.log(`ECHO RCVD: ${data}`);
    }

    if(op == "SETUP RCVD"){
        send_message({op: "PROVISION"});
    }
}

send_message = function(msg_in) {
    var msg = JSON.stringify(msg_in)
    console.log(`Sending ${msg}`);
    pyaci.stdin.write(msg + '\n');
}


module.exports = function(RED) {

    function BleMeshNode(config) {
        RED.nodes.createNode(this, config);

        this.localName = config.localName;
        this.uuid = config.uuid;
        this.pin = config.pin;

        this.on('input', function(msg) {    
            
            var value = msg.value;

            var msg_out = {
                op: "SET",
                uuid: this.uuid,
                pin: this.pin,
                value: this.value
            };

            this.send(msg_out.toString);
        });
    }
    RED.nodes.registerType("ble-mesh",BleMeshNode);

    RED.events.on('runtime-event', (ev) => {
        // RED.log.info(`[BleMesh] <runtime-event> ${JSON.stringify(ev)}`);
        
        // send_message({op: "ECHO", data: "Hi"});
        send_message({op: "SETUP"});
    });
}