//################################################################
//
//   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
//
//################################################################


// Refresh rate in seconds
var refresh=20

//display an event detail in its own native window
eventWindow = function(manager, evid, width, height) {
    url = "/zport/dmd/"+manager+"/viewEventFields?evid=" + evid
    windowprops = "width=500,height=650,resizable=yes,scrollbars=yes";
    evwindow = window.open(url, evid, windowprops);
    evwindow.focus();
}

devlink = function(name) {
    return A({href:"/zport/dmd/deviceSearchResults?query=" + name}, name)
}

orglink = function(name) {
    return A({href:"/zport/dmd/Systems" + name}, name)
}

eventUpdate = function(rows) {
    log("           update events");
    var tb = TBODY({'id':'events'})
    for (var i=0;i<rows.length;i++) {
        row = rows[i];
        evid = row.pop();
        sev = row.pop()
        state = row.pop();
        classname = "zenevents_" + sev + "_noack";
        var tr = TR({'class': classname})
        for (var j=0;j<row.length;j++) {
            if (j == 0) {
                appendChildNodes(tr, TD(null, devlink(row[j])));
            } else {
                appendChildNodes(tr, TD(null, row[j]));
            }
        }
        appendChildNodes(tb, tr);
    }
    swapDOM("events", tb);
}


statusUpdate = function(id, data) {
    newbody = TBODY({'class':'tablevalues', 'id':id});
    for (var r=0; r<data.length;r++) {
        var tr = TR(null);
        var row = data[r];
        for (var i=0;i<row.length;i++) {
            if (i == 0) {
                var a;
                if (id.indexOf("dev") == 0) {
                    a = devlink(row[i]);
                } else {
                    a = orglink(row[i]);
                }
                appendChildNodes(tr, TD(null, a));
            } else {
                appendChildNodes(tr, TD(null, row[i]));
            }
        }
        appendChildNodes(newbody,tr);
    }
    swapDOM(id, newbody);
}


updateDashboard = function(data) {
    log("               got data");
    for (var id in data) {
        if (id == "events") {
            eventUpdate(data[id]);
        } else {
            statusUpdate(id, data[id]);
        }
    }
    callLater(refresh, refreshData);
}

updateError = function(err) {
    if (err instanceof CancelledError) {
        return;
    }
    logError(err);
    var tb = TBODY({'id':'events'},TR({'class':'errortitle'},
                TD({'colspan':'4'}, "Lost Connection to Zenoss")));
    swapDOM('events', tb)
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
