function notifyParentOfNewUrl() {
    try {
          var parwin = currentWindow().parent;
          var url = location.href;
          parwin.zmlistener.checkForDomainChange(url);
        } 
    catch(e){ noop() }
}

addLoadEvent(notifyParentOfNewUrl);
