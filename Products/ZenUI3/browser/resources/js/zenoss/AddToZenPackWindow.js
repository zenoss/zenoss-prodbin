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

(function(){

Ext.ns('Zenoss');

/**
 * @class Zenoss.AddToZenPackWindow
 * @extends Ext.Window
 */
Zenoss.AddToZenPackWindow = Ext.extend(Ext.Window, {
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            id: 'addToZenPackWindow',
            title: _t('Add to Zen Pack'),
            layout: 'fit',
            autoHeight: true,
            width: 310,
            closeAction: 'hide',
            plain: true,
            items: [{
                id: 'addzenpackform',
                xtype: 'form',
                monitorValid: true,
                defaults: {width: 180},
                autoHeight: true,
                border: false,
                frame: false,
                labelWidth: 100,
                items: [{
                    fieldLabel: _t('Zen Pack'),
                    name: 'zpname',
                    xtype: 'combo',
                    allowBlank: false,
                    store: new Ext.data.DirectStore({
                        id: 'myzpstore',
                        fields: ['name'],
                        root: 'packs',
                        totalProperty: 'totalCount',
                        directFn: 
                            Zenoss.remote.ZenPackRouter.getEligiblePacks
                    }),
                    valueField: 'name', 
                    displayField: 'name',
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true,
                    id: 'zpcombobox'
                }],
                buttons: [{
                    text: _t('Cancel'),
                    handler: function () {
                        Ext.getCmp('addToZenPackWindow').hide();
                    }
                }, {
                    text: _t('Submit'),
                    formBind: true,
                    handler: function () {
                        form = Ext.getCmp('addzenpackform');
                        var chosenzenpack = 
                            form.getForm().findField('zpname').getValue();
                            Zenoss.remote.ZenPackRouter.addToZenPack({
                                topack: Ext.getCmp('addToZenPackWindow').target,
                                zenpack: chosenzenpack
                            },
                            function (data) {
                                Ext.getCmp('addToZenPackWindow').hide();
                            }
                        );
                    }
                }]
            }]
        });
        Zenoss.AddToZenPackWindow.superclass.constructor.call(this, config);
    },
    setTarget: function (target) {
        this.target = target;
    }
});

Ext.reg('AddToZenPackWindow', Zenoss.AddToZenPackWindow);

})();
