//################################################################
//
//   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
//
//################################################################


// Refresh rate in seconds
var refresh=30;
var cancelSecs=15;
var url = "/zport/dmd/ZenEventManager/getDashboardInfo";

var sysevts = '<table class="zentable" cellpadding="3" cellspacing="1">';
sysevts += '<thead><tr class="tabletitle"><th colspan="6">Systems</tr>';
sysevts += '<tr class="tableheader">
sysevts += '<th>System</th><th>Critical</th><th>Error</th>';
sysevts += '<th>Warn</th><th>Info</th><th>Debug</th>
sysevts += '</tr></thead>';

var devevts = '<table class="zentable" cellpadding="3" cellspacing="1">';
devevts += '<thead><tr class="tabletitle"><th colspan="4">';
devevts += '<a style="color: white" href="/zport/dmd/Devices/viewEvents/">';
devevts += 'Devices</a> with Events (Severity &gt;= Error)</th></tr>';
devevts += '<tr class="tableheader">
devevts += '<th>Name</th><th>Acked By</th><th>Critical</th><th>Error</th>
devevts += '</tr></thead>';
            

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
    //newbody = TBODY({'class':'tablevalues', 'id':id});
    log("statusupdate "+id);
    var table = new Array();
    table.push(sysevts);
    table.push("<tbody>");
    for (var r=0; r<data.length;r++) {
        table.push("<tr>");
        var row = data[r];
        for (var j=0; j<row.length; j++) {
            table.push(mkTableData(row[j]));
        }
        table.push("</tr>");
    }
    table.push("</tbody></table>");
    var stable = table.join("");
    //log(stable);
    $(id).innerHTML = stable;
}


mkTableData = function(data) {
    //make a TD object based on data passed in
    //if {href:"/zport/dmd/System/Dev",content:"/Dev"} its a link
    //if ['zenevents_5_noak", 0, 6] its a event status field
    //if typeof(data) == string plain old TD
    var td = "";
    if (typeof(data) == "object") {
        if (data.href) { 
            //log("href " + data.content);
            td = "<td><a href='"+data.href+"'>"+data.content+"</a></td>";
        } else if (data.cssclass) {
            //log("css " + data.content);
            var content = data.content
            delete data.content
            td = "<td class='"+data.cssclass+"'>"+data.content+"</td>";
        } else if (data.length==3) {
            //log("evtstatus " + repr(data));
            if (data[1] == data[2]) {
                //event count == acked count no severity background
                td = "<td align='right'>"+data[1]+"/"+data[2]+"</td>";
            } else if (data[2] > 0) {
                //event count > 0 add severity background
                td = "<td align='right' class='"+data[0]+"'>";
                td += data[1]+"/"+data[2]+"</td>";
            } else {
                //no events 
                td = "<td align='right'>0/0</td>";
            }
        }
    } else if (typeof(data) == "string") {
        //log("plain " + data);
        td = "<td >"+data+"</td>";
    }
    return td
}

var cancelWithTimeout = function (deferred, timeout) { 
    var canceller = callLater(timeout, function () { 
        // cancel the deferred after timeout seconds 
        deferred.cancel(); 
        log("cancel load data")
    }); 
    return deferred.addCallback(function (res) { 
        // if the deferred fires successfully, cancel the timeout 
        canceller.cancel(); 
        return res; 
    }); 
}; 


updateDashboard = function(data) {
    log("got data");
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

refreshData = function() {
    logger.debuggingBookmarklet(true)
    log("loading");
    var defr = cancelWithTimeout(
        loadJSONDoc(url), cancelSecs);
    defr.addCallback(updateDashboard);
    defr.addErrback(updateError);
}

addLoadEvent(refreshData);
