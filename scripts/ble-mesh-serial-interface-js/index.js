'use strict';

const BLEMeshSerialInterface = require('ble-mesh-serial-interface-js/BLEMeshSerialInterface');

const MESH_ACCESS_ADDR = 0x8E89BED6;
const MESH_INTERVAL_MIN_MS = 100;
const MESH_CHANNEL = 38;
const COM_PORT = '/dev/tty.usbmodem0006822145041';

const ble = new BLEMeshSerialInterface();

ble.openSerialPort(COM_PORT, err => {
  console.log("Try open");

  if (err) {
    console.log(err);
  }

  const buf = new Buffer([0x01]);
  
  ble.echo(buf, (err, res) => {
    console.log("Try echo");

    if (err) {
      console.log("Error in echo");
      console.log(err);
    }
    if (res) {
      console.log("Res: ", res);
    }
  });

  ble.init(MESH_ACCESS_ADDR, MESH_INTERVAL_MIN_MS, MESH_CHANNEL, (res, err) => {
    console.log("Try init");
    
    if (err) {
      console.log("Error in init");
      console.log(err);
    }
  
  })
});
