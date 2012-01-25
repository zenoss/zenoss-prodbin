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
             var store = [];
             Ext.each(record.availableRRDTypes, function(item) {
                 store.push([item]);
             });
             Ext.apply(config, {
                 fieldLabel: _t('RRD Type'),
                 name: 'rrdtype',
                 editable: false,
                 forceSelection: true,
                 autoSelect: true,
                 triggerAction: 'all',
                 queryMode: 'local',
                 displayField: 'name',
                 valueField: 'name',
                 store:  Ext.create('Ext.data.ArrayStore', {
                     model: 'Zenoss.model.Name',
                     data: store
                 })
             });
             this.callParent(arguments);
         }
     });

}());