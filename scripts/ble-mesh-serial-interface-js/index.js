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

  console.log("Try echo");
  const data = [68, 69, 69];
  ble.echo(data, (err, res) => {
    if (err) {
      console.log(err);
    }

    if (res) {
      console.log("Res:", res);
    }
  });

  ble.provStartScan((err, res) => {
    if (err) {
      console.log(err);
    }

    if (res) {
      console.log("Res:", res);
    }
  });
});
