module.exports = function(RED) {
    function LogicAnd(config) {
        RED.nodes.createNode(this,config);
        var node = this;
        
        this.n_inputs = config.n_inputs;
        this.states = {};

        console.log(config);

        checkOn = function(_states) {
            if(Object.values(_states).includes(0)){
                return 0;
            }
            return 1;
        }

        node.on('input', function(msg) {
            // var address = String(msg);
            var value = msg.payload.value;

            if(Object.keys(this.states).includes(address)){
                this.states[address] = value;
            } else {
                if(Object.keys(this.states).length < this.n_inputs){
                    this.states[address] = value;
                } else {
                    node.error("Too many inputs");
                    return;
                }
            }
            
            console.log(JSON.stringify(this.states));
            console.log(checkOn(this.states));
            
            if(Object.keys(this.states).length == this.n_inputs){
                node.send({
                    payload: {
                        value: checkOn(this.states)
                    }
                })
            }

        });

        
    }
    RED.nodes.registerType("logic-and",LogicAnd);
}