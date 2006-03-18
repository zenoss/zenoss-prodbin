//################################################################
//
//   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
//
//################################################################


// Refresh rate in seconds
var refresh=20;

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
    newbody = TBODY({'class':'tablevalues', 'id':id});
    log("statusupdate");
    for (var r=0; r<data.length;r++) {
        var tr = TR(null);
        var row = data[r];
        for (var j=0; j<row.length; j++) {
            appendChildNodes(tr, mkTableData(row[j]));
        }
        appendChildNodes(newbody, tr);
    }
    swapDOM(id, newbody);
}


mkTableData = function(data) {
    //make a TD object based on data passed in
    //if {href:"/zport/dmd/System/Dev",content:"/Dev"} its an A 
    //if ['zenevents_5_noak", 0, 6] its a event status field
    //if typeof(data) == string plain old TD
    var td = null
    if (typeof(data) == "object") {
        if (data.href) { 
            log("href " + data.content);
            td = TD(null, A(data, data.content))
        } else if (data.cssclass) {
            log("css " + data.content);
            td = TD(data, data.content)
        } else if (data.length==3) {
            log("evtstatus " + repr(data));
            if (data[2] > 0)
                td = TD({"class":data[0]},data[1]+"/"+data[2]) 
            else
                td = TD(null, "0/0")
        } else {
            td = TD(null, "")
        }
    } else {
        log("plain " + data);
        td = TD(null, data)
    }
    return td
}

updateDashboard = function(data) {
    log("got data");
    for (var id in data) {
        statusUpdate(id, data[id]);
    }
    updateTimestamp();
    callLater(refresh, refreshData);
}

updateError = function(err) {
    if (err instanceof CancelledError) {
        return;
    }
    logError(err);
    $("dashTime").innerHTML = "<b class='errortitle'>Lost Connection to Zenoss</b>";
    callLater(refresh, refreshData);
}

refreshData = function() {
    //logger.debuggingBookmarklet(true)
    log("loading");
    var defr = loadJSONDoc("/zport/dmd/ZenEventManager/getDashboardInfo")
    defr.addCallback(updateDashboard)
    defr.addErrback(updateError)
}

addLoadEvent(refreshData);
