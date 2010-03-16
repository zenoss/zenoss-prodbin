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
     var DataPointItemSelector = Ext.extend(Ext.ux.form.ItemSelector, {
         constructor: function(config) {
             var record = config.record;
             Ext.applyIf(config, {
                 name: 'dataPoints',
                 fieldLabel: _t('Data Points'),
                 id: 'thresholdItemSelector',
                 imagePath: "/zenui/img/xtheme-zenoss/icon",
                 drawUpIcon: false,
                 drawDownIcon: false,
                 drawTopIcon: false,
                 drawBotIcon: false,
                 multiselects: [{
                       width: 250,
                       height: 200,
                       store: record.allDataPoints                            
                 },{
                       width: 250,
                       height: 200,
                       // datapoints comes back as a string from the server
                       store: record.dataPoints.split(",") || []                            
                }]
                });
                              
             DataPointItemSelector.superclass.constructor.apply(this, arguments);
         }
     });
     Ext.reg('datapointitemselector', DataPointItemSelector);
}());