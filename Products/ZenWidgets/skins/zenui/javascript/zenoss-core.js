// Graceful degradation of Firebug console object
// via http://ajaxian.com/archives/graceful-degradation-of-firebug-console-object
if (! ("console" in window) || !("firebug" in console)) {
    var names = ["log", "debug", "info", "warn", "error", "assert", "dir", "dirxml", "group"
                 , "groupEnd", "time", "timeEnd", "count", "trace", "profile", "profileEnd"];
    window.console = {};
    for (var i = 0; i <names.length; ++i) window.console[names[i]] = function() {};
}

// Set up the Javascript loader
function getLoader() {
    loader = new YAHOO.util.YUILoader({
        onProgress: function(o) {
            console.info(o.name + " module loaded.");
        },
        onFailure: function(msg, xhrreq) {
            console.warn('FAILURE: ' + msg)
        }
    });
    loader.base = '/zport/dmd/yui/';

    // Register zenoss scripts
    loader.addModule({
        name: "datatablesamskin",
        type: "css",
        fullpath: "/zport/dmd/yui/datatable/assets/skins/sam/datatable.css"
    });
    loader.addModule({
        name: "autocompleteskin",
        type: "css",
        fullpath: "/zport/dmd/yui/autocomplete/assets/skins/sam/autocomplete.css"
    });
    loader.addModule({
        name: "zenautocomplete",
        type: "js",
        fullpath: "/zport/dmd/javascript/zenautocomplete.js",
        requires: ["autocomplete", "animation", "autocompleteskin","zenossutils"]
    });
    loader.addModule({
        name: "portlet",
        type: "js",
        fullpath: "/zport/dmd/javascript/portlet.js",
        requires: ["dragdrop", "event", "dom", "animation", 
                   "datasource", "datatable", "datatablesamskin",
                   "container", "button","zenautocomplete", "zenossutils"]
    });
    loader.addModule({
        name: "portletsource",
        type: "js",
        fullpath: "/zport/ZenPortletManager/get_source",
        requires: ["portlet"]
    });
    loader.addModule({
        name: "zenossutils",
        type: "js",
        fullpath: "/zport/javascript/zenoss-utils.js",
        requires: ['dom', 'event']
    });
    loader.addModule({
        name: "devicezengrid",
        type: "js",
        fullpath: "/zport/dmd/javascript/devicezengrid.js",
        requires: ['zenossutils']
    });
    loader.addModule({
        name: "eventzengrid",
        type: "js",
        fullpath: "/zport/dmd/javascript/zengrid.js",
        requires: ['zenossutils']
    });
    loader.addModule({
        name: 'geomap',
        type: 'js',
        fullpath: '/zport/dmd/javascript/geomap.js',
        requires: ['zenossutils', 'container']
    });
    loader.addModule({
        name: 'simplegeomap',
        type: 'js',
        fullpath: '/zport/dmd/javascript/geomap-2.1.js',
        requires: ['zenossutils', 'container']
    });
    loader.addModule({
        name: 'swoopygraphs',
        type: 'js',
        fullpath: '/zport/dmd/zenrrdzoom.js',
        requires: ['zenossutils']
    });
    return loader;
}

//Declare the Zenoss namespace
YAHOO.namespace("zenoss");

// Put the loader somewhere accessible
YAHOO.zenoss.getLoader = getLoader;

