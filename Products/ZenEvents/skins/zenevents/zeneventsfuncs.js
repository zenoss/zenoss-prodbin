var refreshControl, loadStatusDefered;
var autoRefresh = 0;

var printError = function(err) {
    log("error: ", err);
}

var errorHandler = function(error) {
    log("error loading events type=", error);
    resetLoadStatus();
    var node = document.getElementById("loadingStatus");
    if (node) {
	node.innerHTML = 'Events Unavailable';
    }
}

var processData = function(evt) {
    log("processingData evt=", evt);
    log("processingData status=", evt.statusText);
    /*bodyNode = req.responseXML.getElementById("eventsBody");
    log("processingData tbody=", bodyNode.id);*/
    if (evt.status == 200) {
        renderTableBody(evt.responseText);
    }
};

//render the table rows by putting the returned data into the tbody element.
var renderTableBody = function(html) {
    log("renderTableBody");
    resetLoadStatus();
    evbody = document.getElementById("eventsBody");
    /* this won't work on IE */
    evbody.innerHTML = html;
    document.forms.control.resetStart.value = 0;
};

var statusCount = 0;
var loadStatus = function() {
    var node = document.getElementById("loadingStatus");
    if (node) {
        var msg = "loading...";
        for (var i=0;i<statusCount;i++) {
            msg = msg + ".";
        }
        log("status msg=", msg);
        node.innerHTML = msg;
        statusCount += 1;
        return callLater(1,loadStatus);
    }
};

var resetLoadStatus = function() {
    if (loadStatusDefered) { //very stange if this isn't defined
        loadStatusDefered.cancel();
        loadStatusDefered = null;
        statusCount = 0;
    }
};

//load the event list
var getTablePage = function(form) {
    log("getTablePage url=", form.url.value);
    if (refreshControl) { refreshControl.cancel(); }
    if (loadStatusDefered) { // Oops! We are already resubmiting!
        log("resubmit while query pending!!") 
    } else {
        loadStatusDefered = loadStatus()
	var d = doSimpleXMLHttpRequest(form.url.value + "?" + 
				       queryString(form));
	d = cancelWithTimeout(d, 30);
	d.addCallbacks(processData, errorHandler);
	d.addErrback(printError);
    }

    if (autoRefresh) {
	var rate = parseInt(form.refreshRate.value)
        refreshControl = callLater(rate,getTablePage,form);
    }
};

//set the sortedHeader and sence and submit form
var setSortedHeader = function(name, form) {
    sence = form.sortedSence.value;
    if (name == form.sortedHeader.value) {
        if (sence == "") { sence = "asc"; }
        else if (sence == "asc") {sence = "desc";}
        else {sence = "";name=""}
    } else {
        sence = "asc";
    }
    form.sortedHeader.value = name;
    form.sortedSence.value = sence;
    log("sortedHeader=", form.sortedHeader.value);
    log("sortedSence=", form.sortedSence.value);
    getTablePage(form)
}

// load new page after navigation button is clicked.
var getPageNavButton = function(name, form) {
    form.navbutton.value = name;
    log("navbutton=", form.navbutton.value);
    getTablePage(form);
}

//look for enter press while in text input and execute getTablePage
var getPageViaEnter = function(evt) {
    evt = (evt) ? evt : event;
    var target = (evt.target) ? evt.target : evt.srcElement;
    var form = target.form;
    var charCode = (evt.charCode) ? evt.charCode : 
        ((evt.which) ? evt.which : evt.keyCode);
    if (charCode == 13 || charCode == 3) {
        form.resetStart.value=1;
        getTablePage(form);
        return false;
    }
    return true;
};


var startRefresh = function(button, form) {
    if (autoRefresh) {
        log("stopAutoRefresh");
        refreshControl.cancel()
        button.value = 'Start Refresh';
        autoRefresh=0
    } else {
        log("startAutoRefresh");
        button.value = 'Stop Refresh';
        autoRefresh=1
        getTablePage(form);
    }
};

//display an event detail in its own native window
var eventWindow = function(manager, evid, width, height) {
    url = "/zport/dmd/"+manager+"/viewEventFields?evid=" + evid
    windowprops = "width=500,height=650,resizable=yes,scrollbars=yes";
    evwindow = window.open(url, evid, windowprops);
    evwindow.focus();
}
