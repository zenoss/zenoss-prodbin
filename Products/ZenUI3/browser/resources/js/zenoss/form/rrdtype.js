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
     Ext.define("Zenoss.form.rrdtype", {
         alias:['widget.rrdtype'],
         extend:"Ext.form.ComboBox",
         constructor: function(config) {
             var record = config.record;
             config = config || {};
             Ext.apply(config, {
                 fieldLabel: _t('RRD Type'),
                 name: 'rrdtype',
                 editable: false,
                 forceSelection: true,
                 autoSelect: true,
                 triggerAction: 'all',
                 mode: 'local',
                 store: record.availableRRDTypes
             });
             this.callParent(arguments);
         }
     });

}());