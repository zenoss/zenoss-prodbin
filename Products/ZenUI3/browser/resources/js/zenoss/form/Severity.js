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
     var Severity = Ext.extend(Ext.form.ComboBox, {
         constructor: function(config) {
             config = config || {};
             
             Ext.applyIf(config, {
                 fieldLabel: _t('Severity'),
                 name: 'severity',
                 typeAhead: true,
                 triggerAction: 'all',
                 mode: 'local',
                 // this is defined in zenoss.js so should always be present
                 store: Zenoss.env.SEVERITIES
             });
             Severity.superclass.constructor.apply(this, arguments);
         }
     });
     Ext.reg('Severity', Severity);
}());