var page = require('webpage').create(),
    system = require('system'),
    address, output, size;

//phantomjs rasterize.js USERNAME PASSWORD URL PDF
if (system.args.length < 5 || system.args.length > 7) {
    console.log('Usage: rasterize.js URL username password output_filename [paperwidth*paperheight|paperformat] [zoom]');
    console.log('  paper (pdf output) examples: "5in*7.5in", "10cm*20cm", "A4", "Letter"');
    phantom.exit(1);
} else {
    address = system.args[1];
    username = system.args[2];
    password = system.args[3];
    outputFile = system.args[4];
    
    page.settings.localToRemoteUrlAccessEnabled = true;
    page.settings.resourceTimeout = 10000
    
    // use the provided username and password if they were provided
    if (username != "nil" && password != "nil") {
        page.customHeaders={'Authorization': 'Basic '+btoa(username + ':' + password)};
    } else {
        console.log('Username and password were not provided');
    }

    page.viewportSize = { width: 800, height: 800 };
    if (system.args.length > 5 && system.args[2].substr(-4) === ".pdf") {
        pageFormat = system.args[5]
        size = system.args[3].split('*');
        page.paperSize = size.length === 2 ? { width: size[0], height: size[1], margin: '0px' }
                                           : { format: pageFormat, orientation: 'portrait', margin: '1cm' };
    }

    if (system.args.length > 6) {
        pageZoomFactor = system.args[6];
        page.zoomFactor = pageZoomFactor;
    }

    page.open(address, function (status) {
        if (status !== 'success') {
            console.log('Unable to load the address!');
            phantom.exit();
        } else {
            window.setTimeout(function () {
                page.render(outputFile);
                phantom.exit();
            }, 200);
        }
    });
}
