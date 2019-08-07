const Pyaci = require('../src/Pyaci.js')
const cp = require('child_process');
var assert = require('assert');
// var events = require('events');

var eventBus = require('../src/eventBus.js');


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
        this.pyaci = new Pyaci().getInstance()

        this.pyaci.pyscript = {
            filename: 'pyaci_test.py',
            working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/node-red-contrib-ble-mesh/ble-mesh/tests/',
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
        this.testStatusEventGPIO();
        this.testSetAckFailedEventGPIO();
        this.testGetGPIO();
        this.testSetName();
        this.testRemoveNode();
        
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
        var test_devs = ["FOOO", "RAAHH"]
        this.newUnProvisionedDeviceEventTriggered = false;
        eventBus.on("NewUnProvisionedDevice", (data) => {
            assertNotEqual(-1, test_devs.indexOf(data.uuid));
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

    testStatusEventGPIO() {
        this.statusEventGPIOEventTriggered = false;
        eventBus.on("StatusEventGPIO_" + "FOOO", (data) => {
            assertEquals(data.uuid, "FOOO");
            assertEquals(data.pin, 17);
            assertEquals(data.value, 1);
            this.statusEventGPIOEventTriggered = true;
        });

        this.pyaci.send("TestStatusEventGPIO");

        setTimeout(() => {assert(this.statusEventGPIOEventTriggered)}, TESTAWAIT);
    }
    
    testSetAckFailedEventGPIO() {
        this.setAckFailedEventGPIOTriggered = false;
        eventBus.on("SetAckFailedEventGPIO_" + "FOOO", (data) => {
            assertEquals(data.uuid, "FOOO");
            assertEquals(data.pin, 17);
            assertEquals(data.value, 1);
            this.setAckFailedEventGPIOTriggered = true;
        });

        this.pyaci.send("TestSetAckFailedEventGPIO");

        setTimeout(() => {assert(this.setAckFailedEventGPIOTriggered)}, TESTAWAIT);
    }

    testGetGPIO() {
        assertFalse(this.pyaci.getGPIO(-1, "FOOO"));
        assertFalse(this.pyaci.getGPIO("", "FOOO"));
        assertFalse(this.pyaci.getGPIO(null, "FOOO"));

        assertFalse(this.pyaci.getGPIO(17, 1));
        assertFalse(this.pyaci.getGPIO(17, null));
        assertFalse(this.pyaci.getGPIO(17, ""));
        assertFalse(this.pyaci.getGPIO(17));

        assert(this.pyaci.getGPIO(17, "FOOO"));

        // TODO - add a set callback...
    }

    testSetName() {

        assertFalse(this.pyaci.setName("FOOO", 1));
        assertFalse(this.pyaci.setName("FOOO", null));
        assertFalse(this.pyaci.setName("FOOO", ""));
        assertFalse(this.pyaci.setName("FOOO"));

        assertFalse(this.pyaci.setName(1, "name"));
        assertFalse(this.pyaci.setName(null, "name"));
        assertFalse(this.pyaci.setName("", "name"));

        assert(this.pyaci.setName("FOOO", "name"));
    }

    testRemoveNode(){
        assertFalse(this.pyaci.removeNode(1));
        assertFalse(this.pyaci.removeNode(null));
        assertFalse(this.pyaci.removeNode(""));
        assertFalse(this.pyaci.removeNode());
        assert(this.pyaci.removeNode("FOOO"));
    }

}

if (require.main === module) {
    p = new TestPyaci();
    p.run();
}