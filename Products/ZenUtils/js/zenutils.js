postJSONDoc = function (url, postVars) {
        var req = getXMLHttpRequest();
        req.open("POST", url, true);
        req.setRequestHeader("Content-type", 
                             "application/x-www-form-urlencoded");
        var data = queryString(postVars);
        var d = sendXMLHttpRequest(req, data);
        return d.addCallback(evalJSONRequest);

}
var cancelWithTimeout = function (deferred, timeout) { 
    var canceller = callLater(timeout, function () { 
        // cancel the deferred after timeout seconds 
        deferred.cancel(); 
        //log("cancel load data")
    }); 
    return deferred.addCallback(function (res) { 
        // if the deferred fires successfully, cancel the timeout 
        canceller.cancel(); 
        return res; 
    }); 
}; 
