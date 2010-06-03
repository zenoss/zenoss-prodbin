(function(){

Ext.ns('Zenoss.render');

// templates for the events renderer
var iconTemplate = new Ext.Template(
    '<td class="severity-icon-small {severity} {noevents}">{count}</td>');
iconTemplate.compile();

var rainbowTemplate = new Ext.Template(
    '<table class="eventrainbow"><tr>{cells}</tr></table>');
rainbowTemplate.compile();

var upDownTemplate = new Ext.Template(
    '<span class="status-{0}{2}">{1}</span>');
upDownTemplate.compile();

function convertToUnits(num, divby, unitstr, places){
    unitstr = unitstr || "B";
    places = places || 2;
    divby = divby || 1024.0;
    var units = [];
    Ext.each(['', 'K', 'M', 'G', 'T', 'P'], function(p){
        units.push(p+unitstr);
    });
    var sign = 1;
    if (num < 0) {
        num = Math.abs(num);
        sign = -1;
    }
    var i;
    for (i=0;i<units.length;i++) {
        if (num<divby) {
            break;
        }
        num = num/divby;
    }
    return (num*sign).toFixed(places) + units[i];
}

function pingStatusBase(bool) {
    if (Ext.isString(bool)) {
        bool = bool.toLowerCase();
        if (bool=='none') {
            return 'Unknown';
        }
        bool = bool=='up';
    }
    var str = bool ? 'Up' : 'Down';
    return str;
}

Ext.apply(Zenoss.render, {

    bytesString: function(num) {
        return num===0 ? '0' :convertToUnits(num, 1024.0, 'B');
    },

    pingStatus: function(bool) {
        var str = pingStatusBase(bool);
        return upDownTemplate.apply([str.toLowerCase(), str]);
    },

    pingStatusLarge: function(bool) {
        var str = pingStatusBase(bool);
        return upDownTemplate.apply([str.toLowerCase(), str, '-large']);
    },

    ipAddress: function(ip) {
        if (!ip||ip=='0.0.0.0') {
            return '';
        }
        return Ext.isString(ip) ? ip : Zenoss.util.num2dot(ip);
    },

    severity: function(sev) {
        return '<div class="severity-icon-small '+
            Zenoss.util.convertSeverity(sev) +
            '"'+'><'+'/div>';
    },

    // renders availability as a percentage with 3 digits after decimal point
    availability: function(value) {
        return Ext.util.Format.number(value*100, '0.000%');
    },

    evstatus: function(evstatus) {
        return '<div class="status-icon-small-'+evstatus.toLowerCase()+'"><'+'/div>';
    },

    events: function(value, count) {
        var result = '',
            sevs = ['critical', 'error', 'warning', 'info', 'debug', 'clear'];
        count = count || 3;
        Ext.each(sevs.slice(0, count), function(severity) {
            var noevents = (0 === value[severity]) ? 'no-events' : '';
            result += iconTemplate.apply({
                severity: severity,
                count:value[severity],
                noevents: noevents
            });
        });
        return rainbowTemplate.apply({cells: result});
    },

    locking: function(obj) {
        /*
        * Expects an object with keys updates, deletion, events, all boolean
        */
        var from = [];
        if (obj.updates) {
            from.push('updates');
        }
        if (obj.deletion) {
            from.push('deletion');
        }
        if (!Ext.isEmpty(from)) {
            var l = _t('Locked from ') + from.join(_t(' and '));
            if (obj.events) {
                l += "<br/>"+_t("Send event when blocked");
            } else {
                l += "<br/>"+_t("Do not send event when blocked");
            }
            return l;
        } else {
            return _t('Unlocked');
        }
    },

    locking_icons: function(obj) {
        /*
        * Expects an object with keys updates, deletion, events, all boolean
        * Returns images representing locking status.
        */
        var tpl = new Ext.Template(
            '<img border="0" src="locked-{str}-icon.png"',
            'style="vertical-align:middle"/>'),
            result = '';
        tpl.compile();
        if (obj.updates) {
            result += tpl.apply({str:'update'});
        }
        if (obj.deletion) {
            result += tpl.apply({str:'delete'});
        }
        if (obj.events) {
            result += tpl.apply({str:'sendevent'});
        }
        return result;
    },

    /*
     * Given a uid, determines the type of the object and passes rendering
     * off to the appropriate rendering function.
     * e.g. Zenoss.render.link('/zport/dmd/Devices/Server') =>
     * <a href="/zport/dmd/itinfrastructure#devices:/Devices/Server/Linux">...
     *
     * Can also just accept a url and name for wrapping in an anchor tag, by
     * passing in null for the first argument.
     */
    link: function(uid, url, name) {
        if (!url) {
            var dflt = 'default_uid_renderer',
                type = Zenoss.types.type(uid) || dflt,
                renderer = Zenoss.render[type];
            if (renderer) {
                return renderer(uid, name);
            }
        }
        if (url && name) {
            return '<a class="z-entity" href="'+url+'">'+name+'</a>';
        }
    },

    default_uid_renderer: function(uid, name) {
        // Just straight up links to the object.
        var parts;
        if (!uid) {
            return uid;
        }
        if (Ext.isObject(uid)) {
            uid = uid.uid;
            name = uid.name;
        }
        if (!name) {
            parts = uid.split('/');
            name = parts[parts.length-1];
        }
        return Zenoss.render.link(null, uid, name);
    },

    linkFromGrid: function(name, col, record) {
        var item;
        if (typeof(record.data[col.id]) == 'object') {
            item = record.data[col.id];

            if (item.uid) {
                return Zenoss.render.link(item.uid, null, item.text);
            }
            return item.text;
        }

        return name;
    },

    Device: function(uid, name) {
        // For now, link to the old device page
        return Zenoss.render.link(null, uid+'/devicedetail', name);
    },

    DeviceClass: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Devices/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#devices:.zport.dmd.Devices' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    },

    DeviceLocation: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Locations/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#locs:.zport.dmd.Locations' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    },

    DeviceGroup: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Groups/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#groups:.zport.dmd.Groups' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) name = value;
        return Zenoss.render.link(null, url, name);
    },

    DeviceComponent: function(name, col, record) {
        var item = record.data[col.id];
        if (item.uid){
            // TODO once these pages are built fix the link
            return Zenoss.render.default_uid_renderer(item.uid, item.text);
        }
        return item.text;
    },

    EventClass: function(uid, name) {
        return Zenoss.render.default_uid_renderer(uid, name);
    },

    IpServiceClass: function(value, metadata, record, rowIndex, colIndex, store) {
        // this is intended to set directly as a column renderer instead of
        // using Types.js. See the Ext.grid.ColumnModel.setRenderer
        // documentation
        var uid = record.data.serviceClassUid.replace(/\//g, '.');
        return Zenoss.render.serviceClass('ipservice', uid, value);
    },
    
    WinServiceClass: function(value, metadata, record, rowIndex, colIndex, store) {
        // this is intended to set directly as a column renderer instead of
        // using Types.js. See the Ext.grid.ColumnModel.setRenderer
        // documentation
        var uid = record.data.serviceClassUid.replace(/\//g, '.');
        return Zenoss.render.serviceClass('winservice', uid, value);
    },
    
    serviceClass: function(page, uid, name) {
        var url = String.format('/zport/dmd/{0}#navTree:{1}', page, uid);
        return Zenoss.render.link(null, url, name);
    },

    IpInterface: function(uid, name) {
        var deviceUid = uid.split('/os/interfaces/')[0];
        var url = deviceUid + '/devicedetail#deviceDetailNav:IpInterface:' + uid;
        return Zenoss.render.link(null, url, name);
    },

    IpAddress: function(uid, name) {
        return Zenoss.render.Network(uid, name);
    },

    Network: function(uid, name) {
        var url = '/zport/dmd/networks#networks:' + uid.replace(/\//g, '.');
        if (!name) {
            var parts = uid.split('/');
            name = parts[parts.length-1];
        }
        return Zenoss.render.link(null, url, name);
    },
    
    Process: function(uid, name) {
        var url = '/zport/dmd/process#processTree:' + uid.replace(/\//g, '.');
        if (!name) {
            var parts = uid.split('/');
            name = parts[parts.length-1];
        }
        return Zenoss.render.link(null, url, name);
    }

}); // Ext.apply

})(); // End local namespace
