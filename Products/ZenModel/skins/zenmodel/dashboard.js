//################################################################
//
//   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
//
//################################################################


// Refresh rate in seconds
var refresh=30;
var cancelSecs=10;
//var url="data.json";

// Look for stupid IE browsers
var isie = navigator.userAgent.indexOf('MSIE') != -1;

function updateTimestamp(){
    $("dashTime").innerHTML = "<b>Refreshing...</b>";
    callLater(1,updateTimestampNow);
}

function updateTimestampNow(){
    var d = new Date();
    var h = "Last Updated: ";
    h += toISOTimestamp(d)
    $("dashTime").innerHTML = h;
}


statusUpdate = function(id, data) {
    /* draw clear then draw the rows of the tbody */
    //log("drawTableBody "+id);
    var tbody = null;
    if (isie) {
        tbody = $(id);
        clearTableBody(tbody);
    } else {
        tbody = TBODY({'id':id});
    }
    for (var r=0; r<data.length;r++) {
        var tr = tbody.insertRow(tbody.rows.length);
        setElementClass(tr, "tablevalues");
        var row = data[r];
        for (var j=0; j<row.length; j++) {
            var td = tr.insertCell(tr.cells.length);
            if (row[j].cssclass) { 
                setElementClass(td, row[j].cssclass);
                td.innerHTML = row[j].data;
            } else if (typeof(row[j]) == "string") {
                td.innerHTML = row[j]
            }
        }
    }
    if (!isie) swapDOM(id, tbody);
}

clearTableBody = function(tbody) {
    /* remove all rows from table */
    while (tbody.rows.length > 0) {
        tbody.deleteRow(0);
    }
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


updateDashboard = function(data) {
    //log("got data");
    for (var id in data) {
        statusUpdate(id, data[id]);
    }
    updateTimestamp();
    callLater(refresh, refreshData);
}

updateError = function(err) {
    logError(err);
    $("dashTime").innerHTML = "<b class='errortitle'>Lost Connection to Zenoss</b>";
    callLater(refresh, refreshData);
}

refreshData = function(url) {
    //logger.debuggingBookmarklet(true)
    //log("loading");
    var defr = cancelWithTimeout(
        loadJSONDoc(url), cancelSecs);
    defr.addCallback(updateDashboard);
    defr.addErrback(updateError);
}

normalDashboard = function() {
    var url = "/zport/dmd/ZenEventManager/getDashboardInfo";
    refreshData(url)
}

simpleDashboard = function() {
    var url = "/zport/dmd/ZenEventManager/getDashboardInfo?simple:boolean=True";
    refreshData(url)
}
