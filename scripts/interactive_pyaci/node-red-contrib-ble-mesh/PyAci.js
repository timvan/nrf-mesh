const cp = require('child_process');
var assert = require('assert');
// var events = require('events');

var eventBus = require('./eventBus.js');

class Pyaci {

    constructor() {
        this.child;
        this.output_channel;

        this.pyscript = {
            filename: 'interactive_pyaci.py',
            working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/',
            args: ["--log-level", "3"]
        }

        // Register input responses and events
        this.input_listners = {
            "EchoRsp": this.echoRsp,
            "NewUnprovisionedDevice": this.newUnProvisionedDevice,
            "ProvisionComplete": this.provisionComplete,
            "CompositionDataStatus": this.compositionDataStatus,
            "AddAppKeysComplete": this.addAppKeysComplete,
            "SetEventGPIO": this.setEventGPIO,
            "GetProvisionedDevicesRsp": this.getProvisionedDevicesRsp
        }

        eventBus.addListener("EchoRsp", () => {});
        eventBus.addListener("NewUnProvisionedDevice", () => {});
        eventBus.addListener("ProvisionComplete", () => {});
        eventBus.addListener("CompositionDataStatus", () => {});
        eventBus.addListener("AddAppKeysComplete", () => {});
        eventBus.addListener("SetEventGPIO", () => {});
        eventBus.addListener("NewProvisionedDevice", () => {});

    }

    log(msg) {
        console.log(`[pyaci.js] ${msg}`);
    }

    connect() {
        try {
            this.child = cp.spawn('python3'
                , [this.pyscript.working_dir + this.pyscript.filename].concat(this.pyscript.args)
                , {
                    cwd: this.pyscript.working_dir,
                    stdio: ['pipe', 'pipe', 2]
                }
            );

            this.output_channel = this.child.stdin;

            this.child.stdout.on('data', (data) => {
                var msgs = data.toString().trim().split("\n");
                msgs.forEach((m) => {
                    this.handle_new_message(m);  
                })
            });

        } catch (error) {
            this.log(error)
            this.log("Unable to establish connection with Pyaci")
        }
    }

    disconnect() {
        var op = "Disconnect"
        this.send(op);
        this.child.kill();
    }

    // OUTPUT

    send(op, data=null) {
        if(op == "" || op == null){
            this.log("Error - cannot send empty message")
            return false;
        }

        var msg = {op: op};
        
        if(data != null){
            msg.data = data;
        }
        
        var msg_out = JSON.stringify(msg)

        this.log(`TX: ${msg_out}`);
        this.output_channel.write(msg_out + '\n');
        return true;
    }

    echo(msg) {
        var op = "Echo";
        return this.send(op, msg);
    }

    provisionScanStart() {
        var op = "ProvisionScanStart";
        return this.send(op);
    }

    getProvisionedDevices() {
        var op = "GetProvisionedDevices";
        return this.send(op);
    }

    provision(uuid, name=null) {
        var op = "Provision";
        if(uuid == "" || uuid == null){
            this.log(`Provision error uuid cannot be empty`)
            return false;
        };

        var data = {
            uuid: uuid
        };

        if(name) {
            data.name  = name
        }

        return this.send(op, data);
    }

    configure(uuid) {
        var op = "Configure";

        if(uuid == "" || uuid == null){
            this.log(`configure - error uuid cannot be empty `)
            return false;
        }

        var data = {
            uuid: uuid
        };

        return this.send(op, data);
    }

    addAppKeys(uuid) {
        var op = "AddAppKeys";

        if(uuid == "" || uuid == null){
            this.log(`addAppKeys - error uuid cannot be empty `);
            return false;
        }

        var data = {
            uuid: uuid
        };

        return this.send(op, data);
    }

    configureGPIO(asInput, pin, uuid) {
        var op = "ConfigureGPIO";

        if(typeof asInput != 'boolean'|| asInput == null){
            this.log("Input error configureGPIO - asInput");
            return false;
        }
        if(typeof pin != 'number' || pin < 0 || pin == null){
            this.log("Input error configureGPIO - pin");
            return false;
        }
        if(typeof uuid != 'string' || uuid == "" || uuid == null){
            this.log("Input error configureGPIO - uuid");
            return false; 
        }
        var data = {
            pin: pin,
            uuid: uuid,
            asInput: asInput
        };
        return this.send(op, data);
    }

    setGPIO(onoff, pin, uuid) {
        var op = "SetGPIO";

        if(typeof onoff != 'boolean' && typeof onoff != 'number'){
            this.log("Input error setGPIO - onoff");
            return false;
        }
        if(typeof onoff === 'number' && (onoff < 0 || onoff > 1)){
            this.log("Input error setGPIO - onoff");
            return false;
        }

        if(typeof pin != 'number' || pin < 0 || pin == null){
            this.log("Input error setGPIO - pin");
            return false;
        }
        if(typeof uuid != 'string' || uuid == "" || uuid == null){
            this.log("Input error setGPIO - uuid");
            return false; 
        }s

        var data = {
            value: onoff,
            pin: pin,
            uuid: uuid
        };
        return this.send(op, data);
    }

    setName(uuid, name) {
        var op = "SetName";

        if(typeof uuid != 'string' || uuid == "" || uuid == null){
            this.log("Input error setName - uuid");
            return false; 
        }

        var data = {
            name: name,
            uuid: uuid
        };
        return this.send(op, data);
    }

    // INPUT

    handle_new_message(msg_in) {
        
        try {
            var msg = JSON.parse(msg_in);
            var op = msg.op;
            var data = msg.data;
            this.log(`RX: ${msg_in}`);
        } catch(err) {
            this.log(`Parse Failed: ${msg_in}`)
            return;
        }

        try {
            this.input_listners[op](data)
        } catch(err){
            this.log(`Failed trying response to ${op}`);
            this.log(err);
            return;
        }
    }

    echoRsp(data) {
        eventBus.emit("EchoRsp", data);
    }

    newUnProvisionedDevice(data) {
        eventBus.emit("NewUnProvisionedDevice", data);
    }

    getProvisionedDevicesRsp(data) {
        eventBus.emit("NewProvisionedDevice", data)
    }

    provisionComplete(data) {
        eventBus.emit("ProvisionComplete", data);
    }

    compositionDataStatus(data) {
        eventBus.emit("CompositionDataStatus", data);
    }

    addAppKeysComplete(data) {
        var uuid = data.uuid;
        eventBus.addListener("SetEventGPIO_" + uuid, () => {});
        eventBus.emit("AddAppKeysComplete", data);
    }

    setEventGPIO(data) {
        var uuid = data.uuid;
        eventBus.emit("SetEventGPIO_" + uuid, data);
    }

}

class Singleton {

    constructor() {
        if (!Singleton.instance) {
            Singleton.instance = new Pyaci();
        }
    }

    getInstance() {
        return Singleton.instance;
    }
}

module.exports = Singleton;


/**************************************************************/
/* UNIT TESTING                                               */
/**************************************************************/

const TESTAWAIT = 1000;

function assertFalse(x){
    assert(!x);
}

function assertEquals(x, y){
    assert(x === y);
}

function assertNotEqual(x, y){
    assert(x != y);
}

class TestPyaci {

    constructor() {
        this.pyaci = new Singleton().getInstance()

        this.pyaci.pyscript = {
            filename: 'pyaci_test.py',
            working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/node-red-contrib-ble-mesh/',
            args: []
        }
    }

    run() {
        this.testComplete = false;

        this.testConnect();
        this.testSend();
        this.testEcho();
        this.testNewUnProvisionedDevice();
        this.testProvisionComplete();
        this.testConfigure();
        this.testAddAppKeys();
        this.testConfigureGPIO();
        this.testSetGPIO();
        this.testSetEventGPIO();
        
        // KEEP LAST
        // while(!this.testComple){};
        // this.testDisconnect();
    }

    testConnect() {
        this.pyaci.connect();
    }

    testDisconnect() {
        this.pyaci.disconnect();
    }

    testSend() {
        assertFalse(this.pyaci.send(""));
        assertFalse(this.pyaci.send(null));
        assert(this.pyaci.send("Test"));
        assert(this.pyaci.send("Test", {}));
    }

    testEcho() {
        var msg = "hello world";
        assert(this.pyaci.echo(msg));
        
        this.echoRspEventTriggered = false;
        eventBus.on("EchoRsp", (data) => {
            assertEquals(msg, data);
            this.echoRspEventTriggered = true;
        })

        setTimeout(() => {assert(this.echoRspEventTriggered)}, TESTAWAIT);
    }

    testNewUnProvisionedDevice() {
        // New device with uuid FOOO is sent from pyaci_test upon receival of provisionScanStart
        assert(this.pyaci.provisionScanStart());
        
        this.newUnProvisionedDeviceEventTriggered = false;
        eventBus.on("NewUnProvisionedDevice", (data) => {
            assertEquals(data.uuid, "FOOO");
            this.newUnProvisionedDeviceEventTriggered = true;
        });

        setTimeout(() => {assert(this.newUnProvisionedDeviceEventTriggered)}, TESTAWAIT);
    }

    testProvisionComplete() {
        assertFalse(this.pyaci.provision());
        assertFalse(this.pyaci.provision(""));
        assert(this.pyaci.provision("FOOO"));
        
        this.provisionCompleteEventTriggered = false;
        eventBus.on("ProvisionComplete", (data) => {
            assertEquals(data.uuid, "FOOO");
            this.provisionCompleteEventTriggered = true;
        });

        setTimeout(() => {assert(this.provisionCompleteEventTriggered)}, TESTAWAIT);
    }

    testConfigure() {
        assertFalse(this.pyaci.configure());
        assertFalse(this.pyaci.configure(""));
        assert(this.pyaci.configure("FOOO"));
        
        this.compositionDataStatusEventTriggered = false;
        eventBus.on("CompositionDataStatus", (data) => {
            assertEquals(data.uuid, "FOOO");
            this.compositionDataStatusEventTriggered = true;
        });

        setTimeout(() => {assert(this.compositionDataStatusEventTriggered)}, TESTAWAIT);
    }

    testAddAppKeys() {
        assertFalse(this.pyaci.addAppKeys());
        assertFalse(this.pyaci.addAppKeys(""));
        assert(this.pyaci.addAppKeys("FOOO"));

        this.addAppKeysCompleteEventTriggered = false;
        eventBus.on("AddAppKeysComplete", (data) => {
            assertEquals(data.uuid, "FOOO");
            this.addAppKeysCompleteEventTriggered = true;
        });

        setTimeout(() => {assert(this.addAppKeysCompleteEventTriggered)}, TESTAWAIT);
    }

    testConfigureGPIO() {
        assertFalse(this.pyaci.configureGPIO(1, 17, "FOOO"));
        assertFalse(this.pyaci.configureGPIO("", 17, "FOOO"));
        assertFalse(this.pyaci.configureGPIO(null, 17, "FOOO"));

        assertFalse(this.pyaci.configureGPIO(true, -1, "FOOO"));
        assertFalse(this.pyaci.configureGPIO(false, "", "FOOO"));
        assertFalse(this.pyaci.configureGPIO(true, null, "FOOO"));

        assertFalse(this.pyaci.configureGPIO(true, 17, 1));
        assertFalse(this.pyaci.configureGPIO(false, 17, null));
        assertFalse(this.pyaci.configureGPIO(false, 17, ""));
        assertFalse(this.pyaci.configureGPIO(false, 17));

        assert(this.pyaci.configureGPIO(true, 17, "FOOO"));

        // TODO - add a configure callback...

        // this.configureGPIOEventTriggered = false;
        // eventBus.on("ConfigureGPIO", (data) => {
        //     assertEquals(data.uuid, "FOOO");
        //     assertEquals(data.pin, 17);
        //     assertEquals(data.asInput, true);
        //     this.configureGPIOEventTriggered = true;
        // });
        
        // setTimeout(assert, TESTAWAIT, this.addAppKeysEventTriggered);
    }

    testSetGPIO() {
        assertFalse(this.pyaci.setGPIO(null, 17, "FOOO"));
        assertFalse(this.pyaci.setGPIO("", 17, "FOOO"));
        assertFalse(this.pyaci.setGPIO(-1, 17, "FOOO"));
        assertFalse(this.pyaci.setGPIO(2, 17, "FOOO"));

        assertFalse(this.pyaci.setGPIO(true, -1, "FOOO"));
        assertFalse(this.pyaci.setGPIO(false, "", "FOOO"));
        assertFalse(this.pyaci.setGPIO(true, null, "FOOO"));

        assertFalse(this.pyaci.setGPIO(true, 17, 1));
        assertFalse(this.pyaci.setGPIO(false, 17, null));
        assertFalse(this.pyaci.setGPIO(false, 17, ""));
        assertFalse(this.pyaci.setGPIO(false, 17));

        assert(this.pyaci.setGPIO(true, 17, "FOOO"));
        assert(this.pyaci.setGPIO(0, 17, "FOOO"));

        // TODO - add a set callback...
    }

    testSetEventGPIO() {
        this.setEventGPIOEventTriggered = false;
        eventBus.on("SetEventGPIO_" + "FOOO", (data) => {
            assertEquals(data.uuid, "FOOO");
            assertEquals(data.pin, 17);
            assertEquals(data.value, 1);
            this.setEventGPIOEventTriggered = true;
        });

        this.pyaci.send("TestSetEventGPIO");

        setTimeout(() => {assert(this.setEventGPIOEventTriggered)}, TESTAWAIT);
    }
}

if (require.main === module) {
    p = new TestPyaci();
    p.run();
}