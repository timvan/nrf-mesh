const EventEmitter = require('events');
const emitter = new EventEmitter();
emitter.setMaxListeners(15)
module.exports = emitter;