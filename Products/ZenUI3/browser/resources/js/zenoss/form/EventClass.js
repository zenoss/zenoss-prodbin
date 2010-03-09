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
     var EventClass = Ext.extend(Ext.form.ComboBox, {
         constructor: function(config) {
             config = config || {};
             if (!Zenoss.env.EVENT_CLASSES) {
                 throw "You must include the js-snippets viewlet before you use the eventClass control";
             }
             Ext.applyIf(config, {
                 fieldLabel: _t('Event Class'),
                 name: 'eventClass',
                 typeAhead: true,
                 triggerAction: 'all',
                 mode: 'local',
                 store: Zenoss.env.EVENT_CLASSES
             });
             EventClass.superclass.constructor.apply(this, arguments);
         }
     });
     Ext.reg('EventClass', EventClass);
}());