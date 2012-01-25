/*
 ###########################################################################
 #
 # This program is part of Zenoss Core, an open source monitoring platform.
 # Copyright (C) 2010, Zenoss Inc.
 #
 # This program is free software; you can redistribute it and/or modify it
 # under the terms of the GNU General Public License version 2 or (at your
 # option) any later version as published by the Free Software Foundation.
 #
 # For complete information please visit: http://www.zenoss.com/oss/
 #
 ###########################################################################
 */

/* package level */
(function() {

var ZF = Ext.ns('Zenoss.form');

Ext.define("Zenoss.form.AutoFormPanel", {
    extend: "Zenoss.form.BaseDetailForm",
    alias: ['widget.autoformpanel']
});



/*
* Zenoss.form.getGeneratedForm
* Accepts a uid and a callback.
* Asks the router for a form for the object represented by uid.
* Returns a config object that can be added to a container to render the form.
*/
ZF.getGeneratedForm = function(uid, callback, router) {
    // Router doesn't technically matter, since they all do getInfo, but
    // getForm is definitely defined on DeviceRouter
    router = router || Zenoss.remote.DeviceRouter;
    router.getForm({uid:uid}, function(response){
        callback(Ext.apply({
            xtype:'autoformpanel',
            contextUid: uid,
            layout: 'column',
            defaults: {
                layout: 'anchor',
                bodyStyle: 'padding:10px',
                fieldDefaults: {
                    labelAlign: 'top'
                },
                columnWidth: 0.5
            }
        }, response.form));
    });
}

Ext.define("Zenoss.form.AutoFormCombo", {
    extend: "Ext.form.ComboBox",
    alias: ['widget.autoformcombo'],
     constructor: function(config) {
         config = Ext.applyIf(config||{}, {
             editable: false,
             forceSelection: true,
             autoSelect: true,
             triggerAction: 'all',
             queryMode: 'local',
             store: config.values || []
         });
         Zenoss.form.AutoFormCombo.superclass.constructor.call(this, config);
     }

});


})();
