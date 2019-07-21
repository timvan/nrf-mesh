var Pyaci = require('./Pyaci_n.js');
var assert = require('assert');
var events = require('events');

var eventBus = require('./eventBus.js');

NRF52_DEV_BOARD_GPIO_PINS = [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25]

class BluetoothMesh {
    constructor() {
        this.pyaci = new Pyaci().getInstance();        
        this.devices = [];

        eventBus.on("NewUnProvisionedDevice", (data) => {
            this.addNewDevice(data)
        });
    }

    addNewDevice(data) {
        var device = new Device(data.uuid);
        this.devices.push(device);
    }

    getProvisionedDevices() {
        return this.devices.filter(value => {
            return value.provisioned;
        })
    };

    getUnProvisionedDevices() {
        return this.devices.filter(value => {
            return !value.provisioned;
        })
    }
}

class Device {

    constructor(uuid) {
        this.pyaci = new Pyaci().getInstance();
        
        assert(uuid != undefined);
        assert(uuid != null);
        this.uuid = uuid;
        this.localname = "";

        this.elements = [];
        
        for(var pin in NRF52_DEV_BOARD_GPIO_PINS) {
            this.elements.push(new Element(pin, this.uuid))
        };

        this.provisioned = false;
        this.configured = false;
        this.appKeysAdded = false;

        // TODO - need name from provision scan data  
        // this.name = name

        // TODO - need some method health checking if this is connected
        // this.connected;

        eventBus.on("ProvisionComplete", (data) => {
            if(data.uuid === this.uuid){
                this.provisioned = true;
            }
        });

        eventBus.on("CompositionDataStatus", (data) => {
            if(data.uuid === this.uuid){
                this.configured = true;
            }
        });

        eventBus.on("AddAppKeysComplete", (data) => {
            if(data.uuid === this.uuid){
                this.appKeysAdded = true;
            }
        });
    }

    provision(name="") {
        if(name != ""){
            this.localname = name;
            this.pyaci.provision(uuid, name);
        } else {
            this.pyaci.provision(uuid);
        }
    }

    configure(){
        this.pyaci.configure(this.uuid);
    }

    addAppKeys(){
        this.pyaci.addAppKeys(this.uuid);
    }

    getElement(pin){
        if(!NRF52_DEV_BOARD_GPIO_PINS.includes(pin)){
            return null
        }
        var element_index = NRF52_DEV_BOARD_GPIO_PINS.indexOf(pin);
        return this.devices[element_index];
    }
}

class Element {
    constructor(pin, uuid){
        this.pyaci = new Pyaci().getInstance();

        this.pin = pin;
        this.uuid = uuid;
        
        // default configuration for pin is output
        this.isInput = false;
    }

    configureGPIOasInput(asInput){
         // TODO - should this respond to callback
        if(this.pyaci.configureGPIO(asInput, this.pin, this.uuid)){
            this.isInput = asInput;
            return true;
        } else {
            return false;
        }
    }

    setGPIO(value){
        if(this.isInput){
            return false;
        }
        return this.pyaci.setGPIO(value, this.pin, this.uuid);
    }
}

/**************************************************************/
/* UNIT TESTING                                               */
/**************************************************************/

const TESTAWAIT = 500;

function assertTrue(x){
    assert(x);
}

function assertFalse(x){
    assert(!x);
}

function assertEquals(x, y){
    assert(x === y);
}

function assertNotEqual(x, y){
    assert(x != y);
}

class TestDevice {
    constructor() {
        this.pyaci = new Pyaci().getInstance();
    }

    run() {
        this.device = new Device("TESTDEV");
        this.testInit();
        this.testProvision();

    }

    testInit() {
        assertEquals(this.device.elements.length, NRF52_DEV_BOARD_GPIO_PINS.length);
    }

    testProvision() {
        eventBus.emit("ProvisionComplete", {uuid: "NOTTESTDEV"})
        assertFalse(this.device.provisioned);
        eventBus.emit("ProvisionComplete", {uuid: "TESTDEV"})
        assertTrue(this.device.provisioned);
    }

    testConfigure() {
        // TODO
    }

    testAddAppKeys() {
        // TODO
    }
}

class TestElement {
    constructor() {
        this.pyaci = new Pyaci().getInstance();
        this.pin = 17;
        this.element = new Element(this.pin, "RAH");
    }

    run() {
        this.testConfigureGPIO();
        this.testSetGPIO();
    }

    testConfigureGPIO() {
        assert(this.element.configureGPIOasInput(true));
        assert(this.element.isInput);
    }

    testSetGPIO() {
        assert(this.element.configureGPIOasInput(true));
        assert(!this.element.setGPIO(false));
        assert(this.element.configureGPIOasInput(false));
        assert(this.element.setGPIO(true));
    }

}

if (require.main === module) {
    
    pyaci = new Pyaci().getInstance()

    pyaci.pyscript = {
        filename: 'pyaci_test.py',
        working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/node-red-contrib-ble-mesh/',
        args: []
    }

    pyaci.connect();


    d = new TestDevice();
    d.run();

    e = new TestElement();
    e.run();
}