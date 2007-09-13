YAHOO.namespace('zenoss.zenautocomplete');
YAHOO.namespace('zenoss.env');

YAHOO.zenoss.env.cache = new Object();
YAHOO.zenoss.getRemoteData = function(name, url, callback) {
    var o = YAHOO.zenoss.env.cache;
    var d = new Deferred();
    var e = new Deferred();
    d.addCallback(function(){return e;});
    d.addCallback(function(r){
        o[name] = r; 
        return r
    });
    d.addCallback(callback);
    e.addCallback(function(){
        if (o[name]) return o[name];
        else return loadJSONDoc(url);
    });
    d.callback();
    e.callback();
    return d;
}

YAHOO.zenoss.zenautocomplete.ZenAutoComplete = Class.create();
YAHOO.zenoss.zenautocomplete.ZenAutoComplete.prototype = {
    __init__: function(name, url, label, container) {
        bindMethods(this);
        this.input = INPUT({'id':'results'+new Date().getTime()}, null);
        this.results = DIV({'id':'results'+new Date().getTime()}, null);
        this.target = $(container);
        this.container = DIV({'class':'autocompleter-container'}, null);
        addElementClass(this.target, 'yui-skin-sam');
        wrapper = DIV(null, null);
        appendChildNodes(wrapper, this.input, this.results);
        appendChildNodes(this.container,
                         DIV({'class':'control-label'}, label), 
                         wrapper);
        appendChildNodes(this.target, this.container);
        var makeAutoCompleter = method(this, function(locarray) {
            this.oACDS = new YAHOO.widget.DS_JSArray(locarray, {
                queryMatchContains:true});
            this.oAutoComp = new YAHOO.widget.AutoComplete(this.input, 
                this.results, this.oACDS);
            this.oAutoComp.typeAhead = false;
            this.oAutoComp.useShadow = true;
            this.oAutoComp.minQueryLength = 0;
            var mythis = this;
            this.oAutoComp.textboxFocusEvent.subscribe(function(){
                var sInputValue = mythis.input.value;
                if(sInputValue.length===0) {
                    var oSelf = this;
                    setTimeout(function(){oSelf.sendQuery(sInputValue);},0);
                }
            });
        });
        YAHOO.zenoss.getRemoteData(name, url, makeAutoCompleter);
    }
}




YAHOO.register('zenautocomplete', YAHOO.zenoss.zenautocomplete, {});
