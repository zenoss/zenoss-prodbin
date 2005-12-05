var refreshControl, loadStatusDefered;
var autoRefresh = 0;
dojo.require("dojo.io.bind");
//dojo.require("dojo.io.*");

errorHandler = function(type,error) {
    log("error loading events type=", type);
    log("msg=", error.message);
    log("code=", error.number);
    resetLoadStatus();
    errmsg = TBODY('eventsBody',TR(null,
            TD(null,{'class':'errorTitle'},'Events Unavailable')));
    swapDOM("eventsBody", errmsg);
}

processData = function(type, data, evt) {
    log("processingData status=", evt.statusText);
    /*bodyNode = req.responseXML.getElementById("eventsBody");
    log("processingData tbody=", bodyNode.id);*/
    if (evt.status == 200) {
        renderTableBody(data);
    }
};

//render the table rows by putting the returned data into the tbody element.
renderTableBody = function(html) {
    log("renderTableBody");
    resetLoadStatus();
    evbody = document.getElementById("eventsBody");
    evbody.innerHTML = html;
    document.forms.control.resetStart.value = 0;
};

var statusCount = 0;
loadStatus = function() {
    node = document.getElementById("loadingStatus");
    if (node) {
        msg = "loading...";
        for (var i=0;i<statusCount;i++) {
            msg = msg + ".";
        }
        log("status msg=", msg);
        node.innerHTML = msg;
        statusCount += 1;
        return callLater(1,loadStatus);
    }
};

resetLoadStatus = function() {
    if (loadStatusDefered) { //very stange if this isn't defined
        loadStatusDefered.cancel();
        loadStatusDefered = null;
        statusCount = 0;
    }
};

//load the event list using dojo.io.bind
getTablePage = function(form) {
    log("getTablePage url=", form.url.value);
    if (refreshControl) { refreshControl.cancel(); }
    if (loadStatusDefered) { //oh shit we are resubmiting!
        log("resubmit while query pending!!") 
        return
    } else {
        loadStatusDefered = loadStatus()
    }
    dojo.io.bind({url: form.url.value, formNode: form, 
        load: processData,
        error: errorHandler,
        mimetype:"text/plain"})
    rate = parseInt(form.refreshRate.value)
    if (autoRefresh) {
        refreshControl = callLater(rate,getTablePage,form);
    }
};

//set the sortedHeader and sence and submit form
setSortedHeader = function(name, form) {
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
getPageNavButton = function(name, form) {
    form.navbutton.value = name;
    log("navbutton=", form.navbutton.value);
    getTablePage(form);
}

//look for enter press while in text input and execute getTablePage
getPageViaEnter = function(evt) {
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


startRefresh = function(button, form) {
    if (autoRefresh) {
        log("stopAutoRefresh");
        refreshControl.cancel()
        button.value = 'Start Auto-Refresh';
        autoRefresh=0
    } else {
        log("startAutoRefresh");
        button.value = 'Stop Auto-Refresh';
        autoRefresh=1
        getTablePage(form);
    }
};

//display an event detail in its own native window
eventWindow = function(manager, evid, width, height) {
    url = "/zport/dmd/"+manager+"/viewEventFields?evid=" + evid
    windowprops = "width=500,height=650,resizable=yes,scrollbars=yes";
    evwindow = window.open(url, evid, windowprops);
    evwindow.focus();
}
