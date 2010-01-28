(function(){

Ext.ns('Zenoss.render');

// templates for the events renderer
var iconTemplate = new Ext.Template(
    '<td class="severity-icon-small {severity}">{count}</td>'
);
iconTemplate.compile();

var rainbowTemplate = new Ext.Template(
    '<table class="eventrainbow"><tr>{cells}</tr></table>'
);
rainbowTemplate.compile();
                     
// renders events using icons for critical, error and warning
Zenoss.render.events = function (value) {
}

Ext.apply(Zenoss.render, {

    severity: function(sev) {
        return '<div class="severity-icon-small '+
            Zenoss.util.convertSeverity(sev) +
            '"'+'><'+'/div>'
    },

    // renders availability as a percentage with 3 digits after decimal point
    availability: function(value) {
        return Ext.util.Format.number(value*100, '0.000%');
    },

    evstatus: function(evstatus) {
        return '<div class="status-icon-small '+evstatus.toLowerCase()+'"><'+'/div>';
    },

    events: function(value) {
        var result = '';
        Ext.each(['critical', 'error', 'warning'], function(severity) {
            result += iconTemplate.apply({severity: severity,
                                          count:value[severity]});
        });
        return rainbowTemplate.apply({cells: result});
    },

    /* 
     * Given a uid, determines the type of the object and passes rendering
     * off to the appropriate rendering function.
     * e.g. Zenoss.render.link('/zport/dmd/Devices/Server') =>
     * <a href="/zport/dmd/itinfrastructure#devices:/Devices/Server/Linux">...
     *
     * Can also just accept a url and name for wrapping in an anchor tag.
     */
    link: function(uid, url, name) {
        if (!url) {
            var type = Zenoss.types.type(uid)
            var renderer = Zenoss.render[type];
            if (renderer) {
                return renderer(uid, name);
            }
        }
        return '<a href="'+url+'">'+name+'</a>';
    },

    Device: function(uid, name) {
        // For now, link to the old device page
        return Zenoss.render.link(null, uid, name);
    },

    DeviceClass: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Devices/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#devices:/Devices' + value;
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    },

    DeviceLocation: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Locations/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#locs:/Locations' + value;
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    }

}); // Ext.apply

})(); // End local namespace
