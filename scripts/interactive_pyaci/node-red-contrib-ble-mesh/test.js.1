const { spawn } = require('child_process');
function run() {

    const process = spawn('python', ['--version']);

    process.stdout.on(
      'data', (data) => {console.log(data.toString())}
    );
  
    process.stderr.on(
      'err', (err) => {console.log(err.toString())}
    );

    
    const pyaci = spawn('python'
        , ['stdio-test.py']
        , {stdio: ['pipe', 'pipe', 2]}
        
    );

    pyaci.stdout.on(
      'data', (data) => {console.log(data.toString())}
    );

    pyaci.stdout.on('close', () => {
        console.log(`stdout close`);
    });

    pyaci.on('exit', (code, signal) => {
        console.log(`pyaci exited ${code} ${signal}`);
    });

    pyaci.stdin.write("echo\n");

    console.log("fin")
    console.log(pyaci.connected);

    // pyaci.kill()

}

(() => {
    try {
        run()
        // process.exit(0)
    } catch (e) {
        console.error(e.stack);
        process.exit(1);
    }
})();
