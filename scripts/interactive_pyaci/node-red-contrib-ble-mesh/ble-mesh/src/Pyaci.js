const cp = require('child_process');
var assert = require('assert');
// var events = require('events');
var eventBus = require('./eventBus.js');
const fs = require('fs');
class Pyaci {
	constructor() {
		this.child;
		this.output_channel;
		this.stream = fs.createWriteStream('/Users/Tim-Mac/.node-red/node-red-log.txt', { flags: 'a' });
		this.pyscript = {
			filename: 'main.py',
			working_dir: '/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/',
			args: ['--log-level', '0']
		};
		// Register input responses and events
		this.input_listeners = {
			'EchoRsp': this.echoRsp,
			'NewUnprovisionedDevice': this.newUnProvisionedDevice,
			'ProvisionComplete': this.provisionComplete,
			'ConfigurationComplete': this.configurationComplete,
			'SetEventGPIO': this.setEventGPIO,
			'StatusEventGPIO': this.statusEventGPIO,
			'SetAckFailedEventGPIO': this.setAckFailedEventGPIO,
			'GetProvisionedDevicesRsp': this.getProvisionedDevicesRsp
		};
		eventBus.addListener('EchoRsp', () => {});
		eventBus.addListener('NewUnProvisionedDevice', () => {});
		eventBus.addListener('ProvisionComplete', () => {});
		eventBus.addListener('ConfigurationComplete', () => {});
		eventBus.addListener('NewProvisionedDevice', () => {});
	}
	log(msg) {
		var d = new Date();
		var timestamp = `${ d.getFullYear() }-${ d.getMonth() }-${ d.getDate() } ${ d.getHours() }:${ d.getMinutes() }:${ d.getSeconds() }.${ d.getMilliseconds() }`;
		var out = `[pyaci.js] ${ timestamp } ${ msg }`;
		this.stream.write(out + '\n');
		console.log(out);
	}
	connect() {
		try {
			this.child = cp.spawn('python3', [this.pyscript.working_dir + this.pyscript.filename].concat(this.pyscript.args), {
				cwd: this.pyscript.working_dir,
				stdio: ['pipe', 'pipe', 2]
			});
			this.output_channel = this.child.stdin;
			this.child.stdout.on('data', data => {
				var msgs = data.toString().trim().split('\n');
				msgs.forEach(m => {
					this.handle_new_message(m);
				});
			});
		} catch (error) {
			this.log(error);
			this.log('Unable to establish connection with Pyaci');
		}
	}
	disconnect() {
		var op = 'Disconnect';
		this.send(op);
		this.child.kill();
	}
	// OUTPUT
	send(op, data = null) {
		if (op == '' || op == null) {
			this.log('Error - cannot send empty message');
			return false;
		}
		var msg = { op: op };
		if (data != null) {
			msg.data = data;
		}
		var msg_out = JSON.stringify(msg);
		this.output_channel.write(msg_out + '\n');
		var log = `TX ${ msg_out }`;
		this.log(log);
		return true;
	}
	echo(msg) {
		var op = 'Echo';
		return this.send(op, msg);
	}
	provisionScanStart() {
		var op = 'ProvisionScanStart';
		return this.send(op);
	}
	getProvisionedDevices() {
		var op = 'GetProvisionedDevices';
		return this.send(op);
	}
	provision(uuid, name = null) {
		var op = 'Provision';
		if (uuid == '' || uuid == null) {
			this.log(`Provision error uuid cannot be empty`);
			return false;
		}
		;
		var data = { uuid: uuid };
		if (name) {
			data.name = name;
		}
		return this.send(op, data);
	}
	configure(uuid) {
		var op = 'Configure';
		if (uuid == '' || uuid == null) {
			this.log(`configure - error uuid cannot be empty `);
			return false;
		}
		var data = { uuid: uuid };
		return this.send(op, data);
	}
	configureGPIO(asInput, pin, uuid) {
		var op = 'ConfigureGPIO';
		if (typeof asInput != 'boolean' || asInput == null) {
			this.log('Input error configureGPIO - asInput');
			return false;
		}
		if (typeof pin != 'number' || pin < 0 || pin == null) {
			this.log('Input error configureGPIO - pin');
			return false;
		}
		if (typeof uuid != 'string' || uuid == '' || uuid == null) {
			this.log('Input error configureGPIO - uuid');
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
		var op = 'SetGPIO';
		if (typeof onoff != 'boolean' && typeof onoff != 'number') {
			this.log('Input error setGPIO - onoff');
			return false;
		}
		if (typeof onoff === 'number' && (onoff < 0 || onoff > 1)) {
			this.log('Input error setGPIO - onoff');
			return false;
		}
		if (typeof pin != 'number' || pin < 0 || pin == null) {
			this.log(`Input error setGPIO - pin: ${ pin }`);
			return false;
		}
		if (typeof uuid != 'string' || uuid == '' || uuid == null) {
			this.log('Input error setGPIO - uuid');
			return false;
		}
		var data = {
			value: onoff,
			pin: pin,
			uuid: uuid
		};
		return this.send(op, data);
	}
	getGPIO(pin, uuid) {
		var op = 'GetGPIO';
		if (typeof pin != 'number' || pin < 0 || pin == null) {
			this.log(`Input error getGPIO - pin: ${ pin }`);
			return false;
		}
		if (typeof uuid != 'string' || uuid == '' || uuid == null) {
			this.log('Input error getGPIO - uuid');
			return false;
		}
		var data = {
			pin: pin,
			uuid: uuid
		};
		return this.send(op, data);
	}
	setName(uuid, name) {
		var op = 'SetName';
		if (typeof uuid != 'string' || uuid == '' || uuid == null) {
			this.log('Input error setName - uuid');
			return false;
		}
		if (typeof name != 'string' || name == '' || name == null) {
			this.log('Input error setName - name');
			return false;
		}
		var data = {
			name: String(name),
			uuid: uuid
		};
		return this.send(op, data);
	}
	removeNode(uuid) {
		var op = 'RemoveNode';
		if (typeof uuid != 'string' || uuid == '' || uuid == null) {
			this.log('Input error removeNode - uuid');
			return false;
		}
		var data = { uuid: uuid };
		return this.send(op, data);
	}
	// INPUT
	handle_new_message(msg_in) {
		try {
			var msg = JSON.parse(msg_in);
			var op = msg.op;
			var data = msg.data;
			var log = `RX ${ JSON.stringify(msg) }`;
			this.log(log);
		} catch (err) {
			this.log(`Parse Failed: ${ msg_in }`);
			return;
		}
		try {
			this.input_listeners[op](data);
		} catch (err) {
			this.log(`Failed trying response to ${ op }`);
			this.log(err);
			return;
		}
	}
	echoRsp(data) {
		eventBus.emit('EchoRsp', data);
	}
	newUnProvisionedDevice(data) {
		eventBus.emit('NewUnProvisionedDevice', data);
	}
	getProvisionedDevicesRsp(data) {
		eventBus.emit('NewProvisionedDevice', data);
	}
	provisionComplete(data) {
		eventBus.emit('ProvisionComplete', data);
	}
	configurationComplete(data) {
		eventBus.emit('ConfigurationComplete', data);
	}
	setEventGPIO(data) {
		var uuid = data.uuid;
		eventBus.emit('SetEventGPIO_' + uuid, data);
	}
	statusEventGPIO(data) {
		var uuid = data.uuid;
		eventBus.emit('StatusEventGPIO_' + uuid, data);
	}
	setAckFailedEventGPIO(data) {
		var uuid = data.uuid;
		eventBus.emit('SetAckFailedEventGPIO_' + uuid, data);
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