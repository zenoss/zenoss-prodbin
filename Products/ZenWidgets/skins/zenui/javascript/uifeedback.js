(function() { // Let's use a private namespace, please

var Z = YAHOO.zenoss,            // Internal shorthand
    Y = YAHOO.util,              // Internal shorthand
    W = YAHOO.widget,            // Internal shorthand
    INFO     = 0,                // Same as in messaging.py
    WARNING  = 1,                // Same as in messaging.py
    CRITICAL = 2,                // Same as in messaging.py
    body = window.document.body, // Cache to save lookups
    Yowl = document.Yowl,        // Cache to save lookups
    pollInterval = 1000*30,      // 60 seconds
    priorities = ['low', 'high', 'emergency'],
    icons = ['/zport/dmd/img/agt_action_success-32.png',
             '/zport/dmd/img/messagebox_warning-32.png',
             '/zport/dmd/img/agt_stop-32.png'];

// Set up Yowl to be called by the Messenger
Yowl.register( 'zenoss', ['info'], ['info'],
    //Default image is a check mark
    '/zport/dmd/img/agt_action_success-32.png'
);

/**
 * A modified XHRDataSource that can accept a callable for request
 * parameters. Useful for preventing caching by sending current time with
 * requests.
 */
Z.CallableReqDS = function(oLiveData, oConfigs) {
    // Workaround for bug #2176072 in YUI 2.6.0
    this.constructor = Y.XHRDataSource;
    // Chain constructors
    Z.CallableReqDS.superclass.constructor.call(this, oLiveData, oConfigs);
    // Set constructor back (also part of fix)
    this.constructor = Z.CallableReqDS;
}
YAHOO.lang.extend(Z.CallableReqDS, Y.XHRDataSource);

Z.CallableReqDS.prototype.makeConnection = function(oRequest, oCallback, 
                                                  oCaller) {
    if (typeof(oRequest)=='function') oRequest = oRequest();
    Z.CallableReqDS.superclass.makeConnection.call(this, oRequest, 
                                                 oCallback, oCaller)
}

// Return an IE-cache-busting query string.
function _defeatCaching(){return '?_dc='+new Date().getTime()}

/**
 * Provide our own custom ConnectionManager that lets us keep track of the
 * outstanding connection so we can then later abort the connection and
 * prevent our failure callback from being called when it really shouldn't
**/
Z.ConnectionManager = {

    lastConn: null,

    abort: function(conn) {
        return Y.Connect.abort(conn);
    },

    abortAll: function() {
        this.abort(this.lastConn);
    },

    asyncRequest: function(method, uri, callback, postData) {
        this.lastConn = Y.Connect.asyncRequest(method, uri, callback, postData);
        return this.lastConn;
    },

    isCallInProgress: function(conn) {
        return Y.Connect.isCallInProgress(conn);
    }
};

/** 
 * register a listener for the beforeunload event so that we can cancel
 * outstanding connections
**/
Y.Event.addListener(window, "beforeunload", function(event) {
    Z.ConnectionManager.abortAll();
});

/**
 * Singleton object that accepts messages both directly and from periodic
 * polling of the server, and displays them in the browser.
**/
Z.Messenger = {

    // Start the polling off real good
    initialize: function() {
        this.startPolling(pollInterval); 
    },

    // Source of remote data
    datasource: new Z.CallableReqDS(
        // Pointer to live data
        "/zport/dmd/getUserMessages", 
        // Config object
        { 
            connMgr: Z.ConnectionManager,
            connXhrMode: "cancelStaleRequests",
            responseType: Y.XHRDataSource.TYPE_JSON, 
            responseSchema: {
                resultsList: "messages",
                fields:[
                    "sticky",
                    "title",
                    "image",
                    "body", 
                    {key: "priority", type: "number"}
                ],
                metaFields: {
                    totalRecords: 'totalRecords'
                }
            },
            maxCacheEntries: 0
        }
    ),

    // Callbacks for remote data; also handle connection errors
    callbacks: {
        success: function(r, o) {
            forEach(o.results, Z.Messenger.send);
        },

        failure: function() {
            Z.Messenger.connectionError();
        }
    },

    // Ask the server once for new messages
    checkMessages: function() {
        this.datasource.sendRequest(null, this.callbacks);
    },

    // Ask the server for messages once, then keep asking every interval ms
    startPolling: function(interval) {
        this.checkMessages();
        this.datasource.setInterval(interval, _defeatCaching, this.callbacks);
    },

    stopPolling: function() {
        this.datasource.clearAllIntervals();
    },

    // Shorthand to signify a connection error. Can be used by whatever.
    connectionError: function(msg) {
        var msg = msg || "Server connection error.";
        this.stopPolling();
        this.critical(msg);
    },

    // Put a message into the browser
    send: function(msgConfig) {
        var text     = msgConfig.body,
            title    = (msgConfig.title || "FYI"),
            priority = priorities[msgConfig.priority],
            image    = (msgConfig.image || icons[msgConfig.priority]),
            sticky   = (msgConfig.sticky || false);
        Yowl.notify('info', title, text, 'zenoss', image, sticky, priority);
    },

    // Shortcut to send severity INFO messages
    info: function(message) {
        this.send({
            title: "Information",
            body: message,
            priority: INFO
        })
    },

    // Shortcut to send severity WARNING messages
    warning: function(message) {
        this.send({
            title: "Warning",
            body: message,
            priority: WARNING
        })
    },

    // Shortcut to send severity CRITICAL messages
    critical: function(message) {
        this.send({
            title: "Error",
            body: message,
            priority: CRITICAL,
            sticky: true
        })
    }


}; // end Z.Messenger


})(); // end private namespace

YAHOO.register("uifeedback", YAHOO.zenoss.Messenger, {});
