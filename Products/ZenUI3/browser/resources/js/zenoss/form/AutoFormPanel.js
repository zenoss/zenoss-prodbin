/*
 ###########################################################################
 #
 # This program is part of Zenoss Core, an open source monitoring platform.
 # Copyright (C) 2010, Zenoss Inc.
 #
 # This program is free software; you can redistribute it and/or modify it
 # under the terms of the GNU General Public License version 2 as published by
 # the Free Software Foundation.
 #
 # For complete information please visit: http://www.zenoss.com/oss/
 #
 ###########################################################################
 */

/* package level */
(function() {

var ZF = Ext.ns('Zenoss.form');

ZF.AutoFormPanel = Ext.extend(ZF.BaseDetailForm, {});

Ext.reg('autoformpanel', ZF.AutoFormPanel);

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
            api: {
                submit:  function(x, y, panel){
                    var form = panel.form,
                        values = form.getFieldValues(true /* true to select dirty only */);
                    router.setInfo(Ext.applyIf(values, form.baseParams), Ext.emptyFn);
                }
            },
            border: false,
            layout: 'column',
            defaults: {
                layout: 'form',
                bodyStyle: 'padding:10px',
                labelAlign: 'top',
                columnWidth: 0.5
            }
        }, response.form));
    });
}

ZF.AutoFormCombo = Ext.extend(Ext.form.ComboBox, {
     constructor: function(config) {
         config = Ext.applyIf(config||{}, {
             editable: false,
             forceSelection: true,
             autoSelect: true,
             triggerAction: 'all',
             mode: 'local',
             store: config.values || []
         });
         Zenoss.form.AutoFormCombo.superclass.constructor.call(this, config);
     }

});
Ext.reg('autoformcombo', ZF.AutoFormCombo);

})();
