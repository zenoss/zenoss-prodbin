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
               "container", "button", "autocomplete",
               "autocompleteskin"]
});
loader.addModule({
    name: "zenautocomplete",
    type: "js",
    fullpath: "/zport/dmd/javascript/zenautocomplete.js",
    requires: ["autocomplete", "autocompleteskin"]
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
            this.__init__.apply(this,arguments);
        } 
    }
}

// Subclassing! (thanks, me)

var Subclass={
    create: function(klass){
        return function() {
            for (var property in klass.prototype) {
                if (property=='__init__' ||
                    property=='__class__' ) continue;
                this[property] = klass.prototype[property];
            }
            this.superclass = {
                constructor: klass,
                __init__: method(this, klass.prototype.__init__)
            };
            bindMethods(this);
            this.__init__.apply(this, arguments);
        }
    }
}

