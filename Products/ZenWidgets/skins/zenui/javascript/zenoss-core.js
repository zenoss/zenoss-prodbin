// Set up the Javascript loader
loader = new YAHOO.util.YUILoader();
loader.base = '/zport/dmd/yui/';

// Register zenoss scripts
loader.addModule({
    name: "datatablesamskin",
    type: "css",
    fullpath: "/zport/dmd/yui/datatable/assets/skins/sam/datatable.css"
});
loader.addModule({
    name: "autocompleteskin",
    type: "css",
    fullpath: "/zport/dmd/yui/autocomplete/assets/skins/sam/autocomplete.css"
});
loader.addModule({
    name: "portlet",
    type: "js",
    fullpath: "/zport/dmd/javascript/portlet.js",
    requires: ["dragdrop", "event", "dom", "animation", 
               "datasource", "datatable", "datatablesamskin",
               "container", "button","zenautocomplete"]
});
loader.addModule({
    name: "zenautocomplete",
    type: "js",
    fullpath: "/zport/dmd/javascript/zenautocomplete.js",
    requires: ["autocomplete", "animation", "autocompleteskin"]
});

//Declare the Zenoss namespace
YAHOO.namespace("zenoss");

// Put the loader somewhere accessible
YAHOO.namespace("zenoss.loader");
YAHOO.zenoss.loader = loader;

// Define a helpful "class" function (thanks, Prototype)

var Class={
    create:function(){
        return function(){
            bindMethods(this);
            this.__init__.apply(this,arguments);
        } 
    }
}

YAHOO.zenoss.Class = Class;


function bindMethodsTo(src, scope) {
    for (var property in src) {
        if (typeof src[property]=='function') {
            src[property] = method(scope, src[property]);
        }
    }
}

// Subclassing! (thanks, me)

var Subclass={
    create: function(klass){
        return function() {
            this.superclass = {};
            for (var property in klass.prototype) {
                if (!(property in this))
                    this[property] = klass.prototype[property];
                    this.superclass[property] = klass.prototype[property];
            }
            bindMethods(this);
            bindMethodsTo(this.superclass, this);
            this.__init__.apply(this, arguments);
        }
    }
}
YAHOO.zenoss.Subclass = Subclass;


function purge(d) {
    var a = d.attributes, i, l, n;
    if (a) {
        l = a.length;
        for (i = 0; i < l; i += 1) {
            n = a[i].name;
            if (typeof d[n] === 'function') {
                d[n] = null;
            }
        }
    }
    a = d.childNodes;
    if (a) {
        l = a.length;
        for (i = 0; i < l; i += 1) {
            purge(d.childNodes[i]);
        }
    }
}
YAHOO.zenoss.purge = purge;
