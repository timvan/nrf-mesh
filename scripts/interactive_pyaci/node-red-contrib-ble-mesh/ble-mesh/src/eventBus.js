const EventEmitter = require('events');
const emitter = new EventEmitter();
emitter.setMaxListeners(32)
module.exports = emitter;