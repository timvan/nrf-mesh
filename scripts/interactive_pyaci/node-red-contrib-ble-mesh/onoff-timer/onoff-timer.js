module.exports = function(RED) {
    function OnOffTimer(config) {
        RED.nodes.createNode(this,config);
        var node = this;
        
        var interval = config.interval;

        node.on('input', (msg) => {
            this.on = msg.payload;
        });


        this.send = (value) => {

            if(value){
                node.send({payload: 1});
            } else {
                node.send({payload: 0});
            }

            setTimeout(this.send, interval, !value);
        }

        this.send(false);


        
    }
    RED.nodes.registerType("onoff-timer",OnOffTimer);
}