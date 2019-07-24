var Pyaci = require('./Pyaci.js');
var assert = require('assert');
var events = require('events');

var eventBus = require('./eventBus.js');

NRF52_DEV_BOARD_GPIO_PINS = [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25]

class BluetoothMesh {
    constructor() {        
        this.devices = [];

        eventBus.on("NewUnProvisionedDevice", (data) => {
            if(this.devices.filter(
                value => {return data.uuid === value.uuid}).length == 0)
            {   
                this.addNewDevice(data)
            };
            
        });

        eventBus.on("NewProvisionedDevice", (data) => {
            if(this.devices.filter(
                value => {return data.uuid === value.uuid}).length == 0)
            {
                var device = new Device(data.uuid);
                if(Object.keys(data).includes("name")){
                    device.name = data.name;
                }
                device.provisioned = true;

                // assumes all NewProvisionedDevices are configured and setup
                // TODO - add check..
                device.configured = true;
                device.appKeysAdded = true;

                this.devices.push(device);
            };
            
        });
    }

    provisionScanStart() {
        var pyaci = new Pyaci().getInstance();        
        pyaci.provisionScanStart()
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

    getDevice(uuid){
        var device = this.devices.filter((value) =>{
            return value.uuid === uuid;
        })
        return device[0];
    }
}

class Device {

    constructor(uuid) {
        
        assert(uuid != undefined);
        assert(uuid != null);
        this.uuid = uuid;
        this.name = "";

        this.elements = [];
        
        for(var i in NRF52_DEV_BOARD_GPIO_PINS) {
            this.elements.push(new Element(NRF52_DEV_BOARD_GPIO_PINS[i], this.uuid))
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
        var pyaci = new Pyaci().getInstance();
        if(name != "" || name != undefined || name != null){
            this.name = name;
            pyaci.provision(this.uuid, name);
        } else {
            pyaci.provision(this.uuid);
        }
    }

    configure(){
        var pyaci = new Pyaci().getInstance();
        pyaci.configure(this.uuid);
    }

    addAppKeys(){
        var pyaci = new Pyaci().getInstance();
        pyaci.addAppKeys(this.uuid);
    }

    getElement(pin){
        if(!NRF52_DEV_BOARD_GPIO_PINS.includes(pin)){
            return null
        };
        return this.elements.filter(value => {
            return value.pin === pin;
        })[0];
    }

    setName(name){
        var pyaci = new Pyaci().getInstance();
        pyaci.setName(this.uuid, name);
        this.name = name;
    }
}

class Element {
    constructor(pin, uuid){
        this.pin = parseInt(pin);
        this.uuid = uuid;
        
        // default configuration for pin is output
        this.isInput = false;
    }

    configureGPIOasInput(asInput){
         // TODO - should this respond to callback
        var pyaci = new Pyaci().getInstance();       
        if(pyaci.configureGPIO(asInput, this.pin, this.uuid)){
            this.isInput = asInput;
            return true;
        } else {
            return false;
        }
    }

    setGPIO(value){
        var pyaci = new Pyaci().getInstance();
        if(this.isInput){
            return false;
        }
        return pyaci.setGPIO(value, this.pin, this.uuid);
    }

    getGPIO(){
        var pyaci = new Pyaci().getInstance();
        return pyaci.getGPIO(this.pin, this.uuid);
    }
}

module.exports = {
    Mesh: BluetoothMesh,
    Device: Device,
    Element: Element
};

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
        this.testGetElement();

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

    testGetElement() {
        assertEquals(this.device.getElement(12).pin, 12);
        assertEquals(this.device.getElement(16).pin, 16);
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