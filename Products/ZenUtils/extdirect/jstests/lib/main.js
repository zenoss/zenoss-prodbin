// load up an empty html page so that onReady fires
Envjs('index.html');

// wait for all the callbacks to run
Envjs.wait(2000);

// print results
Ext.each(results, function(result) {
    print(result);
});

// exit using the total failures as the exit status
quit(exit_status);
