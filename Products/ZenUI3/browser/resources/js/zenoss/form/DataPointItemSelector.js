/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


/* package level */
(function() {
Ext.define("Zenoss.form.DataPointItemSelector", {
    alias:['widget.datapointitemselector'],
    extend:"Ext.ux.form.ItemSelector",
    constructor: function(config) {
        var record = config.record;

        this.value = config.value;

        Ext.applyIf(config, {
            name: 'dataPoints',
            fieldLabel: _t('Data Points'),
            id: 'thresholdItemSelector',
            imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
            drawUpIcon: false,
            drawDownIcon: false,
            drawTopIcon: false,
            drawBotIcon: false,
            store: record.allDataPoints
        });
        this.callParent(arguments);
    }
});

}());
