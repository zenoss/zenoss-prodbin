/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2015, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


/* package level */
(function() {
    Ext.define("Zenoss.form.TimeSpan", {
        alias:['widget.timespan'],
        extend:"Ext.panel.Panel",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                layout: 'vbox',
                height: 50,
                items: [{
                    xtype: 'container',
                    html: config.fieldLabel + ":",
                    width: 300
                },{
                    xtype: 'container',
                    layout: 'hbox',
                    items: [{
                        xtype: 'numberfield',
                        name: config.name,
                        value: config.value[0],
                        minValue: 1,
                        width: 75
                    }, {
                        xtype: 'container',
                        width: 10
                    },{
                        xtype: 'combo',
                        name: config.name,
                        editable: false,
                        forceSelection: true,
                        autoSelect: true,
                        triggerAction: 'all',
                        queryMode: 'local',
                        value: config.value[1],
                        store: ['days', 'weeks', 'months'],
                        width: 200
                    }]
                }]
            });
            this.callParent(arguments);
        }
    });
}());
