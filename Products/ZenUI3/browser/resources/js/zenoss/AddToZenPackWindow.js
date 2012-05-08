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

(function(){

Ext.ns('Zenoss');



/**
 * @class Zenoss.AddToZenPackWindow
 * @extends Zenoss.dialog.BaseWindow
 */
Ext.define("Zenoss.AddToZenPackWindow", {
    alias:['widget.AddToZenPackWindow'],
    extend:"Zenoss.dialog.BaseWindow",
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            id: 'addToZenPackWindow',
            title: _t('Add to Zen Pack'),
            layout: 'fit',
            modal: true,
            autoHeight: true,
            width: 310,
            closeAction: 'hide',
            plain: true,
            items: [{
                id: 'addzenpackform',
                xtype: 'form',
                listeners: {
                    validitychange: function(form, isValid) {
                        Ext.getCmp('addToZenPackWindow').query('DialogButton')[0].setDisabled(!isValid);
                    }
                },
                defaults: {width: 250},
                autoHeight: true,
                frame: false,
                fieldDefaults: {
                    labelWidth: 100,
                    labelAlign: 'top'
                },
                buttonAlign: 'left',
                items: [{
                    fieldLabel: _t('Zen Pack'),
                    name: 'zpname',
                    xtype: 'combo',
                    emptyText: _t('Please select a zenpack...'),
                    listEmptyText: _t('No zenpacks available'),
                    allowBlank: false,
                    store: new Ext.data.DirectStore({
                        id: 'myzpstore',
                        root: 'packs',
                        model: 'Zenoss.model.Name',
                        totalProperty: 'totalCount',
                        directFn: Zenoss.remote.ZenPackRouter.getEligiblePacks
                    }),
                    valueField: 'name',
                    displayField: 'name',
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true,
                    id: 'zpcombobox'
                }],
                buttons: [{
                    text: _t('Submit'),
                    xtype: 'DialogButton',
                    disabled: true,
                    handler: function () {
                        var form;
                        form = Ext.getCmp('addzenpackform');
                        var chosenzenpack =
                            form.getForm().findField('zpname').getValue();
                            Zenoss.remote.ZenPackRouter.addToZenPack({
                                topack: Ext.getCmp('addToZenPackWindow').target,
                                zenpack: chosenzenpack
                            },
                            function (data) {
                                Ext.getCmp('addToZenPackWindow').hide();
                                Zenoss.message.info(_t("The item was added to the zenpack, {0}"), chosenzenpack);
                            }
                        );
                    }
                },{
                    text: _t('Cancel'),
                    xtype: 'DialogButton',
                    handler: function () {
                        Ext.getCmp('addToZenPackWindow').hide();
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



})();
