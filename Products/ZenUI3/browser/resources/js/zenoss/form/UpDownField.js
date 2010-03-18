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

Ext.ns('Zenoss.form');

Zenoss.form.UpDownField = Ext.extend(Ext.form.ComboBox, {
     constructor: function(config) {
         config = Ext.applyIf(config||{}, {
             editable: false,
             forceSelection: true,
             autoSelect: true,
             triggerAction: 'all',
             mode: 'local',
             store: [
                 [1, 'Up'],
                 [0, 'Down']
             ]
         });
         Zenoss.form.UpDownField.superclass.constructor.call(this, config);
     }
 });
 Ext.reg('updownfield', Zenoss.form.UpDownField);

})();
