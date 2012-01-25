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
     Ext.define("Zenoss.form.EventClass", {
         alias:['widget.eventclass'],
         extend:"Ext.form.ComboBox",
         constructor: function(config) {
             config = config || {};
             if (!Zenoss.env.EVENT_CLASSES) {
                 throw "You must include the js-snippets viewlet before you use the eventClass control";
             }
             Ext.applyIf(config, {
                 name: 'eventClass',
                 typeAhead: true,
                 editable: true,
                 forceSelection: true,
                 autoSelect: true,
                 listConfig:{
                     resizable: true
                 },
                 triggerAction: 'all',
                 defaultListConfig: {
                    maxWidth:250
                 },
                 queryMode: 'local',
                 store: Zenoss.env.EVENT_CLASSES
             });
             this.callParent([config]);
         }
     });

}());