var page = require('webpage').create(),
    system = require('system'),
    address, output, size, username, password, outputFile,
    pageZoomFactor, pageFormat;

//phantomjs rasterize.js URL USERNAME PASSWORD PDF
if (system.args.length < 5 || system.args.length > 7) {
    console.log('Usage: rasterize.js URL username password output_filename [paperwidth*paperheight|paperformat] [zoom]');
    console.log('  paper (pdf output) examples: "5in*7.5in", "10cm*20cm", "A4", "Letter"');
    phantom.exit(1);
} else {
    address = system.args[1];
    username = system.args[2];
    password = system.args[3];
    outputFile = system.args[4];
    pageFormat = system.args[5] || "Letter";
    pageZoomFactor = system.args[6] || 1;

    page.settings.localToRemoteUrlAccessEnabled = true;
    page.settings.resourceTimeout = 10000;

    // use the provided username and password if they were provided
    if (username != "nil" && password != "nil") {
        page.customHeaders={'Authorization': 'Basic '+btoa(username + ':' + password)};
    } else {
        console.log('Username and password were not provided');
    }

    page.viewportSize = { width: 850, height: 1100 };
    page.zoomFactor = pageZoomFactor;
    page.paperSize = {
        format: pageFormat,
        orientation: "landscape",
        margin: "0.25in"
    };

    page.open(address, function (status) {
        if (status !== 'success') {
            console.log('Unable to load the address!');
            phantom.exit(1);
        } else {
            window.setTimeout(function () {
                page.render(outputFile);
                phantom.exit(0);
            }, 1000);
        }
    });
}
