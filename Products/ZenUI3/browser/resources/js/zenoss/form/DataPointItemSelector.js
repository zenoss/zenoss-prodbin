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
